#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageChops, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
RUN_DIR = ROOT / "new_model_runs"
OUT_DIR = ROOT / "paper_figures_svg"

METRICS = {
    "baseline": {
        "Nu": 36.573974,
        "f": 0.090191,
        "T_in": 298.147281,
        "T_out": 298.634552,
        "p_in": 11.122086,
        "p_out": 9.769220,
        "T_wing": 318.630819,
        "vol": 0.000194783,
    },
    "optimal": {
        "Nu": 38.778659,
        "f": 0.095762,
        "T_in": 298.026351,
        "T_out": 298.507896,
        "p_in": 11.696809,
        "p_out": 10.260376,
        "T_wing": 317.393531,
        "vol": 0.000195269,
    },
}


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


def enrich_metrics() -> None:
    for row in METRICS.values():
        row["Delta_p"] = abs(row["p_in"] - row["p_out"])
        row["Delta_T_wing"] = row["T_wing"] - row["T_in"]
        row["Delta_T_out"] = row["T_out"] - row["T_in"]
        row["Q_prime"] = 1e7 * row["vol"]
        row["eta"] = row["Nu"] / (row["f"] ** (1 / 3))


def percent_change(key: str) -> float:
    base = METRICS["baseline"][key]
    opt = METRICS["optimal"][key]
    return (opt - base) / base * 100.0


def trim_white(img: Image.Image, threshold: int = 248, pad: int = 8) -> Image.Image:
    img = img.convert("RGB")
    bg = Image.new("RGB", img.size, (255, 255, 255))
    diff = ImageChops.difference(img, bg)
    gray = diff.convert("L")
    mask = gray.point(lambda p: 255 if p > (255 - threshold) else 0)
    box = mask.getbbox()
    if box is None:
        return img
    left, top, right, bottom = box
    return img.crop((max(0, left - pad), max(0, top - pad), min(img.width, right + pad), min(img.height, bottom + pad)))


