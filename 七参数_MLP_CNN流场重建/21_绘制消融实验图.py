#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""绘制论文用 PVT 消融实验对比图。"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "results" / "pvt_ablation" / "ablation_summary.csv"
OUT_DIR = ROOT / "analysis_results" / "ablation"
OUT_PNG = OUT_DIR / "ablation_field_error_compare.png"


def main() -> None:
    df = pd.read_csv(INPUT)
    # A0 不输出 PVT 场，不能参与场误差柱状对比。
    field_df = df[df["predicts_field"] == True].copy()

    labels = field_df["group"].tolist()
    x = range(len(labels))
    width = 0.35

    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS"]
    plt.rcParams["axes.unicode_minus"] = False

    fig, ax = plt.subplots(figsize=(8.0, 4.6), dpi=220)
    ax.bar([i - width / 2 for i in x], field_df["field_MAE"], width, label="field_MAE", color="#2f6fdd")
    ax.bar([i + width / 2 for i in x], field_df["T_MAE"], width, label="T_MAE / K", color="#20a67a")

    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_ylabel("误差")
    ax.set_title("PVT 消融实验场重建误差对比")
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    ax.legend(frameon=False)

    for i, value in enumerate(field_df["field_MAE"]):
        ax.text(i - width / 2, value + 0.05, f"{value:.3f}", ha="center", va="bottom", fontsize=8)
    for i, value in enumerate(field_df["T_MAE"]):
        ax.text(i + width / 2, value + 0.05, f"{value:.3f}", ha="center", va="bottom", fontsize=8)

    fig.tight_layout()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PNG, bbox_inches="tight")
    print(OUT_PNG)


if __name__ == "__main__":
    main()
