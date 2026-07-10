#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""导出当前论文所需的真实图文件与可复核数据，不修改论文正文。"""

from __future__ import annotations

import csv
import importlib.util
import json
import shutil
from datetime import datetime
from pathlib import Path
from types import ModuleType

import matplotlib.pyplot as plt
import numpy as np
import torch
from torch.utils.data import DataLoader


ROOT = Path(__file__).resolve().parents[1]
DESKTOP_ROOT = Path("D:/Desktop/大论文初稿")
MODEL_ROOT = ROOT / "七参数_MLP_CNN流场重建"
RESULT_DIR = MODEL_ROOT / "results/unet_pUt_320x96_full_e50"
DATASET = MODEL_ROOT / "data/field_reconstruction_dataset_320x96_full_pUt.npz"
FIELD_DIR = ROOT / "七参数_PDE_PINN尝试/field_data_320x96"
TRAIN_SCRIPT = MODEL_ROOT / "08_UNet高精度流场重建训练.py"
SOURCE_FIGURES = DESKTOP_ROOT / "论文图表补全/figures"


def unique_output_dir() -> Path:
    base = DESKTOP_ROOT / "论文图片与数据交付_20260710"
    if not base.exists():
        return base
    return base.with_name(base.name + "_" + datetime.now().strftime("%H%M%S"))


