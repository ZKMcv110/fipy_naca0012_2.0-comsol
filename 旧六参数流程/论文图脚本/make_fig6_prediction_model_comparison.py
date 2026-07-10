#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = ROOT / "ai_cnn_model_results"
OUT_DIR = ROOT / "paper_figures_svg"


def setup_matplotlib() -> None:
    plt.rcParams["font.sans-serif"] = [
        "Microsoft YaHei",
        "SimHei",
        "Noto Sans CJK SC",
        "Arial Unicode MS",
        "DejaVu Sans",
    ]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["svg.fonttype"] = "none"
    plt.rcParams["axes.grid"] = False


def r2_score(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    return 1.0 - ss_res / ss_tot


def scatter_panel(ax: plt.Axes, df: pd.DataFrame, target: str, color: str) -> None:
    true = df[f"true_{target}"].to_numpy(float)
    pred = df[f"pred_{target}"].to_numpy(float)
    lo = min(true.min(), pred.min())
    hi = max(true.max(), pred.max())
    pad = (hi - lo) * 0.08
    lo -= pad
    hi += pad

    ax.scatter(true, pred, s=24, color=color, alpha=0.75, edgecolor="white", linewidth=0.45)
    ax.plot([lo, hi], [lo, hi], color="#dc2626", lw=1.3, ls="--", label="理想线")
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_xlabel(f"CFD 真实值 {target}")
    ax.set_ylabel(f"预测值 {target}")
    ax.text(
        0.04,
        0.94,
        f"{target}: R²={r2_score(true, pred):.3f}",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=9.0,
        bbox=dict(boxstyle="round,pad=0.22", facecolor="white", edgecolor="#d8dee9", alpha=0.92),
    )
    ax.legend(frameon=False, loc="lower right")
    ax.grid(False)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)


def bar_panel(ax: plt.Axes, comparison: pd.DataFrame, metric: str, ylabel: str, ylim: tuple[float, float] | None = None) -> None:
    models = ["MLP", "Multimodal-Fusion"]
    targets = ["Nu", "f"]
    colors = {"MLP": "#2f7d32", "Multimodal-Fusion": "#1f5fd0"}
    labels = {"MLP": "MLP", "Multimodal-Fusion": "多模态模型"}

    width = 0.34
    x = np.arange(len(targets))
    for idx, model in enumerate(models):
        values = []
        for target in targets:
            row = comparison[(comparison["model"] == model) & (comparison["target"] == target)].iloc[0]
            values.append(float(row[metric]))
        offset = (idx - 0.5) * width
        bars = ax.bar(x + offset, values, width, label=labels[model], color=colors[model])
        for bar, val in zip(bars, values):
            text = f"{val:.3f}" if metric == "R2" else f"{val:.2f}"
            ax.text(bar.get_x() + bar.get_width() / 2, val, text, ha="center", va="bottom", fontsize=8.2)

    ax.set_xticks(x, targets)
    ax.set_ylabel(ylabel)
    if ylim:
        ax.set_ylim(*ylim)
    ax.grid(False)
    ax.legend(frameon=False, loc="best")
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)


def main() -> None:
    setup_matplotlib()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    pred_path = RESULTS_DIR / "multimodal_feature_predictions.csv"
    if not pred_path.exists():
        pred_path = RESULTS_DIR / "test_predictions.csv"
    comparison_path = RESULTS_DIR / "paper_table8_model_comparison.csv"

    pred = pd.read_csv(pred_path)
    comparison = pd.read_csv(comparison_path)

    fig, axes = plt.subplots(2, 2, figsize=(10.8, 7.0), dpi=180)
    scatter_panel(axes[0, 0], pred, "Nu", "#1f77b4")
    scatter_panel(axes[0, 1], pred, "f", "#f28e2b")
    bar_panel(axes[1, 0], comparison, "R2", "R²", (0.90, 1.0))
    bar_panel(axes[1, 1], comparison, "MAPE_percent", "MAPE / %", (0, 3.05))

    axes[1, 0].set_title("预测精度对比", fontsize=10.5, color="#083b91", pad=5)
    axes[1, 1].set_title("预测误差对比", fontsize=10.5, color="#083b91", pad=5)

    fig.tight_layout()
    fig.savefig(OUT_DIR / "Fig6_Prediction_and_MLP_Comparison.png", dpi=300)
    fig.savefig(OUT_DIR / "Fig6_Prediction_and_MLP_Comparison.svg")
    plt.close(fig)
    print(f"Saved: {OUT_DIR / 'Fig6_Prediction_and_MLP_Comparison.svg'}")


if __name__ == "__main__":
    main()
