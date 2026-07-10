#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""使用七参数 PI-CNN-CBAM 几何掩码模型预测单组参数性能。"""

from __future__ import annotations

import argparse
from importlib.machinery import SourceFileLoader
from pathlib import Path

import numpy as np
import torch

from common import (
    DEFAULT_BASELINE,
    PARAM_COLS,
    ROOT,
    baseline_from_labels,
    denormalize,
    eta_value,
    load_json,
    normalize,
    read_csv,
    render_fixed_domain_mask,
)


ablation_mod = SourceFileLoader("ablation_pi_model", str(ROOT / "09_消融实验_PI_CNN_CBAM.py")).load_module()
FusionModel = ablation_mod.FusionModel
ParamMLP = ablation_mod.ParamMLP


def load_pi_model(model_dir: Path, device: torch.device):
    stats_path = model_dir.parent / "stats.json"
    if not stats_path.exists():
        raise FileNotFoundError(
            f"未找到归一化统计文件: {stats_path}。"
            "PI-CNN-CBAM模型目录应位于包含 stats.json 的消融实验输出目录下。"
        )
    weight_path = model_dir / "best_model.pth"
    if not weight_path.exists():
        raise FileNotFoundError(f"未找到模型权重: {weight_path}")
    stats = load_json(stats_path)
    # 从模型目录的 config.json 读取架构配置
    config_path = model_dir / "config.json"
    if config_path.exists():
        cfg = load_json(config_path)
        use_cbam = cfg.get("use_cbam", True)
        desc = cfg.get("desc", "")
    else:
        cfg = {}
        use_cbam = True
        desc = ""
    # baseline 模型使用 ParamMLP（纯参数 MLP，不含几何掩码编码器）
    if "基线" in desc or cfg.get("model_type") == "param_mlp":
        model = ParamMLP().to(device)
    else:
        model = FusionModel(use_cbam=use_cbam).to(device)
    model.load_state_dict(torch.load(weight_path, map_location=device))
    model.eval()
    return model, stats


def predict_with_loaded_model(params: dict[str, float], model, stats: dict, device: torch.device, image_size: int) -> dict[str, float]:
    mask = render_fixed_domain_mask(params, image_size=image_size)
    mask_arr = 1.0 - np.asarray(mask, dtype=np.float32) / 255.0
    param_arr = np.asarray([params[name] for name in PARAM_COLS], dtype=np.float32)
    param_norm = normalize(param_arr, stats["param_mean"], stats["param_std"])
    with torch.no_grad():
        pred_norm = model(
            torch.tensor(mask_arr[None, None, :, :], dtype=torch.float32, device=device),
            torch.tensor(param_norm[None, :], dtype=torch.float32, device=device),
        ).cpu().numpy()[0]
    nu, f_value = denormalize(pred_norm, stats["target_mean"], stats["target_std"])
    return {"Nu_pred": float(nu), "f_pred": float(f_value)}


def predict_params(params: dict[str, float], model_dir: Path, image_size: int = 64) -> dict[str, float]:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model, stats = load_pi_model(model_dir, device)
    return predict_with_loaded_model(params, model, stats, device, image_size)


def main() -> None:
    parser = argparse.ArgumentParser(description="PI-CNN-CBAM单组七参数预测")
    parser.add_argument("--model-dir", default=str(ROOT / "ablation_results_1000" / "gp"))
    parser.add_argument("--labels", default=str(ROOT / "samples" / "labels_7param_1000.csv"), help="用于计算eta基准值的标签文件")
    parser.add_argument("--image-size", type=int, default=64)
    parser.add_argument("--Nu0", type=float, default=None, help="手动指定基准Nu；不指定时从--labels读取")
    parser.add_argument("--f0", type=float, default=None, help="手动指定基准f；不指定时从--labels读取")
    for name in PARAM_COLS:
        parser.add_argument(f"--{name}", type=float, default=DEFAULT_BASELINE[name])
    args = parser.parse_args()

    params = {name: float(getattr(args, name)) for name in PARAM_COLS}
    pred = predict_params(params, Path(args.model_dir), args.image_size)
    if args.Nu0 is None or args.f0 is None:
        nu0, f0 = baseline_from_labels(read_csv(Path(args.labels)))
    else:
        nu0, f0 = float(args.Nu0), float(args.f0)
    pred["eta_pred"] = eta_value(pred["Nu_pred"], pred["f_pred"], nu0, f0)
    print("[OK] PI-CNN-CBAM 七参数预测结果")
    print("params:", params)
    print(f"baseline: Nu0={nu0:.6f}, f0={f0:.8f}")
    print(f"Nu_pred={pred['Nu_pred']:.6f}")
    print(f"f_pred={pred['f_pred']:.8f}")
    print(f"eta_pred={pred['eta_pred']:.6f}")


if __name__ == "__main__":
    main()
