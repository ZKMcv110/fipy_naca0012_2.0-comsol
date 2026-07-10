"""从已有 COMSOL 标量结果生成论文证据图。

该脚本只读取 `consol_cfddata/labels.csv` 和三维后处理 CSV，
不重新计算 COMSOL，不修改原始数据。用途是把云图之外的数值结果
整理为分布图、相关性图和三维指标对比图，增强论文证据链。
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[2]
TWO_D_LABELS = ROOT / "consol_cfddata" / "labels.csv"
THREE_D_SUMMARY = (
    ROOT
    / "comsol_3d_airfoil_radiator"
    / "generated_pillar_heat_sink"
    / "results"
    / "pillar_heat_sink_summary.csv"
)
OUT_DIR = ROOT / "大论文初稿" / "figures"

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["svg.fonttype"] = "none"


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def as_float(rows: list[dict[str, str]], key: str) -> list[float]:
    values: list[float] = []
    for row in rows:
        text = row.get(key, "")
        if text:
            values.append(float(text))
    return values


def save_two_d_scalar_evidence(rows: list[dict[str, str]]) -> Path:
    nu = as_float(rows, "Nu")
    f_values = as_float(rows, "f")
    delta_p = as_float(rows, "delta_p")
    delta_t = as_float(rows, "delta_T")

    fig, axes = plt.subplots(2, 2, figsize=(10, 7))
    fig.subplots_adjust(wspace=0.28, hspace=0.36)

    axes[0, 0].hist(nu, bins=24, color="#4477AA", edgecolor="white")
    axes[0, 0].set_title("Nu分布")
    axes[0, 0].set_xlabel("Nu")
    axes[0, 0].set_ylabel("样本数")

    axes[0, 1].hist(f_values, bins=24, color="#EE7733", edgecolor="white")
    axes[0, 1].set_title("f分布")
    axes[0, 1].set_xlabel("f")
    axes[0, 1].set_ylabel("样本数")

    axes[1, 0].scatter(f_values, nu, s=14, alpha=0.72, color="#228833")
    axes[1, 0].set_title("Nu-f权衡关系")
    axes[1, 0].set_xlabel("f")
    axes[1, 0].set_ylabel("Nu")

    axes[1, 1].scatter(delta_p, delta_t, s=14, alpha=0.72, color="#AA3377")
    axes[1, 1].set_title("压降与固体平均温升关系")
    axes[1, 1].set_xlabel("压降/Pa")
    axes[1, 1].set_ylabel("翼型管平均温升/K")

    for ax in axes.ravel():
        ax.grid(True, alpha=0.25, linewidth=0.6)

    output_path = OUT_DIR / "fig3_14_comsol_scalar_evidence.svg"
    fig.savefig(output_path, format="svg", bbox_inches="tight")
    plt.close(fig)
    return output_path


def save_three_d_numeric_evidence(rows: list[dict[str, str]]) -> Path:
    display_names = {
        "baseline": "基准结构",
        "optimal": "过渡结构",
        "optimal_2d": "二维最优三维化",
    }
    rows = [row for row in rows if row.get("case") in display_names]
    names = [display_names[row["case"]] for row in rows]
    metrics = [
        ("t_chip_avg_k", "芯片平均温度/K", "#4477AA"),
        ("t_chip_max_k", "芯片最高温度/K", "#66CCEE"),
        ("r_th_k_per_w", "等效热阻/(K/W)", "#228833"),
        ("delta_p_pa", "压降/Pa", "#EE7733"),
    ]

    fig, axes = plt.subplots(2, 2, figsize=(10, 7))
    fig.subplots_adjust(wspace=0.34, hspace=0.42)

    for ax, (key, title, color) in zip(axes.ravel(), metrics):
        values = [float(row[key]) for row in rows]
        ax.bar(names, values, color=color, width=0.58)
        ax.set_title(title)
        ax.tick_params(axis="x", labelrotation=12)
        ax.grid(True, axis="y", alpha=0.25, linewidth=0.6)
        for index, value in enumerate(values):
            ax.text(index, value, f"{value:.4g}", ha="center", va="bottom", fontsize=8)

    output_path = OUT_DIR / "fig5_8_3d_numeric_evidence.svg"
    fig.savefig(output_path, format="svg", bbox_inches="tight")
    plt.close(fig)
    return output_path


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    two_d_rows = read_rows(TWO_D_LABELS)
    three_d_rows = read_rows(THREE_D_SUMMARY)
    outputs = [
        save_two_d_scalar_evidence(two_d_rows),
        save_three_d_numeric_evidence(three_d_rows),
    ]
    for output in outputs:
        print(output)


if __name__ == "__main__":
    main()
