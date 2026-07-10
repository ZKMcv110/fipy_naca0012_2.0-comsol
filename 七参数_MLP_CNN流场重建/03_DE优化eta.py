#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""使用 MLP-CNN 性能分支进行 DE 优化 eta。

脚本只在当前新目录写结果；不调用 COMSOL，不修改旧工程。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


ROOT = Path(__file__).resolve().parent
PARAM_COLS = ["Ta", "Twa", "Tb", "Ts", "Tt", "Tad", "theta"]
PARAM_RANGES = {
    "Ta": (0.00, 0.05),
    "Twa": (0.20, 0.60),
    "Tb": (0.08, 0.15),
    "Ts": (0.50, 1.50),
    "Tt": (0.50, 1.20),
    "Tad": (0.00, 1.00),
    "theta": (-10.0, 10.0),
}


class ParamToFieldNet(nn.Module):
    def __init__(self, output_hw: tuple[int, int], latent_dim: int = 256):
        super().__init__()
        self.output_hw = output_hw
        self.encoder = nn.Sequential(
            nn.Linear(7, 128),
            nn.ReLU(),
            nn.Linear(128, latent_dim),
            nn.ReLU(),
        )
        self.seed_h, self.seed_w = 5, 8
        self.to_seed = nn.Linear(latent_dim, 128 * self.seed_h * self.seed_w)
        self.decoder = nn.Sequential(
            nn.Upsample(scale_factor=2, mode="bilinear", align_corners=False),
            nn.Conv2d(128, 96, 3, padding=1),
            nn.ReLU(),
            nn.Upsample(scale_factor=2, mode="bilinear", align_corners=False),
            nn.Conv2d(96, 64, 3, padding=1),
            nn.ReLU(),
            nn.Upsample(scale_factor=2, mode="bilinear", align_corners=False),
            nn.Conv2d(64, 32, 3, padding=1),
            nn.ReLU(),
            nn.Conv2d(32, 4, 3, padding=1),
        )
        self.head = nn.Sequential(nn.Linear(latent_dim, 128), nn.ReLU(), nn.Linear(128, 2))

    def forward(self, params: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        latent = self.encoder(params)
        seed = self.to_seed(latent).view(-1, 128, self.seed_h, self.seed_w)
        field = self.decoder(seed)
        field = F.interpolate(field, size=self.output_hw, mode="bilinear", align_corners=False)
        return field, self.head(latent)


def eta_value(nu: float, f_value: float, nu0: float, f0: float) -> float:
    return (nu / max(nu0, 1e-12)) / ((max(f_value, 1e-12) / max(f0, 1e-12)) ** (1.0 / 3.0))


def load_model(model_dir: Path, device: torch.device) -> tuple[ParamToFieldNet, dict[str, np.ndarray]]:
    stats_npz = np.load(model_dir / "normalization_stats.npz")
    stats = {name: stats_npz[name] for name in stats_npz.files}
    output_hw = tuple(int(v) for v in stats["output_hw"])
    model = ParamToFieldNet(output_hw).to(device)
    model.load_state_dict(torch.load(model_dir / "best_model.pth", map_location=device))
    model.eval()
    return model, stats


def predict(model: ParamToFieldNet, stats: dict[str, np.ndarray], params: np.ndarray, device: torch.device) -> dict[str, float]:
    x = (params.astype(np.float32) - stats["param_mean"]) / stats["param_std"]
    with torch.no_grad():
        _, pred_norm = model(torch.tensor(x[None, :], dtype=torch.float32, device=device))
    pred = pred_norm.cpu().numpy()[0] * stats["target_std"] + stats["target_mean"]
    nu, f_value = float(pred[0]), float(pred[1])
    eta = eta_value(nu, f_value, float(stats["nu0"]), float(stats["f0"]))
    return {"Nu_pred": nu, "f_pred": f_value, "eta_pred": eta}


def simple_de(bounds: list[tuple[float, float]], objective, pop_size: int, generations: int, seed: int):
    rng = np.random.default_rng(seed)
    dim = len(bounds)
    low = np.asarray([b[0] for b in bounds], dtype=np.float64)
    high = np.asarray([b[1] for b in bounds], dtype=np.float64)
    pop = low + rng.random((pop_size, dim)) * (high - low)
    scores = np.asarray([objective(ind) for ind in pop], dtype=np.float64)
    history = []
    for gen in range(generations):
        for i in range(pop_size):
            choices = [idx for idx in range(pop_size) if idx != i]
            a, b, c = pop[rng.choice(choices, size=3, replace=False)]
            mutant = np.clip(a + 0.7 * (b - c), low, high)
            cross = rng.random(dim) < 0.8
            if not np.any(cross):
                cross[rng.integers(0, dim)] = True
            trial = np.where(cross, mutant, pop[i])
            trial_score = objective(trial)
            if trial_score > scores[i]:
                pop[i], scores[i] = trial, trial_score
        best_idx = int(np.argmax(scores))
        history.append({"generation": gen + 1, "best_eta": float(scores[best_idx])})
        print(f"generation={gen + 1:03d} best_eta={scores[best_idx]:.6f}")
    best_idx = int(np.argmax(scores))
    return pop[best_idx], float(scores[best_idx]), history


def main() -> None:
    parser = argparse.ArgumentParser(description="使用 MLP-CNN 性能分支进行 DE 优化 eta")
    parser.add_argument("--model-dir", default=str(ROOT / "results" / "mlp_cnn_field_multiloss_e10"))
    parser.add_argument("--output-dir", default=str(ROOT / "optimization_results" / "mlp_cnn_de_multiloss_e10"))
    parser.add_argument("--pop-size", type=int, default=24)
    parser.add_argument("--generations", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model, stats = load_model(Path(args.model_dir), device)
    bounds = [PARAM_RANGES[name] for name in PARAM_COLS]
    cache: dict[tuple[float, ...], dict[str, float]] = {}

    def objective(vec: np.ndarray) -> float:
        key = tuple(np.round(vec, 10).tolist())
        if key not in cache:
            cache[key] = predict(model, stats, vec, device)
        return cache[key]["eta_pred"]

    best_vec, best_eta, history = simple_de(bounds, objective, args.pop_size, args.generations, args.seed)
    best_pred = predict(model, stats, best_vec, device)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    result = {
        "best_params": {name: float(value) for name, value in zip(PARAM_COLS, best_vec)},
        "prediction": best_pred,
        "best_eta_from_de": best_eta,
        "model_dir": str(Path(args.model_dir).resolve()),
        "note": "该结果来自 MLP-CNN 流热场代理模型性能分支，必须回到 CFD 复算验证。",
    }
    (out_dir / "best_params.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    np.savetxt(
        out_dir / "de_history.csv",
        np.asarray([[h["generation"], h["best_eta"]] for h in history]),
        delimiter=",",
        header="generation,best_eta",
        comments="",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
