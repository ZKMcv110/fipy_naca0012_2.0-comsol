#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""当前 MLP-CNN 流热场重建模型的 K 折验证。"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
import torch
from sklearn.model_selection import KFold, train_test_split
from torch.utils.data import DataLoader


ROOT = Path(__file__).resolve().parent


def load_train_module():
    path = ROOT / "02_MLP_CNN流场重建训练.py"
    spec = importlib.util.spec_from_file_location("mlp_cnn_train", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载模块: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def summarize(rows: list[dict]) -> dict:
    keys = [key for key in rows[0] if key not in {"fold", "train_count", "val_count", "test_count", "output_dir"}]
    summary = {}
    for key in keys:
        values = np.asarray([row[key] for row in rows], dtype=float)
        summary[f"{key}_mean"] = float(values.mean())
        summary[f"{key}_std"] = float(values.std(ddof=0))
    return summary


def train_one_fold(module, arrays, field_names, nu0, f0, train_val_idx, test_idx, fold: int, args, device):
    train_idx, val_idx = train_test_split(
        train_val_idx,
        test_size=args.val_ratio,
        random_state=args.seed + fold,
        shuffle=True,
    )
    stats = module.make_stats(arrays, train_idx)
    model = module.ParamToFieldNet(tuple(arrays["fields"].shape[-2:])).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    loaders = {
        "train": DataLoader(module.FieldDataset(arrays, train_idx, stats), batch_size=args.batch_size, shuffle=True),
        "val": DataLoader(module.FieldDataset(arrays, val_idx, stats), batch_size=args.batch_size),
        "test": DataLoader(module.FieldDataset(arrays, test_idx, stats), batch_size=args.batch_size),
    }
    fold_dir = args.output_dir / f"fold_{fold:02d}"
    fold_dir.mkdir(parents=True, exist_ok=True)
    best_val = float("inf")
    for epoch in range(1, args.epochs + 1):
        train_loss, _ = module.run_epoch(
            model, loaders["train"], optimizer, device, stats, nu0, f0, args.alpha, args.beta, args.gamma
        )
        val_loss, _ = module.run_epoch(
            model, loaders["val"], None, device, stats, nu0, f0, args.alpha, args.beta, args.gamma
        )
        if val_loss < best_val:
            best_val = val_loss
            torch.save(model.state_dict(), fold_dir / "best_model.pth")
        print(f"fold={fold} epoch={epoch:03d} train={train_loss:.6f} val={val_loss:.6f}")

    model.load_state_dict(torch.load(fold_dir / "best_model.pth", map_location=device))
    true_t, pred_t, true_f, pred_f, case_ids = module.collect_predictions(model, loaders["test"], stats, device)
    eta_true = module.eta_np(true_t[:, 0], true_t[:, 1], nu0, f0)
    eta_pred = module.eta_np(pred_t[:, 0], pred_t[:, 1], nu0, f0)

    from sklearn.metrics import mean_absolute_error, r2_score

    row = {
        "fold": fold,
        "train_count": int(len(train_idx)),
        "val_count": int(len(val_idx)),
        "test_count": int(len(test_idx)),
        "Nu_R2": float(r2_score(true_t[:, 0], pred_t[:, 0])),
        "Nu_MAE": float(mean_absolute_error(true_t[:, 0], pred_t[:, 0])),
        "f_R2": float(r2_score(true_t[:, 1], pred_t[:, 1])),
        "f_MAE": float(mean_absolute_error(true_t[:, 1], pred_t[:, 1])),
        "eta_R2": float(r2_score(eta_true, eta_pred)),
        "eta_MAE": float(mean_absolute_error(eta_true, eta_pred)),
        "field_MAE": float(np.mean(np.abs(true_f - pred_f))),
        "field_RMSE": float(np.sqrt(np.mean((true_f - pred_f) ** 2))),
        "output_dir": str(fold_dir),
    }
    for idx, name in enumerate(field_names):
        diff = true_f[:, idx] - pred_f[:, idx]
        row[f"{name}_MAE"] = float(np.mean(np.abs(diff)))
        row[f"{name}_RMSE"] = float(np.sqrt(np.mean(diff ** 2)))

    (fold_dir / "metrics.json").write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description="MLP-CNN 流热场重建模型 K 折验证")
    parser.add_argument("--dataset", default=str(ROOT / "data" / "field_reconstruction_dataset_full.npz"))
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results" / "mlp_cnn_kfold_3_e5")
    parser.add_argument("--k-folds", type=int, default=3)
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--alpha", type=float, default=1.0)
    parser.add_argument("--beta", type=float, default=1.0)
    parser.add_argument("--gamma", type=float, default=0.2)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--val-ratio", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    module = load_train_module()
    data = np.load(args.dataset, allow_pickle=True)
    arrays = {name: data[name] for name in ["case_id", "params", "fields", "targets", "eta"]}
    field_names = [str(x) for x in data["field_names"]]
    nu0, f0 = float(data["nu0"]), float(data["f0"])
    args.output_dir.mkdir(parents=True, exist_ok=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    splitter = KFold(n_splits=args.k_folds, shuffle=True, random_state=args.seed)
    rows = []
    for fold, (train_val_idx, test_idx) in enumerate(splitter.split(arrays["params"]), start=1):
        rows.append(train_one_fold(module, arrays, field_names, nu0, f0, train_val_idx, test_idx, fold, args, device))

    summary = {
        "config": {
            "dataset": str(Path(args.dataset).resolve()),
            "output_dir": str(args.output_dir),
            "k_folds": args.k_folds,
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "device": str(device),
            "loss_formula": "L_u + L_v + L_p + L_T + alpha*L_Nu + beta*L_f + gamma*L_eta",
        },
        "folds": rows,
        "summary": summarize(rows),
    }
    (args.output_dir / "kfold_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    keys = list(rows[0].keys())
    csv_lines = [",".join(keys)]
    for row in rows:
        csv_lines.append(",".join(str(row.get(key, "")) for key in keys))
    (args.output_dir / "kfold_metrics.csv").write_text("\n".join(csv_lines) + "\n", encoding="utf-8")

    md = ["# MLP-CNN 3 折短训验证", ""]
    md.append(f"- 折数：{args.k_folds}")
    md.append(f"- 每折 epoch：{args.epochs}")
    md.append(f"- 损失函数：{summary['config']['loss_formula']}")
    md.append("")
    md.append("| 指标 | 均值 | 标准差 |")
    md.append("|---|---:|---:|")
    for key in ["Nu_R2", "Nu_MAE", "f_R2", "f_MAE", "eta_R2", "eta_MAE", "field_RMSE", "T_MAE"]:
        md.append(f"| {key} | {summary['summary'][key + '_mean']:.6f} | {summary['summary'][key + '_std']:.6f} |")
    md.append("")
    md.append("说明：这是当前 MLP-CNN 主线的 3 折短训稳定性验证，不替代后续更长 epoch 的最终训练。")
    (args.output_dir / "kfold_summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps(summary["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