def load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("unet_export_source", TRAIN_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载训练脚本: {TRAIN_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_test_predictions(module: ModuleType) -> dict[str, np.ndarray | list[str]]:
    with np.load(DATASET, allow_pickle=True) as data:
        arrays = {name: data[name] for name in ["case_id", "params", "fields", "targets", "eta"]}
        field_names = [str(item) for item in data["field_names"]]
        nu0, f0 = float(data["nu0"]), float(data["f0"])
    with np.load(RESULT_DIR / "normalization_stats.npz") as stats_file:
        stats = {name: stats_file[name] for name in stats_file.files if name not in {"nu0", "f0", "output_hw"}}
        output_hw = tuple(int(value) for value in stats_file["output_hw"])
    _, _, test_idx = module.split_indices(arrays["params"].shape[0], 42)
    coords = module.make_coord_channels(output_hw)
    test_case_ids = arrays["case_id"][test_idx]
    masks = {int(case_id): module.load_domain_mask(FIELD_DIR, int(case_id), output_hw) for case_id in test_case_ids}
    dataset = module.FieldMaskDataset(arrays, test_idx, stats, masks, coords)
    loader = DataLoader(dataset, batch_size=2, shuffle=False)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = module.ConditionalUNet(output_hw, output_channels=len(field_names)).to(device)
    try:
        state = torch.load(RESULT_DIR / "best_model.pth", map_location=device, weights_only=True)
    except TypeError:
        state = torch.load(RESULT_DIR / "best_model.pth", map_location=device)
    model.load_state_dict(state)
    true_t, pred_t, true_f, pred_f, case_ids = module.collect_predictions(model, loader, stats, device)
    return {
        "true_t": true_t,
        "pred_t": pred_t,
        "true_f": true_f,
        "pred_f": pred_f,
        "case_ids": case_ids,
        "field_names": field_names,
        "eta_true": module.eta_np(true_t[:, 0], true_t[:, 1], nu0, f0),
        "eta_pred": module.eta_np(pred_t[:, 0], pred_t[:, 1], nu0, f0),
    }


def save_test_predictions(path: Path, predictions: dict[str, np.ndarray | list[str]]) -> None:
    true_t = predictions["true_t"]
    pred_t = predictions["pred_t"]
    eta_true = predictions["eta_true"]
    eta_pred = predictions["eta_pred"]
    rows = np.column_stack([true_t[:, 0], pred_t[:, 0], true_t[:, 1], pred_t[:, 1], eta_true, eta_pred])
    np.savetxt(path, rows, delimiter=",", header="Nu_true,Nu_pred,f_true,f_pred,eta_true,eta_pred", comments="")


def save_scatter(path: Path, y_true: np.ndarray, y_pred: np.ndarray, symbol: str) -> None:
    figure, axis = plt.subplots(figsize=(6.2, 5.2), dpi=180)
    axis.scatter(y_true, y_pred, s=24, alpha=0.72, color="#1769aa", edgecolors="none")
    low = float(min(y_true.min(), y_pred.min()))
    high = float(max(y_true.max(), y_pred.max()))
    axis.plot([low, high], [low, high], "--", color="#c43c39", linewidth=1.4, label="y = x")
    axis.set_xlabel(f"CFD {symbol}")
    axis.set_ylabel(f"Predicted {symbol}")
    axis.grid(True, linestyle="--", linewidth=0.55, alpha=0.35)
    axis.legend(frameon=False)
    figure.tight_layout()
    figure.savefig(path, bbox_inches="tight")
    plt.close(figure)


def representative_index(predictions: dict[str, np.ndarray | list[str]]) -> int:
    true_f = predictions["true_f"]
    pred_f = predictions["pred_f"]
    channel_scale = np.std(true_f, axis=(0, 2, 3)) + 1e-8
    normalized_error = np.mean(np.abs(true_f - pred_f) / channel_scale[None, :, None, None], axis=(1, 2, 3))
    order = np.argsort(normalized_error)
    return int(order[len(order) // 2])


def load_physical_grid(case_id: int) -> tuple[list[float], np.ndarray, dict[str, np.ndarray]]:
    with np.load(FIELD_DIR / f"case_{case_id}_full.npz") as data:
        x, y = data["x"], data["y"]
        width, height = np.unique(x).size, np.unique(y).size
        extent = [float(x.min()), float(x.max()), float(y.min()), float(y.max())]
        domain = data["domain"].reshape(height, width)
        raw = {name: data[name].copy() for name in ["x", "y", "u", "v", "p", "T", "domain"]}
    return extent, domain, raw


def save_pvt_comparison(path: Path, true_field: np.ndarray, pred_field: np.ndarray, names: list[str], extent: list[float], domain: np.ndarray) -> None:
    figure, axes = plt.subplots(3, 3, figsize=(13.5, 6.5), constrained_layout=True)
    solid = np.ma.masked_where(domain <= 0, domain)
    colormaps = {"p": "viridis", "U": "turbo", "T": "inferno"}
    for row, name in enumerate(names):
        error = pred_field[row] - true_field[row]
        for axis, values, title in zip(axes[row], [true_field[row], pred_field[row], error], ["CFD", "Prediction", "Error"]):
            image = axis.imshow(values, origin="lower", extent=extent, aspect="equal", cmap=colormaps[name])
            axis.imshow(solid, origin="lower", extent=extent, aspect="equal", cmap="gray_r", alpha=0.6)
            axis.set_title(f"{name} {title}")
            axis.set_xlabel("x / m")
            axis.set_ylabel("y / m")
            figure.colorbar(image, ax=axis, fraction=0.028, pad=0.012)
    figure.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(figure)


def save_error_field(path: Path, values: np.ndarray, name: str, unit: str, extent: list[float], domain: np.ndarray) -> None:
    figure, axis = plt.subplots(figsize=(11.5, 3.2), dpi=180)
    error = np.abs(values)
    image = axis.imshow(error, origin="lower", extent=extent, aspect="equal", cmap="magma")
    solid = np.ma.masked_where(domain <= 0, domain)
    axis.imshow(solid, origin="lower", extent=extent, aspect="equal", cmap="gray_r", alpha=0.65)
    axis.set_xlabel("x / m")
    axis.set_ylabel("y / m")
    axis.set_title(f"Absolute {name} error")
    colorbar = figure.colorbar(image, ax=axis, fraction=0.022, pad=0.018)
    colorbar.set_label(unit)
    figure.tight_layout()
    figure.savefig(path, bbox_inches="tight")
    plt.close(figure)


def save_representative_field_csv(path: Path, raw: dict[str, np.ndarray]) -> None:
    columns = [raw[name] for name in ["x", "y", "p", "u", "v", "T", "domain"]]
    rows = np.column_stack(columns)
    np.savetxt(path, rows, delimiter=",", header="x,y,p,u,v,T,region", comments="")


def save_training_and_de_figures(image_dir: Path, data_dir: Path) -> None:
    history = np.genfromtxt(RESULT_DIR / "train_history.csv", delimiter=",", names=True)
    np.savetxt(data_dir / "train_loss.csv", np.column_stack([history["epoch"], history["train_loss"], history["val_loss"]]),
               delimiter=",", header="epoch,train_loss,val_loss", comments="")
    figure, axis = plt.subplots(figsize=(7.2, 4.6), dpi=180)
    axis.semilogy(history["epoch"], history["train_loss"], label="Train loss", linewidth=1.8)
    axis.semilogy(history["epoch"], history["val_loss"], label="Validation loss", linewidth=1.8)
    axis.set(xlabel="Epoch", ylabel="Loss")
    axis.grid(True, which="both", linestyle="--", linewidth=0.5, alpha=0.35)
    axis.legend(frameon=False)
    figure.tight_layout()
    figure.savefig(image_dir / "图4-2_损失收敛曲线.png", bbox_inches="tight")
    plt.close(figure)

    source = MODEL_ROOT / "optimization_results/mlp_cnn_de_multiloss_e10/de_history.csv"
    shutil.copy2(source, data_dir / "de_history.csv")
    de = np.genfromtxt(source, delimiter=",", names=True)
    figure, axis = plt.subplots(figsize=(7.2, 4.6), dpi=180)
    axis.plot(de["generation"], de["best_eta"], color="#b33b2e", linewidth=2.0)
    axis.set(xlabel="Generation", ylabel="Best eta")
    axis.grid(True, linestyle="--", linewidth=0.5, alpha=0.35)
    figure.tight_layout()
    figure.savefig(image_dir / "图4-10_DE收敛曲线.png", bbox_inches="tight")
    plt.close(figure)


def copy_static_figures(image_dir: Path) -> dict[str, str]:
    sources = {
        "图1-2_技术路线图.png": SOURCE_FIGURES / "图1-2_本文研究技术路线图.png",
        "图3-1_二维计算域.png": SOURCE_FIGURES / "图3-1_翼型柱阵列散热器二维计算域示意图.png",
        "图3-2_二维网格图.png": SOURCE_FIGURES / "图3-2_fig3_3_mesh_comsol.png",
        "图3-3_PVT数据集构建流程图.png": SOURCE_FIGURES / "图3-6_PVT三通道流热场数据集构建流程图.png",
        "图3-4_速度场云图.png": SOURCE_FIGURES / "图3-7_fig3_7_velocity_field.png",
        "图3-5_压力场云图.png": SOURCE_FIGURES / "图3-8_fig3_9_pressure_field.png",
        "图3-6_温度场云图.png": SOURCE_FIGURES / "图3-9_fig3_8_temperature_field.png",
        "图3-7_全局敏感性排序图.png": MODEL_ROOT / "analysis_results/sensitivity/sensitivity_bar_eta.png",
        "图3-8_局部扰动敏感性图.png": MODEL_ROOT / "analysis_results/sensitivity/local_perturbation_eta.png",
        "图4-1_MLP-CNN模型结构图.png": SOURCE_FIGURES / "图4-1_MLP-CNN流热场重建代理模型总体架构图.png",
        "图4-11_优化结构速度场.png": MODEL_ROOT / "validation_results/mlp_cnn_de_multiloss_e10/comsol/case_1/cfd_solution/velocity_magnitude.png",
        "图4-12_优化结构压力场.png": MODEL_ROOT / "validation_results/mlp_cnn_de_multiloss_e10/comsol/case_1/cfd_solution/pressure.png",
        "图4-13_优化结构温度场.png": MODEL_ROOT / "validation_results/mlp_cnn_de_multiloss_e10/comsol/case_1/cfd_solution/temperature.png",
        "图5-1_三维模型图.png": ROOT / "comsol_3d_airfoil_radiator/generated_chip_airfoil_heat_sink/chip_mlp_cnn_de_multiloss_e10/exports_clean_with_legends/chip_mlp_cnn_de_multiloss_e10_appearance.png",
        "图5-2_三维网格图.png": ROOT / "comsol_3d_airfoil_radiator/generated_chip_airfoil_heat_sink/chip_mlp_cnn_de_multiloss_e10/exports_clean_with_legends/chip_mlp_cnn_de_multiloss_e10_mesh.png",
    }
    manifest = {}
    for output_name, source in sources.items():
        if not source.exists():
            raise FileNotFoundError(source)
        shutil.copy2(source, image_dir / output_name)
        manifest[output_name] = str(source)
    return manifest


def save_sensitivity_data(data_dir: Path) -> None:
    with (MODEL_ROOT / "analysis_results/sensitivity/rf_importance.csv").open(encoding="utf-8-sig", newline="") as handle:
        global_data = list(csv.DictReader(handle))
    with (data_dir / "sensitivity_global.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["parameter", "importance"])
        for row in global_data:
            if row["target"] == "eta":
                writer.writerow([row["parameter"], row["rf_permutation_importance"]])
    with (MODEL_ROOT / "analysis_results/sensitivity/local_perturbation_eta.csv").open(encoding="utf-8-sig", newline="") as handle:
        local = list(csv.DictReader(handle))
    with (data_dir / "sensitivity_local.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["parameter", "eta_range"])
        for row in local:
            writer.writerow([row["parameter"], row["eta_range"]])


def save_3d_comparison(image_dir: Path, field: str, title: str) -> None:
    baseline = ROOT / f"comsol_3d_airfoil_radiator/generated_chip_airfoil_heat_sink/chip_baseline_reference/exports_comparison/chip_baseline_reference_{field}.png"
    optimized = ROOT / f"comsol_3d_airfoil_radiator/generated_chip_airfoil_heat_sink/chip_mlp_cnn_de_multiloss_e10/exports_comparison/chip_mlp_cnn_de_multiloss_e10_{field}.png"
    figure, axes = plt.subplots(1, 2, figsize=(14, 5.2), dpi=160)
    for axis, path, label in zip(axes, [baseline, optimized], ["Baseline", "Optimized"]):
        axis.imshow(plt.imread(path))
        axis.set_title(label, fontsize=14)
        axis.axis("off")
    shared_ranges = {"temperature": "293.15-381 K", "velocity": "0-0.09 m/s", "pressure": "0-0.02 Pa"}
    figure.suptitle(f"Shared color range: {shared_ranges[field]}", fontsize=12)
    figure.tight_layout(pad=0.5)
    figure.savefig(image_dir / title, bbox_inches="tight", facecolor="white")
    plt.close(figure)


def save_baseline_and_grid_data(data_dir: Path) -> None:
    baseline = {
        "二维几何baseline": {"Ta": 0.0, "Twa": 0.4, "Tb": 0.12, "Ts": 1.1, "Tt": 0.85, "Tad": 0.0, "theta": 0.0},
        "二维eta归一化参考": {
            "Nu0": 30.36612319946289, "f0": 0.09299600124359131, "eta0": 1.0,
            "说明": "由现有代码按前六参数寻找最接近标准baseline的样本得到；并非标准baseline直接复算值。",
            "reference_case_id": 30232,
            "reference_theta": 9.760765974386846,
        },
        "三维baseline": {"Ta": 0.0, "Twa": 0.4, "Tb": 0.12, "Ts": 1.1, "Tt": 0.85, "Tad": 0.0, "theta": 0.0,
                         "Nu3D0": 39.72984480163116, "f3D0": 2.5818406177419426, "eta3D0": 1.0},
    }
    (data_dir / "baseline_reference.json").write_text(json.dumps(baseline, ensure_ascii=False, indent=2), encoding="utf-8")
    grid_dir = MODEL_ROOT / "analysis_results/grid_independence"
    for name in ["grid_independence_2d_real_results.csv", "grid_independence_3d_real_results.csv", "grid_independence_summary.csv", "grid_independence_summary.md"]:
        shutil.copy2(grid_dir / name, data_dir / name)


def write_readme(output_dir: Path, manifest: dict[str, str], representative_case: int) -> None:
    lines = [
        "# 论文图片与数据交付说明", "",
        "本目录未修改论文正文。CFD 云图和三维场均来自现有 COMSOL 导出或真实场数据；预测散点图与误差场由已训练模型重新推理生成。", "",
        f"- 代表性测试工况：case_id={representative_case}",
        "- `region`：0 为空气域，1 为固体域。",
        "- `de_history.csv` 原始训练链只记录 generation 与 best_eta，未记录每代 best_Nu、best_f，未补造空缺值。",
        "- 当前二维和三维粗/中/细网格结果均未满足全部判据，论文不能写成网格无关性已通过。", "",
        "## 静态图片来源", "",
    ]
    lines.extend(f"- `{name}`：`{source}`" for name, source in manifest.items())
    (output_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    output_dir = unique_output_dir()
    image_dir, data_dir = output_dir / "图片", output_dir / "数据"
    image_dir.mkdir(parents=True)
    data_dir.mkdir(parents=True)
    manifest = copy_static_figures(image_dir)
    save_training_and_de_figures(image_dir, data_dir)
    save_sensitivity_data(data_dir)
    save_baseline_and_grid_data(data_dir)

    module = load_module()
    predictions = load_test_predictions(module)
    save_test_predictions(data_dir / "test_predictions.csv", predictions)
    save_scatter(image_dir / "图4-3_Nu预测散点图.png", predictions["true_t"][:, 0], predictions["pred_t"][:, 0], "Nu")
    save_scatter(image_dir / "图4-4_f预测散点图.png", predictions["true_t"][:, 1], predictions["pred_t"][:, 1], "f")
    save_scatter(image_dir / "图4-5_eta预测散点图.png", predictions["eta_true"], predictions["eta_pred"], "eta")

    index = representative_index(predictions)
    case_id = int(predictions["case_ids"][index])
    extent, domain, raw = load_physical_grid(case_id)
    true_field, pred_field = predictions["true_f"][index], predictions["pred_f"][index]
    names = list(predictions["field_names"])
    save_pvt_comparison(image_dir / "图4-6_PVT重建对比图.png", true_field, pred_field, names, extent, domain)
    units = {"p": "Pa", "U": "m/s", "T": "K"}
    output_names = {"p": "图4-7_压力误差图.png", "U": "图4-8_速度误差图.png", "T": "图4-9_温度误差图.png"}
    for channel, name in enumerate(names):
        save_error_field(image_dir / output_names[name], pred_field[channel] - true_field[channel], name, units[name], extent, domain)
    save_representative_field_csv(data_dir / f"case_{case_id}_真实场数据.csv", raw)

    save_3d_comparison(image_dir, "temperature", "图5-3_三维温度场对比图.png")
    save_3d_comparison(image_dir, "velocity", "图5-4_三维速度场对比图.png")
    save_3d_comparison(image_dir, "pressure", "图5-5_三维压力场对比图.png")
    write_readme(output_dir, manifest, case_id)
    print(f"[完成] 交付目录: {output_dir}")


if __name__ == "__main__":
    main()
