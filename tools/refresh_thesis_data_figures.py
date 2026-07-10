#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""重画论文图片汇总目录中的关键数据图。

只使用已有 CSV/JSON 结果，不重新训练、不覆盖模型；输出仍写回论文图片汇总目录，
保持正文中的图片路径不变。
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
IMAGE_DIR = ROOT / "大论文初稿" / "完整论文初稿_图片汇总"
MODEL_ROOT = ROOT / "七参数_MLP_CNN流场重建"


def setup_style() -> None:
    plt.rcParams.update(
        {
            "font.sans-serif": ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"],
            "axes.unicode_minus": False,
            "figure.dpi": 160,
            "savefig.dpi": 220,
            "axes.linewidth": 1.0,
            "axes.grid": True,
            "grid.alpha": 0.25,
            "grid.linestyle": "--",
            "legend.frameon": False,
        }
    )


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def to_float(value: str | None) -> float:
    if value is None or value == "":
        return float("nan")
    return float(value)


def save_figure(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"[OK] {path}")


def plot_global_sensitivity() -> None:
    rows = read_csv(MODEL_ROOT / "analysis_results" / "sensitivity" / "rf_importance.csv")
    parameters = ["Ta", "Twa", "Tb", "Ts", "Tt", "Tad", "theta"]
    labels = {
        "Ta": r"$T_a$",
        "Twa": r"$T_{wa}$",
        "Tb": r"$T_b$",
        "Ts": r"$T_s$",
        "Tt": r"$T_t$",
        "Tad": r"$T_{ad}$",
        "theta": r"$\theta$",
    }
    targets = ["Nu", "f", "eta"]
    colors = {"Nu": "#2563eb", "f": "#dc2626", "eta": "#059669"}
    values = {
        target: {
            row["parameter"]: to_float(row["rf_permutation_importance"])
            for row in rows
            if row["target"] == target
        }
        for target in targets
    }

    order = sorted(parameters, key=lambda p: values["eta"].get(p, 0.0))
    y = np.arange(len(order))
    height = 0.22
    plt.figure(figsize=(9.2, 4.8))
    for offset, target in zip([-height, 0, height], targets):
        data = [values[target].get(param, 0.0) for param in order]
        plt.barh(y + offset, data, height=height, label=target, color=colors[target], alpha=0.88)
    plt.yticks(y, [labels[param] for param in order])
    plt.xlabel("置换重要性")
    plt.title("七参数对 Nu、f 与 η 的全局敏感性排序")
    plt.legend(ncol=3, loc="lower right")
    plt.tight_layout()
    save_figure(IMAGE_DIR / "图3-7_全局敏感性排序图.png")


def plot_local_sensitivity() -> None:
    rows = read_csv(MODEL_ROOT / "analysis_results" / "sensitivity" / "local_perturbation_eta.csv")
    labels = {
        "Ta": r"$T_a$",
        "Twa": r"$T_{wa}$",
        "Tb": r"$T_b$",
        "Ts": r"$T_s$",
        "Tt": r"$T_t$",
        "Tad": r"$T_{ad}$",
        "theta": r"$\theta$",
    }
    rows = sorted(rows, key=lambda r: to_float(r["eta_range"]))
    y = np.arange(len(rows))
    values = [to_float(row["eta_range"]) for row in rows]
    names = [labels[row["parameter"]] for row in rows]
    plt.figure(figsize=(8.6, 4.6))
    bars = plt.barh(y, values, color="#7c3aed", alpha=0.82)
    plt.yticks(y, names)
    plt.xlabel(r"局部扰动引起的 $\eta$ 变化幅度")
    plt.title("DE 最优点附近的局部扰动敏感性")
    for bar, value in zip(bars, values):
        plt.text(value + max(values) * 0.012, bar.get_y() + bar.get_height() / 2, f"{value:.4f}", va="center", fontsize=9)
    plt.xlim(0, max(values) * 1.16)
    plt.tight_layout()
    save_figure(IMAGE_DIR / "图3-8_局部扰动敏感性图.png")


def plot_training_loss() -> None:
    rows = read_csv(MODEL_ROOT / "results" / "unet_pUt_320x96_full_e50" / "train_history.csv")
    epoch = np.array([to_float(row["epoch"]) for row in rows])
    train = np.array([to_float(row["train_loss"]) for row in rows])
    val = np.array([to_float(row["val_loss"]) for row in rows])
    plt.figure(figsize=(7.2, 4.6))
    plt.semilogy(epoch, train, color="#2563eb", linewidth=2.0, label="训练损失")
    plt.semilogy(epoch, val, color="#f97316", linewidth=2.0, label="验证损失")
    best_idx = int(np.nanargmin(val))
    plt.scatter([epoch[best_idx]], [val[best_idx]], color="#dc2626", zorder=4, s=36)
    plt.text(epoch[best_idx], val[best_idx] * 1.10, f"最低验证损失={val[best_idx]:.3f}", fontsize=9)
    plt.xlabel("训练轮次")
    plt.ylabel("损失函数值")
    plt.title("MLP-CNN 流热场重建模型训练收敛曲线")
    plt.legend(loc="upper right")
    plt.tight_layout()
    save_figure(IMAGE_DIR / "图4-2_损失收敛曲线.png")


