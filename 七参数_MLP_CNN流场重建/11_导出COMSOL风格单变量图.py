#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""导出接近 COMSOL 云图风格的单变量长条图。

用于把规则采样场和模型预测场按同一变量、同一色标、同一物理比例导出，
避免训练诊断图因色标、坐标轴和子图布局导致与 COMSOL 截图视觉不一致。
"""

from __future__ import annotations

import argparse
import importlib.util
import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
TRAIN_SCRIPT = ROOT / "08_UNet高精度流场重建训练.py"
PARAM_DIR = PROJECT_ROOT / "七参数_几何掩码代理优化"
LABELS_PATH = PARAM_DIR / "samples" / "labels_7param_1000.csv"
CHORD = 0.01
CHANNEL_CHOICES = ["u", "v", "U", "p", "T"]

sys.path.insert(0, str(PARAM_DIR))
from common import naca_airfoil_points  # noqa: E402


def read_variable(data: np.lib.npyio.NpzFile, variable: str, shape: tuple[int, int]) -> np.ndarray:
    if variable == "U":
        u = data["u"].astype(np.float32)
        v = data["v"].astype(np.float32)
        return np.sqrt(u * u + v * v).reshape(shape)
    return data[variable].reshape(shape)


def load_train_module():
    spec = importlib.util.spec_from_file_location("unet_train_mod", TRAIN_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载训练脚本: {TRAIN_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_physical_grid(field_dir: Path, case_id: int):
    path = field_dir / f"case_{case_id}_full.npz"
    data = np.load(path)
    x = data["x"]
    y = data["y"]
    xs = np.unique(x)
    ys = np.unique(y)
    extent = [float(xs.min()), float(xs.max()), float(ys.min()), float(ys.max())]
    shape = (int(ys.size), int(xs.size))
    domain = data["domain"].reshape(shape)
    return data, extent, domain


def load_case_params(case_id: int, labels_path: Path = LABELS_PATH) -> dict[str, float]:
    labels = pd.read_csv(labels_path)
    row = labels.loc[labels["case_id"].astype(int) == int(case_id)]
    if row.empty:
        raise ValueError(f"标签文件中没有 case_id={case_id}: {labels_path}")
    record = row.iloc[0]
    return {name: float(record[name]) for name in ["Ta", "Twa", "Tb", "Ts", "Tt", "Tad", "theta"]}


def make_airfoil_polygons(params: dict[str, float]) -> list[np.ndarray]:
    """生成与二维 COMSOL 建模脚本一致的 3x8 翼型解析轮廓。"""
    base = naca_airfoil_points(params, chord=CHORD)
    col_pitch = (1.0 + params["Ts"]) * CHORD
    polygons: list[np.ndarray] = []
    for row_index, y_factor in enumerate([-1, 0, 1]):
        stagger = params["Tad"] * CHORD if row_index % 2 != 0 else 0.0
        for col_index in range(8):
            x_shift = col_index * col_pitch + stagger
            y_shift = y_factor * params["Tt"] * CHORD
            shifted = base + np.asarray([x_shift, y_shift], dtype=np.float64)
            center = np.asarray([x_shift + 0.5 * CHORD, y_shift], dtype=np.float64)
            angle = math.radians(params["theta"])
            cos_a, sin_a = math.cos(angle), math.sin(angle)
            rotation = np.asarray([[cos_a, -sin_a], [sin_a, cos_a]], dtype=np.float64)
            polygons.append((shifted - center) @ rotation + center)
    return polygons


def draw_single_field(
    values: np.ndarray,
    domain: np.ndarray,
    extent: list[float],
    out_path: Path,
    cmap: str,
    vmin: float | None,
    vmax: float | None,
    show_solid_outline: bool,
    polygons: list[np.ndarray] | None = None,
) -> None:
    # 按物理尺寸控制画布比例，接近 COMSOL 长条云图。
    x_range = extent[1] - extent[0]
    y_range = extent[3] - extent[2]
    ratio = max(x_range / max(y_range, 1e-12), 1.0)
    fig_w = 12.0
    fig_h = max(1.25, min(3.0, fig_w / ratio))
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=220)
    ax.imshow(values, origin="lower", extent=extent, aspect="equal", cmap=cmap, vmin=vmin, vmax=vmax)
    if show_solid_outline:
        if polygons:
            for poly in polygons:
                closed = np.vstack([poly, poly[0]])
                ax.plot(closed[:, 0], closed[:, 1], color="black", linewidth=0.5)
        else:
            ax.contour(domain, levels=[0.5], origin="lower", extent=extent, colors="black", linewidths=0.45)
    ax.set_axis_off()
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    fig.savefig(out_path, bbox_inches="tight", pad_inches=0)
    plt.close(fig)


def predict_case(mod, model_dir: Path, dataset_path: Path, field_dir: Path, case_id: int):
    data = np.load(dataset_path, allow_pickle=True)
    case_ids = data["case_id"].astype(int)
    matches = np.where(case_ids == case_id)[0]
    if matches.size == 0:
        raise ValueError(f"数据集中没有 case_id={case_id}")
    idx = int(matches[0])

    stats_path = model_dir / "normalization_stats.npz"
    if stats_path.exists():
        stats_npz = np.load(stats_path)
        stats = {key: stats_npz[key] for key in [
            "param_mean", "param_std", "field_mean", "field_std",
            "target_mean", "target_std", "eta_mean", "eta_std",
        ]}
    else:
        # 兼容早期单工况过拟合结果：当时未保存归一化参数，但参数完全由该 case 自身确定。
        one_params = data["params"][idx:idx + 1].astype(np.float32)
        one_fields = data["fields"][idx:idx + 1].astype(np.float32)
        one_targets = data["targets"][idx:idx + 1].astype(np.float32)
        one_eta = data["eta"][idx:idx + 1].astype(np.float32)
        stats = {
            "param_mean": one_params.mean(axis=0),
            "param_std": one_params.std(axis=0) + 1e-6,
            "field_mean": one_fields.mean(axis=(0, 2, 3))[:, None, None],
            "field_std": one_fields.std(axis=(0, 2, 3))[:, None, None] + 1e-6,
            "target_mean": one_targets.mean(axis=0),
            "target_std": one_targets.std(axis=0) + 1e-6,
            "eta_mean": one_eta.mean(axis=0),
            "eta_std": one_eta.std(axis=0) + 1e-6,
        }
    output_hw = tuple(int(x) for x in data["fields"].shape[-2:])
    field_names = [str(x) for x in data["field_names"]]
    params = (data["params"][idx:idx + 1] - stats["param_mean"]) / stats["param_std"]
    mask = mod.load_domain_mask(field_dir, case_id, output_hw)[None].astype(np.float32)
    coords = mod.make_coord_channels(output_hw)[None].astype(np.float32)
    spatial = np.concatenate([mask, coords], axis=1)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = mod.ConditionalUNet(output_hw, output_channels=len(field_names)).to(device)
    checkpoint = model_dir / "best_model.pth"
    if not checkpoint.exists():
        checkpoint = model_dir / "overfit_model.pth"
    model.load_state_dict(torch.load(checkpoint, map_location=device))
    model.eval()
    with torch.no_grad():
        pred, _ = model(
            torch.tensor(params, dtype=torch.float32, device=device),
            torch.tensor(spatial, dtype=torch.float32, device=device),
        )
    pred_raw = pred.cpu().numpy()[0] * stats["field_std"] + stats["field_mean"]
    return pred_raw, field_names


def main() -> None:
    parser = argparse.ArgumentParser(description="导出 COMSOL 风格单变量图")
    parser.add_argument("--case-id", type=int, default=20009)
    parser.add_argument("--variable", choices=CHANNEL_CHOICES, default="T")
    parser.add_argument("--field-dir", default=str(PROJECT_ROOT / "七参数_PDE_PINN尝试" / "field_data_320x96"))
    parser.add_argument("--dataset", default=str(ROOT / "data" / "field_reconstruction_dataset_320x96_first20.npz"))
    parser.add_argument("--model-dir", default=str(ROOT / "results" / "unet_overfit_case_20009_e300"))
    parser.add_argument("--output-dir", default=str(ROOT / "results" / "comsol_style_exports"))
    parser.add_argument("--cmap", default="jet")
    parser.add_argument("--vmin", type=float, default=None)
    parser.add_argument("--vmax", type=float, default=None)
    parser.add_argument("--no-solid-outline", action="store_true")
    parser.add_argument("--truth-only", action="store_true")
    args = parser.parse_args()

    field_dir = Path(args.field_dir)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    data, extent, domain = load_physical_grid(field_dir, args.case_id)
    polygons = make_airfoil_polygons(load_case_params(args.case_id))
    shape = domain.shape
    truth = read_variable(data, args.variable, shape)

    pred = None
    if not args.truth_only:
        mod = load_train_module()
        pred_fields, field_names = predict_case(mod, Path(args.model_dir), Path(args.dataset), field_dir, args.case_id)
        if args.variable not in field_names:
            raise ValueError(f"模型数据集没有 {args.variable} 通道，当前通道: {field_names}")
        pred = pred_fields[field_names.index(args.variable)]

    if args.vmin is None or args.vmax is None:
        if pred is None:
            vmin = float(np.nanmin(truth)) if args.vmin is None else args.vmin
            vmax = float(np.nanmax(truth)) if args.vmax is None else args.vmax
        else:
            both = np.concatenate([truth.ravel(), pred.ravel()])
            vmin = float(np.nanmin(both)) if args.vmin is None else args.vmin
            vmax = float(np.nanmax(both)) if args.vmax is None else args.vmax
    else:
        vmin, vmax = args.vmin, args.vmax

    prefix = f"case_{args.case_id}_{args.variable}"
    draw_single_field(
        truth,
        domain,
        extent,
        out_dir / f"{prefix}_comsol_sample_style.png",
        args.cmap,
        vmin,
        vmax,
        not args.no_solid_outline,
        polygons,
    )
    if pred is not None:
        draw_single_field(
            pred,
            domain,
            extent,
            out_dir / f"{prefix}_pred_style.png",
            args.cmap,
            vmin,
            vmax,
            not args.no_solid_outline,
            polygons,
        )
        draw_single_field(
            pred - truth,
            domain,
            extent,
            out_dir / f"{prefix}_error_style.png",
            "coolwarm",
            None,
            None,
            not args.no_solid_outline,
            polygons,
        )
    print(out_dir)
    print(f"vmin={vmin:.6g}, vmax={vmax:.6g}")


if __name__ == "__main__":
    main()
