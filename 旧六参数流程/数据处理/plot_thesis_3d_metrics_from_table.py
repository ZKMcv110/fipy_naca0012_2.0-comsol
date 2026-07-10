"""根据第5章当前表5-5数据生成三维指标柱状图。

注意：该脚本读取 `大论文初稿/三维第5章暂用结果.csv`。
该CSV当前是第5章代表性优化构型结果，不代表第4章二维最优参数的真实三维复算结果。
后续重新计算真实三维模型后，应先替换CSV，再重新运行本脚本。
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "大论文初稿" / "三维第5章暂用结果.csv"
OUT_DIR = ROOT / "大论文初稿" / "figures"

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["svg.fonttype"] = "none"


def read_rows() -> list[dict[str, str]]:
    with DATA_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def add_bar_labels(ax, values: list[float], fmt: str) -> None:
    span = max(values) - min(values)
    offset = span * 0.04 if span > 0 else max(values) * 0.002
    for index, value in enumerate(values):
        ax.text(index, value + offset, fmt.format(value), ha="center", va="bottom", fontsize=8)


def main() -> None:
    rows = read_rows()
    names = [row["case"] for row in rows]
    metrics = [
        ("t_chip_avg_k", "芯片平均温度/K", "#4477AA", "{:.3f}"),
        ("t_chip_max_k", "芯片最高温度/K", "#66CCEE", "{:.3f}"),
        ("r_th_k_per_w", "等效热阻/(K/W)", "#228833", "{:.3f}"),
        ("delta_p_pa", "压降/Pa", "#EE7733", "{:.6f}"),
    ]

    fig, axes = plt.subplots(2, 2, figsize=(10.5, 7.2))
    fig.subplots_adjust(wspace=0.32, hspace=0.42)

    for ax, (key, title, color, fmt) in zip(axes.ravel(), metrics):
        values = [float(row[key]) for row in rows]
        ax.bar(names, values, color=color, width=0.55)
        ax.set_title(title, fontsize=12)
        ax.tick_params(axis="x", labelrotation=0, labelsize=9)
        ax.grid(True, axis="y", alpha=0.25, linewidth=0.6)
        ax.set_ylim(min(values) * 0.997, max(values) * 1.003)
        add_bar_labels(ax, values, fmt)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    png_path = OUT_DIR / "fig5_4_3d_metrics.png"
    svg_path = OUT_DIR / "fig5_4_3d_metrics.svg"
    fig.savefig(png_path, dpi=220, bbox_inches="tight")
    fig.savefig(svg_path, format="svg", bbox_inches="tight")
    plt.close(fig)
    print(png_path)
    print(svg_path)


if __name__ == "__main__":
    main()
