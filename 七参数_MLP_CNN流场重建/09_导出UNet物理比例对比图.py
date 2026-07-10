#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""为已训练的条件 U-Net 导出 COMSOL 物理比例对比图。"""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader


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
    parser = argparse.ArgumentParser(description="导出 U-Net 物理比例重建对比图")
    parser.add_argument("--model-dir", default=str(ROOT / "results" / "unet_mask_field_e5"))
    parser.add_argument("--dataset", default=str(ROOT / "data" / "field_reconstruction_dataset_full.npz"))
    parser.add_argument("--field-dir", default=str(PROJECT_ROOT / "七参数_PDE_PINN尝试" / "field_data"))
    parser.add_argument("--max-cases", type=int, default=3)
    args = parser.parse_args()

    mod = load_train_module()
    model_dir = Path(args.model_dir)
    field_dir = Path(args.field_dir)
    stats_npz = np.load(model_dir / "normalization_stats.npz")
    stats = {key: stats_npz[key] for key in [
        "param_mean", "param_std", "field_mean", "field_std",
        "target_mean", "target_std", "eta_mean", "eta_std",
    ]}

    data = np.load(args.dataset, allow_pickle=True)
    arrays = {name: data[name] for name in ["case_id", "params", "fields", "targets", "eta"]}
    field_names = [str(x) for x in data["field_names"]]
    output_hw = tuple(int(x) for x in arrays["fields"].shape[-2:])
    _, _, test_idx = mod.split_indices(arrays["params"].shape[0], 42)
    case_ids = [int(arrays["case_id"][idx]) for idx in test_idx[: args.max_cases]]
    masks = {case_id: mod.load_domain_mask(field_dir, case_id, output_hw) for case_id in case_ids}
    coords = mod.make_coord_channels(output_hw)
    # 只对指定测试样本构建小数据集，保持和训练脚本一致的数据处理口径。
    selected_indices = np.asarray(test_idx[: args.max_cases], dtype=np.int64)
    loader = DataLoader(mod.FieldMaskDataset(arrays, selected_indices, stats, masks, coords), batch_size=1)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = mod.ConditionalUNet(output_hw, output_channels=len(field_names)).to(device)
    model.load_state_dict(torch.load(model_dir / "best_model.pth", map_location=device))
    model.eval()

    with torch.no_grad():
        for batch in loader:
            case_id = int(batch["case_id"].item())
            pred_field, _ = model(batch["params"].to(device), batch["spatial"].to(device))
            pred = pred_field.cpu().numpy() * stats["field_std"] + stats["field_mean"]
            true = batch["fields"].numpy() * stats["field_std"] + stats["field_mean"]
            mod.save_physical_field_comparison(model_dir, field_dir, case_id, true[0], pred[0], field_names)
            print(model_dir / f"case_{case_id}_physical_compare.png")


if __name__ == "__main__":
    main()
