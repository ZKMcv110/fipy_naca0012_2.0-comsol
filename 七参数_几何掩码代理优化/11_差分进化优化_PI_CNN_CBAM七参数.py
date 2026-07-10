#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""使用七参数 PI-CNN-CBAM 几何掩码模型进行差分进化优化。"""

from __future__ import annotations

import argparse
import json
from importlib.machinery import SourceFileLoader
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch

from common import PARAM_COLS, PARAM_RANGES, PROJECT_ROOT, ROOT, baseline_from_labels, ensure_dir, eta_value, read_csv, write_json


pred_mod = SourceFileLoader("predict_pi_cbam", str(ROOT / "10_预测_PI_CNN_CBAM性能.py")).load_module()
load_pi_model = pred_mod.load_pi_model
predict_with_loaded_model = pred_mod.predict_with_loaded_model


def simple_de(bounds: list[tuple[float, float]], objective, pop_size: int, generations: int, seed: int):
    rng = np.random.default_rng(seed)
    dim = len(bounds)
    low = np.asarray([b[0] for b in bounds], dtype=np.float64)
    high = np.asarray([b[1] for b in bounds], dtype=np.float64)
    pop = low + rng.random((pop_size, dim)) * (high - low)
    scores = np.asarray([objective(x) for x in pop], dtype=np.float64)
    history = []
    for gen in range(1, generations + 1):
        for i in range(pop_size):
            choices = [j for j in range(pop_size) if j != i]
            a, b, c = pop[rng.choice(choices, 3, replace=False)]
            mutant = np.clip(a + 0.8 * (b - c), low, high)
            cross = rng.random(dim) < 0.9
            if not cross.any():
                cross[rng.integers(0, dim)] = True
            trial = np.where(cross, mutant, pop[i])
            trial_score = objective(trial)
            if trial_score > scores[i]:
                pop[i] = trial
                scores[i] = trial_score
        best_idx = int(np.argmax(scores))
        history.append({"generation": gen, "best_eta": float(scores[best_idx])})
        print(f"[INFO] generation={gen} best_eta={scores[best_idx]:.6f}")
    best_idx = int(np.argmax(scores))
    return pop[best_idx], float(scores[best_idx]), history


def main() -> None:
    parser = argparse.ArgumentParser(description="PI-CNN-CBAM差分进化优化七参数")
    parser.add_argument("--model-dir", default=str(ROOT / "ablation_results_1000" / "gp"))
    parser.add_argument("--labels", default=str(ROOT / "samples" / "labels_7param_1000.csv"))
    parser.add_argument("--output-dir", default=str(ROOT / "optimization_results_1000_gp"))
    parser.add_argument("--pop-size", type=int, default=32)
    parser.add_argument("--generations", type=int, default=30)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--image-size", type=int, default=64)
    args = parser.parse_args()
    if args.pop_size < 4:
        raise ValueError("差分进化至少需要4个个体，--pop-size 必须 >= 4。")
    if args.generations < 1:
        raise ValueError("--generations 必须 >= 1。")

    labels = read_csv(Path(args.labels))
    nu0, f0 = baseline_from_labels(labels)
    nu_min, nu_max = float(labels["Nu"].min()), float(labels["Nu"].max())
    f_min, f_max = float(labels["f"].min()), float(labels["f"].max())
    nu_lower, nu_upper = 0.8 * nu_min, 1.2 * nu_max
    f_lower, f_upper = 0.8 * f_min, 1.2 * f_max
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model, stats = load_pi_model(Path(args.model_dir), device)
    bounds = [PARAM_RANGES[name] for name in PARAM_COLS]
    theta_note = "训练标签包含多个theta取值，按PARAM_RANGES搜索。"
    if "theta" in labels.columns and labels["theta"].nunique() == 1:
        theta_fixed = float(labels["theta"].iloc[0])
        bounds[PARAM_COLS.index("theta")] = (theta_fixed, theta_fixed)
        theta_note = f"训练标签中theta只有一个取值，优化时固定theta={theta_fixed}，避免外推。"
        print(f"[WARN] 训练标签中 theta 只有一个取值，优化时固定 theta={theta_fixed}，避免外推。")
    cache: dict[tuple[float, ...], dict] = {}

    def objective(vector: np.ndarray) -> float:
        params = {name: float(value) for name, value in zip(PARAM_COLS, vector)}
        key = tuple(round(params[name], 8) for name in PARAM_COLS)
        if key not in cache:
            pred = predict_with_loaded_model(params, model, stats, device, args.image_size)
            if pred["Nu_pred"] <= 0 or pred["f_pred"] <= 0:
                pred["eta_pred"] = -1.0e9
            elif not (nu_lower <= pred["Nu_pred"] <= nu_upper and f_lower <= pred["f_pred"] <= f_upper):
                pred["eta_pred"] = -1.0e9
            else:
                pred["eta_pred"] = eta_value(pred["Nu_pred"], pred["f_pred"], nu0, f0)
            cache[key] = pred
        return cache[key]["eta_pred"]

    best_vec, _best_eta, history = simple_de(bounds, objective, args.pop_size, args.generations, args.seed)
    best_params = {name: float(value) for name, value in zip(PARAM_COLS, best_vec)}
    best_pred = predict_with_loaded_model(best_params, model, stats, device, args.image_size)
    best_pred["eta_pred"] = eta_value(best_pred["Nu_pred"], max(best_pred["f_pred"], 1e-12), nu0, f0)

    out_dir = ensure_dir(Path(args.output_dir))
    write_json(out_dir / "best_params.json", {
        "best_params": best_params,
        "prediction": best_pred,
        "baseline": {"Nu0": nu0, "f0": f0},
        "search_bounds": {name: [float(low), float(high)] for name, (low, high) in zip(PARAM_COLS, bounds)},
        "model_source": str(Path(args.model_dir)),
        "note": f"该结果由PI-CNN-CBAM几何掩码代理模型预测，必须回到COMSOL复核。{theta_note}",
    })
    pd.DataFrame(history).to_csv(out_dir / "de_history.csv", index=False, encoding="utf-8-sig")
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot([row["generation"] for row in history], [row["best_eta"] for row in history], marker="o")
    ax.set_xlabel("Generation")
    ax.set_ylabel("Best eta")
    fig.tight_layout()
    fig.savefig(out_dir / "de_convergence.png", dpi=200)
    plt.close(fig)
    print(f"[OK] PI-CNN-CBAM最优参数已保存: {out_dir / 'best_params.json'}")
    print(json.dumps({"best_params": best_params, **best_pred}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
