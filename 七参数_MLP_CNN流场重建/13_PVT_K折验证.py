#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""PVT Conditional U-Net 3 折验证。

本脚本复用 `14_PVT消融实验.py` 中的模型、数据集和训练函数，
采用 A3 配置：坐标/区域条件输入 + eta 一致性 + 梯度一致性。
K 折结果用于验证数据划分稳定性，不替代 50 epoch 全量主模型。
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import numpy as np
import torch
from sklearn.model_selection import KFold


ROOT = Path(__file__).resolve().parent
DEFAULT_DATASET = ROOT / "data" / "field_reconstruction_dataset_320x96_full_pUt.npz"
DEFAULT_OUTPUT_DIR = ROOT / "results" / "pvt_unet_kfold_3_e20"


def load_ablation_module() -> ModuleType:
    path = ROOT / "14_PVT消融实验.py"
    spec = importlib.util.spec_from_file_location("pvt_ablation", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载消融模块: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def save_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=True), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def summarize(rows: list[dict[str, object]]) -> dict[str, object]:
    metric_keys = [
        "Nu_R2", "f_R2", "eta_R2",
        "Nu_MAE", "f_MAE", "eta_MAE",
        "p_MAE", "U_MAE", "T_MAE",
        "field_MAE", "field_RMSE", "boundary_MAE",
    ]
    summary: dict[str, object] = {"fold_count": len(rows), "folds": rows}
    for key in metric_keys:
        values = [float(row[key]) for row in rows if row.get(key) is not None]
        if values:
            summary[f"{key}_mean"] = float(np.mean(values))
            summary[f"{key}_std"] = float(np.std(values, ddof=0))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="运行 PVT 主模型 K 折验证")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET))
    parser.add_argument("--field-dir", default=str(ROOT.parent / "七参数_PDE_PINN尝试" / "field_data_320x96"))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--folds", type=int, default=3)
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--lr", type=float, default=5e-4)
    parser.add_argument("--alpha", type=float, default=1.0)
    parser.add_argument("--beta", type=float, default=1.0)
    parser.add_argument("--gamma", type=float, default=0.2)
    parser.add_argument("--grad-weight", type=float, default=0.5)
    parser.add_argument("--field-weights", default="4,6,3")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    module = load_ablation_module()
    arrays, field_names, nu0, f0 = module.load_arrays(Path(args.dataset), args.limit)
    if field_names != ["p", "U", "T"]:
        raise ValueError(f"K 折验证要求 p/U/T 三通道数据，当前为 {field_names}")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    kfold = KFold(n_splits=args.folds, shuffle=True, random_state=args.seed)
    all_indices = np.arange(arrays["params"].shape[0])
    rows: list[dict[str, object]] = []

    for fold_id, (train_val_idx, test_idx) in enumerate(kfold.split(all_indices), start=1):
        rng = np.random.default_rng(args.seed + fold_id)
        shuffled = rng.permutation(train_val_idx)
        val_count = max(1, int(shuffled.size * 0.15))
        val_idx = shuffled[:val_count]
        train_idx = shuffled[val_count:]
        fold_args = argparse.Namespace(**vars(args))
        fold_args.output_dir = str(output_dir / f"fold_{fold_id}")
        config = module.ABLATION_GROUPS["A3"]
        metrics = module.train_one_group(
            config, arrays, field_names, nu0, f0,
            train_idx, val_idx, test_idx, fold_args, device,
        )
        metrics["fold"] = fold_id
        rows.append(metrics)
        write_csv(output_dir / "kfold_metrics.csv", rows)
        save_json(output_dir / "kfold_summary.json", summarize(rows))

    print(json.dumps(summarize(rows), ensure_ascii=False, indent=2, allow_nan=True))


if __name__ == "__main__":
    main()
