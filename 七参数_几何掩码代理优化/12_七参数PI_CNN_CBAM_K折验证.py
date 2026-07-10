#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""七参数几何掩码 PI-CNN-CBAM K 折交叉验证。

该脚本复用 `09_消融实验_PI_CNN_CBAM.py` 中的数据集、模型和指标函数，
只新增 K 折调度与汇总输出。它不调用 COMSOL，不修改旧六参数脚本和旧结果。
"""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import torch
from sklearn.model_selection import KFold, train_test_split
from torch.utils.data import DataLoader

from common import ROOT, baseline_from_labels, ensure_dir, write_json


SOURCE = ROOT / "09_消融实验_PI_CNN_CBAM.py"


def load_training_module():
    spec = importlib.util.spec_from_file_location("seven_param_ablation", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载训练脚本: {SOURCE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def summarize(rows: list[dict]) -> dict:
    metric_keys = [key for key in rows[0].keys() if key not in {"fold", "train_count", "val_count", "test_count"}]
    summary = {}
    for key in metric_keys:
        values = np.asarray([row[key] for row in rows], dtype=np.float64)
        summary[f"{key}_mean"] = float(values.mean())
        summary[f"{key}_std"] = float(values.std(ddof=1)) if len(values) > 1 else 0.0
    return summary


def run_fold(module, df: pd.DataFrame, fold_id: int, train_val_idx: np.ndarray, test_idx: np.ndarray, args, device: torch.device) -> dict:
    train_idx, val_idx = train_test_split(
        train_val_idx,
        test_size=args.val_ratio,
        random_state=args.seed + fold_id,
        shuffle=True,
    )
    stats = module.compute_stats(df, train_idx.tolist())
    nu0, f0 = baseline_from_labels(df)

    datasets = {
        "train": module.MaskParamDataset(df.iloc[train_idx], args.mask_dir, stats, args.image_size),
        "val": module.MaskParamDataset(df.iloc[val_idx], args.mask_dir, stats, args.image_size),
        "test": module.MaskParamDataset(df.iloc[test_idx], args.mask_dir, stats, args.image_size),
    }
    loaders = {
        name: DataLoader(ds, batch_size=args.batch_size, shuffle=(name == "train"))
        for name, ds in datasets.items()
    }

    fold_output_dir = ensure_dir(args.output_dir / f"fold_{fold_id:02d}")
    run_args = SimpleNamespace(
        output_dir=str(fold_output_dir),
        epochs=args.epochs,
        lr=args.lr,
        weight_decay=args.weight_decay,
        pi_weight=args.pi_weight,
        gp_weight=args.gp_weight,
    )
    metrics = module.run_one_model(args.model_name, loaders, stats, nu0, f0, run_args, device)
    metrics.pop("model", None)
    return {
        "fold": fold_id,
        "train_count": int(len(train_idx)),
        "val_count": int(len(val_idx)),
        "test_count": int(len(test_idx)),
        **metrics,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="七参数 PI-CNN-CBAM 几何掩码模型 K 折交叉验证")
    parser.add_argument("--labels", default=str(ROOT / "samples" / "labels_7param_1000.csv"))
    parser.add_argument("--mask-dir", default=str(ROOT / "masks_fixed_1000"))
    parser.add_argument("--output-dir", default=str(ROOT / "kfold_results_1000"))
    parser.add_argument("--model-name", default="gp", help="K折验证的消融模型名，例如 gp、pi、cbam、mask、baseline")
    parser.add_argument("--k-folds", type=int, default=5)
    parser.add_argument("--val-ratio", type=float, default=0.15)
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--image-size", type=int, default=64)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--pi-weight", type=float, default=0.05)
    parser.add_argument("--gp-weight", type=float, default=0.01)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    args.mask_dir = Path(args.mask_dir)
    args.output_dir = ensure_dir(Path(args.output_dir))
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    module = load_training_module()
    df = module.load_labels(Path(args.labels))
    splitter = KFold(n_splits=args.k_folds, shuffle=True, random_state=args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[INFO] device={device} samples={len(df)} folds={args.k_folds}")

    rows = []
    for fold_id, (train_val_idx, test_idx) in enumerate(splitter.split(df), start=1):
        print(f"[INFO] Fold {fold_id}/{args.k_folds}")
        rows.append(run_fold(module, df, fold_id, train_val_idx, test_idx, args, device))

    summary = summarize(rows)
    metrics_path = args.output_dir / "kfold_metrics.csv"
    summary_path = args.output_dir / "kfold_summary.json"
    md_path = args.output_dir / "kfold_summary.md"
    pd.DataFrame(rows).to_csv(metrics_path, index=False, encoding="utf-8-sig")
    config = {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()}
    write_json(summary_path, {"config": config, "folds": rows, "summary": summary})
    md_lines = [
        f"# 七参数 PI-CNN-CBAM {args.k_folds}折交叉验证汇总",
        "",
        f"- 样本数：{len(df)}",
        f"- 折数：{args.k_folds}",
        f"- 训练轮数：{args.epochs}",
        f"- 模型名：{args.model_name}",
        f"- 输出目录：`{args.output_dir}`",
        "",
        "| 指标 | 均值 | 标准差 |",
        "| --- | ---: | ---: |",
    ]
    for key, value in summary.items():
        if not key.endswith("_mean"):
            continue
        name = key[:-5]
        md_lines.append(f"| {name} | {value:.6g} | {summary.get(name + '_std', 0.0):.6g} |")
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    print(f"[OK] K折交叉验证结果: {metrics_path}")


if __name__ == "__main__":
    main()
