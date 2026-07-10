#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""单工况 U-Net 过拟合测试。

目的：验证网络结构是否具备复现 COMSOL 规则采样场的能力。
该脚本只训练一个 case，不作为泛化模型结果。
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
TRAIN_SCRIPT = ROOT / "08_UNet高精度流场重建训练.py"


def load_train_module():
    spec = importlib.util.spec_from_file_location("unet_train_mod", TRAIN_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载训练脚本: {TRAIN_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    parser = argparse.ArgumentParser(description="单工况 U-Net 过拟合测试")
    parser.add_argument("--dataset", default=str(ROOT / "data" / "field_reconstruction_dataset_320x96_first20.npz"))
    parser.add_argument("--field-dir", default=str(PROJECT_ROOT / "七参数_PDE_PINN尝试" / "field_data_320x96"))
    parser.add_argument("--case-id", type=int, default=20009)
    parser.add_argument("--output-dir", default=str(ROOT / "results" / "unet_overfit_case_20009"))
    parser.add_argument("--epochs", type=int, default=800)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--field-weights", default="1,8,4,3")
    parser.add_argument("--grad-weight", type=float, default=0.5)
    args = parser.parse_args()

    mod = load_train_module()
    data = np.load(args.dataset, allow_pickle=True)
    case_ids = data["case_id"].astype(int)
    matches = np.where(case_ids == args.case_id)[0]
    if matches.size == 0:
        raise ValueError(f"数据集中没有 case_id={args.case_id}")
    idx = int(matches[0])

    params = data["params"][idx:idx + 1].astype(np.float32)
    fields = data["fields"][idx:idx + 1].astype(np.float32)
    targets = data["targets"][idx:idx + 1].astype(np.float32)
    eta = data["eta"][idx:idx + 1].astype(np.float32)
    field_names = [str(x) for x in data["field_names"]]
    nu0, f0 = float(data["nu0"]), float(data["f0"])
    output_hw = tuple(int(x) for x in fields.shape[-2:])

    # 单样本过拟合时按该样本自身归一化，检验重建能力而非泛化能力。
    stats = {
        "param_mean": params.mean(axis=0),
        "param_std": params.std(axis=0) + 1e-6,
        "field_mean": fields.mean(axis=(0, 2, 3))[:, None, None],
        "field_std": fields.std(axis=(0, 2, 3))[:, None, None] + 1e-6,
        "target_mean": targets.mean(axis=0),
        "target_std": targets.std(axis=0) + 1e-6,
        "eta_mean": eta.mean(axis=0),
        "eta_std": eta.std(axis=0) + 1e-6,
    }
    norm_params = (params - stats["param_mean"]) / stats["param_std"]
    norm_fields = (fields - stats["field_mean"]) / stats["field_std"]
    norm_targets = (targets - stats["target_mean"]) / stats["target_std"]
    norm_eta = (eta - stats["eta_mean"]) / stats["eta_std"]

    mask = mod.load_domain_mask(Path(args.field_dir), args.case_id, output_hw)[None].astype(np.float32)
    coords = mod.make_coord_channels(output_hw)[None].astype(np.float32)
    spatial = np.concatenate([mask, coords], axis=1)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = mod.ConditionalUNet(output_hw, output_channels=len(field_names)).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-5)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max(args.epochs, 1))
    field_weight_values = [float(x) for x in args.field_weights.split(",")]
    if len(field_weight_values) != len(field_names):
        raise ValueError(f"--field-weights 数量必须等于场通道数量: {len(field_weight_values)} != {len(field_names)}")
    weights = torch.tensor(field_weight_values, dtype=torch.float32, device=device)

    params_t = torch.tensor(norm_params, dtype=torch.float32, device=device)
    spatial_t = torch.tensor(spatial, dtype=torch.float32, device=device)
    fields_t = torch.tensor(norm_fields, dtype=torch.float32, device=device)
    targets_t = torch.tensor(norm_targets, dtype=torch.float32, device=device)
    eta_t = torch.tensor(norm_eta, dtype=torch.float32, device=device)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    np.savez(
        out_dir / "normalization_stats.npz",
        param_mean=stats["param_mean"],
        param_std=stats["param_std"],
        field_mean=stats["field_mean"],
        field_std=stats["field_std"],
        target_mean=stats["target_mean"],
        target_std=stats["target_std"],
        eta_mean=stats["eta_mean"],
        eta_std=stats["eta_std"],
        nu0=np.float32(nu0),
        f0=np.float32(f0),
        output_hw=np.asarray(output_hw, dtype=np.int64),
    )
    history = []
    for epoch in range(1, args.epochs + 1):
        model.train()
        pred_field, pred_target = model(params_t, spatial_t)
        loss, parts = mod.compute_loss(
            pred_field, fields_t, pred_target, targets_t, eta_t,
            stats, nu0, f0, weights, alpha=0.0, beta=0.0, gamma=0.0,
            grad_weight=args.grad_weight,
        )
        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
        optimizer.step()
        scheduler.step()
        if epoch == 1 or epoch % 50 == 0 or epoch == args.epochs:
            print(f"epoch={epoch:04d} loss={float(loss.detach().cpu()):.6f}")
        row = {"epoch": epoch, "loss": float(loss.detach().cpu())}
        row.update(parts)
        history.append(row)

    model.eval()
    with torch.no_grad():
        pred_field, _ = model(params_t, spatial_t)
    pred = pred_field.cpu().numpy() * stats["field_std"] + stats["field_mean"]
    true = fields
    metrics = {"case_id": args.case_id, "epochs": args.epochs, "device": str(device)}
    for i, name in enumerate(field_names):
        diff = true[:, i] - pred[:, i]
        metrics[f"{name}_MAE"] = float(np.mean(np.abs(diff)))
        metrics[f"{name}_RMSE"] = float(np.sqrt(np.mean(diff ** 2)))
    metrics["field_MAE"] = float(np.mean(np.abs(true - pred)))
    metrics["field_RMSE"] = float(np.sqrt(np.mean((true - pred) ** 2)))

    torch.save(model.state_dict(), out_dir / "overfit_model.pth")
    (out_dir / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    keys = list(history[0].keys())
    np.savetxt(out_dir / "train_history.csv", np.array([[r[k] for k in keys] for r in history]), delimiter=",", header=",".join(keys), comments="")
    mod.save_physical_field_comparison(out_dir, Path(args.field_dir), args.case_id, true[0], pred[0], field_names)
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