def plot_kfold() -> None:
    rows = read_csv(MODEL_ROOT / "results" / "pvt_unet_kfold_3_e20" / "kfold_metrics.csv")
    folds = np.array([int(to_float(row["fold"])) for row in rows])
    metrics = [
        ("Nu_R2", r"$Nu$ R²"),
        ("f_R2", r"$f$ R²"),
        ("eta_R2", r"$\eta$ R²"),
    ]
    plt.figure(figsize=(7.4, 4.6))
    for key, label in metrics:
        values = np.array([to_float(row[key]) for row in rows])
        plt.plot(folds, values, marker="o", linewidth=2.0, label=f"{label}，均值={np.nanmean(values):.4f}")
    plt.xticks(folds, [f"Fold {item}" for item in folds])
    plt.ylim(0.94, 0.99)
    plt.xlabel("交叉验证折次")
    plt.ylabel("决定系数 R²")
    plt.title("三折交叉验证结果")
    plt.legend(loc="lower right")
    plt.tight_layout()
    svg_path = IMAGE_DIR / "图4-9a_三折交叉验证结果图.svg"
    png_path = IMAGE_DIR / "图4-9a_三折交叉验证结果图.png"
    plt.savefig(svg_path, bbox_inches="tight", facecolor="white")
    plt.savefig(png_path, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"[OK] {svg_path}")
    print(f"[OK] {png_path}")


def plot_ablation() -> None:
    rows = [row for row in read_csv(MODEL_ROOT / "results" / "pvt_ablation" / "ablation_summary.csv") if row["group"] in {"A0", "A1", "A2", "A3", "A4"}]
    groups = [row["group"] for row in rows]
    x = np.arange(len(groups))

    fig, axes = plt.subplots(2, 2, figsize=(10.6, 7.2))
    ax = axes[0, 0]
    width = 0.22
    for offset, key, label, color in [
        (-width, "Nu_R2", r"$Nu$ R²", "#2563eb"),
        (0, "f_R2", r"$f$ R²", "#dc2626"),
        (width, "eta_R2", r"$\eta$ R²", "#059669"),
    ]:
        ax.bar(x + offset, [to_float(row[key]) for row in rows], width=width, label=label, color=color, alpha=0.88)
    ax.set_xticks(x, groups)
    ax.set_ylim(0.94, 0.99)
    ax.set_ylabel("R²")
    ax.set_title("标量性能预测")
    ax.legend(ncol=3, fontsize=9)

    panels = [
        (axes[0, 1], "p_MAE", "压力场 MAE / Pa", "#0891b2"),
        (axes[1, 0], "U_MAE", "速度场 MAE / (m/s)", "#f97316"),
        (axes[1, 1], "T_MAE", "温度场 MAE / K", "#16a34a"),
    ]
    for ax, key, title, color in panels:
        valid_groups = []
        valid_values = []
        for group, row in zip(groups, rows):
            value = to_float(row[key])
            if np.isfinite(value):
                valid_groups.append(group)
                valid_values.append(value)
        bars = ax.bar(valid_groups, valid_values, color=color, alpha=0.86)
        ax.set_title(title)
        ax.set_ylabel("MAE")
        for bar, value in zip(bars, valid_values):
            ax.text(bar.get_x() + bar.get_width() / 2, value, f"{value:.3f}", ha="center", va="bottom", fontsize=8)
        if valid_values:
            ax.set_ylim(0, max(valid_values) * 1.22)

    fig.suptitle("A0-A4 消融实验结果：性能预测与流热场重建误差", fontsize=15, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(IMAGE_DIR / "图4-9b_A0-A4消融实验结果图.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"[OK] {IMAGE_DIR / '图4-9b_A0-A4消融实验结果图.png'}")


def plot_de_convergence() -> None:
    rows = read_csv(MODEL_ROOT / "optimization_results" / "mlp_cnn_de_multiloss_e10" / "de_history.csv")
    generation = np.array([to_float(row["generation"]) for row in rows])
    best_eta = np.array([to_float(row["best_eta"]) for row in rows])
    plt.figure(figsize=(7.2, 4.6))
    plt.plot(generation, best_eta, color="#b91c1c", linewidth=2.4)
    plt.scatter([generation[-1]], [best_eta[-1]], color="#b91c1c", s=36, zorder=3)
    plt.text(generation[-1] * 0.62, best_eta[-1] - 0.002, f"最终最优 η={best_eta[-1]:.4f}", fontsize=10)
    plt.xlabel("迭代代数")
    plt.ylabel(r"当前最优 $\eta$")
    plt.title("差分进化优化收敛曲线")
    plt.tight_layout()
    save_figure(IMAGE_DIR / "图4-10_DE收敛曲线.png")


def write_manifest() -> None:
    manifest = {
        "updated_figures": [
            "图3-7_全局敏感性排序图.png",
            "图3-8_局部扰动敏感性图.png",
            "图4-2_损失收敛曲线.png",
            "图4-9a_三折交叉验证结果图.svg",
            "图4-9a_三折交叉验证结果图.png",
            "图4-9b_A0-A4消融实验结果图.png",
            "图4-10_DE收敛曲线.png",
        ],
        "data_sources": {
            "sensitivity": str(MODEL_ROOT / "analysis_results" / "sensitivity"),
            "training": str(MODEL_ROOT / "results" / "unet_pUt_320x96_full_e50" / "train_history.csv"),
            "kfold": str(MODEL_ROOT / "results" / "pvt_unet_kfold_3_e20" / "kfold_metrics.csv"),
            "ablation": str(MODEL_ROOT / "results" / "pvt_ablation" / "ablation_summary.csv"),
            "de": str(MODEL_ROOT / "optimization_results" / "mlp_cnn_de_multiloss_e10" / "de_history.csv"),
        },
    }
    path = IMAGE_DIR / "数据图重绘说明_20260710.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] {path}")


def main() -> None:
    setup_style()
    plot_global_sensitivity()
    plot_local_sensitivity()
    plot_training_loss()
    plot_kfold()
    plot_ablation()
    plot_de_convergence()
    write_manifest()


if __name__ == "__main__":
    main()