def fit_to_canvas(img: Image.Image, size: tuple[int, int] = (780, 330)) -> Image.Image:
    img = trim_white(img).convert("RGB")
    scale = min(size[0] / img.width, size[1] / img.height)
    new_size = (max(1, int(img.width * scale)), max(1, int(img.height * scale)))
    resized = img.resize(new_size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, (255, 255, 255))
    canvas.paste(resized, ((size[0] - new_size[0]) // 2, (size[1] - new_size[1]) // 2))
    return canvas


def add_contours(ax: plt.Axes, img: Image.Image) -> None:
    gray = img.convert("L").filter(ImageFilter.GaussianBlur(radius=2.0))
    field = np.asarray(gray, dtype=float)
    low, high = np.percentile(field, [16, 86])
    if high <= low:
        return
    levels = np.linspace(low, high, 6)
    x = np.arange(field.shape[1])
    y = np.arange(field.shape[0])
    ax.contour(x, y, field, levels=levels, colors="#111827", linewidths=0.45, alpha=0.35)
    ax.contour(x, y, field, levels=levels, colors="#ffffff", linewidths=0.22, alpha=0.55)


def run_image(case: str, filename: str) -> Image.Image:
    return Image.open(RUN_DIR / case / filename)


def make_fig4() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 3, figsize=(12.9, 3.05), dpi=180)
    specs = [
        ("velocity_magnitude.png", "速度场"),
        ("temperature.png", "温度场"),
        ("pressure.png", "压力场"),
    ]
    for ax, (filename, label) in zip(axes, specs):
        img = fit_to_canvas(run_image("optimal", filename), (780, 330))
        ax.imshow(img)
        add_contours(ax, img)
        ax.set_title(label, fontsize=10.5, pad=4)
        ax.axis("off")
    fig.subplots_adjust(left=0.015, right=0.99, top=0.86, bottom=0.06, wspace=0.04)
    fig.savefig(OUT_DIR / "Fig4_New_Model_Cloudmaps.png", dpi=300)
    fig.savefig(OUT_DIR / "Fig4_New_Model_Cloudmaps.svg")
    plt.close(fig)


def make_fig9() -> None:
    fig = plt.figure(figsize=(12.4, 5.45), dpi=180)
    gs = fig.add_gridspec(2, 2, hspace=0.16, wspace=0.08)
    fields = [
        ("baseline", "velocity_magnitude.png", "基准结构速度场"),
        ("baseline", "temperature.png", "基准结构温度场"),
        ("optimal", "velocity_magnitude.png", "最优结构速度场"),
        ("optimal", "temperature.png", "最优结构温度场"),
    ]
    for idx, (case, filename, title) in enumerate(fields):
        ax = fig.add_subplot(gs[idx // 2, idx % 2])
        img = fit_to_canvas(run_image(case, filename), (760, 320))
        ax.imshow(img)
        add_contours(ax, img)
        ax.set_title(title, fontsize=10.2, pad=4)
        ax.axis("off")

    fig.subplots_adjust(left=0.018, right=0.985, top=0.92, bottom=0.08)
    fig.savefig(OUT_DIR / "Fig9_Heat_Dissipation_Evidence.png", dpi=300)
    fig.savefig(OUT_DIR / "Fig9_Heat_Dissipation_Evidence.svg")
    plt.close(fig)


def make_fig8() -> None:
    fig, ax = plt.subplots(figsize=(7.2, 3.6), dpi=180)
    labels = ["Nu", "Q'", "η", "Tavg", "f", "Δp"]
    keys = ["Nu", "Q_prime", "eta", "T_wing", "f", "Delta_p"]
    values = [percent_change(k) for k in keys]
    colors = ["#1f5fd0", "#2f7d32", "#009688", "#f07a22", "#c2410c", "#b91c1c"]
    x = np.arange(len(labels))
    bars = ax.bar(x, values, color=colors, width=0.58)
    ax.axhline(0, color="#475569", lw=0.9)
    ax.set_xticks(x, labels)
    ax.tick_params(axis="x", labelsize=10)
    ax.set_ylabel("变化比例 / %")
    ax.set_ylim(min(values) * 3.2, max(values) * 1.35)
    for bar, val in zip(bars, values):
        va = "bottom" if val >= 0 else "top"
        y = val + (0.18 if val >= 0 else -0.08)
        ax.text(bar.get_x() + bar.get_width() / 2, y, f"{val:+.2f}%", ha="center", va=va, fontsize=9.2)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    ax.grid(False)
    ax.xaxis.grid(False)
    ax.yaxis.grid(False)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "Fig8_Model_Comparison.png", dpi=300)
    fig.savefig(OUT_DIR / "Fig8_Model_Comparison.svg")
    fig.savefig(OUT_DIR / "Fig8_Heat_Metric_Bars.png", dpi=300)
    fig.savefig(OUT_DIR / "Fig8_Heat_Metric_Bars.svg")
    plt.close(fig)


def save_summary() -> None:
    out = OUT_DIR / "new_model_summary.csv"
    fields = ["metric", "baseline", "optimal", "change_percent"]
    rows = []
    for key in ["Nu", "Q_prime", "T_wing", "Delta_T_wing", "eta", "f", "Delta_p", "Delta_T_out"]:
        rows.append({
            "metric": key,
            "baseline": METRICS["baseline"][key],
            "optimal": METRICS["optimal"][key],
            "change_percent": percent_change(key),
        })
    with out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved: {out}")


def main() -> None:
    setup_matplotlib()
    enrich_metrics()
    make_fig4()
    make_fig8()
    make_fig9()
    save_summary()
    print(f"Saved: {OUT_DIR / 'Fig4_New_Model_Cloudmaps.svg'}")
    print(f"Saved: {OUT_DIR / 'Fig9_Heat_Dissipation_Evidence.svg'}")


if __name__ == "__main__":
    main()
