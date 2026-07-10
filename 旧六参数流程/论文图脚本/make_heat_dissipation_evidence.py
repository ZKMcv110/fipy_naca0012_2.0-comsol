#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Generate heat-dissipation evidence figures for the paper.

This script intentionally uses existing CFD outputs under consol_cfddata. It
does not invent outlet profile data. For now it generates:
1) cloud-map comparison: baseline vs optimal velocity and temperature fields;
2) quantitative metric bars and table: Nu, Q_total, eta, outlet temperature rise,
   friction factor and pressure drop.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image, ImageChops, ImageFilter


DATA_DIR = Path("consol_cfddata")
OUT_DIR = Path("paper_figures_svg")

ZH = {
    "velocity": "\u901f\u5ea6\u573a\u4e91\u56fe",
    "temperature": "\u6e29\u5ea6\u573a\u4e91\u56fe",
    "baseline": "\u57fa\u51c6\u7ed3\u6784",
    "optimal": "\u6700\u4f18\u7ed3\u6784",
    "heat_metrics": "\u6563\u70ed\u6307\u6807\u5bf9\u6bd4",
    "penalty": "\u6d41\u52a8\u963b\u529b\u4ee3\u4ef7",
    "evidence_title": "\u57fa\u51c6\u7ed3\u6784\u4e0e\u6700\u4f18\u7ed3\u6784\u7684\u6563\u70ed\u8bc1\u636e\u94fe",
    "metrics_title": "\u6700\u4f18\u7ed3\u6784\u76f8\u5bf9\u57fa\u51c6\u7ed3\u6784\u7684\u6027\u80fd\u53d8\u5316",
    "case": "\u5de5\u51b5",
    "nu": "\u52aa\u585e\u5c14\u6570 Nu",
    "f": "\u6469\u64e6\u56e0\u5b50 f",
    "eta": "\u7efc\u5408\u6027\u80fd \u03b7",
    "qtotal": "\u603b\u6362\u70ed\u91cf Q_total",
    "dtout": "\u51fa\u53e3\u5e73\u5747\u6e29\u5347 \u0394T_out",
    "dp": "\u538b\u964d \u0394p",
    "percent_change": "\u76f8\u5bf9\u53d8\u5316 / %",
    "cloud_caption": "\u4e91\u56fe\u7528\u4e8e\u5c55\u793a\u6d41\u573a\u548c\u70ed\u5c3e\u8ff9\u5f62\u6001",
    "metric_caption": "\u5b9a\u91cf\u6307\u6807\u7528\u4e8e\u8bc1\u660e\u6563\u70ed\u6539\u5584\u5e76\u8bf4\u660e\u963b\u529b\u4ee3\u4ef7",
    "contour": "\u7b49\u503c\u7ebf",
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
    left = max(0, left - pad)
    top = max(0, top - pad)
    right = min(img.width, right + pad)
    bottom = min(img.height, bottom + pad)
    return img.crop((left, top, right, bottom))


def read_cases(baseline_case: int, optimal_case: int | None) -> tuple[pd.Series, pd.Series]:
    labels = pd.read_csv(DATA_DIR / "labels.csv")
    valid = labels[labels["image_complete"].astype(str).str.lower().isin(["true", "1"])]
    base = valid[valid["case_id"].eq(baseline_case)]
    if base.empty:
        raise ValueError(f"baseline case {baseline_case} not found in labels.csv")
    if optimal_case is None:
        opt = valid.loc[valid["target_param"].idxmax()]
    else:
        matches = valid[valid["case_id"].eq(optimal_case)]
        if matches.empty:
            raise ValueError(f"optimal case {optimal_case} not found in labels.csv")
        opt = matches.iloc[0]
    return base.iloc[0], opt


def case_image(case_id: int, filename: str) -> Image.Image:
    path = DATA_DIR / f"case_{case_id}_cfd_solution" / filename
    if not path.exists():
        raise FileNotFoundError(path)
    return trim_white(Image.open(path))


def fit_to_canvas(img: Image.Image, size: tuple[int, int] = (920, 380)) -> Image.Image:
    """Resize each field image into the same white canvas for equal panel sizes."""
    img = img.convert("RGB")
    canvas_w, canvas_h = size
    scale = min(canvas_w / img.width, canvas_h / img.height)
    new_size = (max(1, int(img.width * scale)), max(1, int(img.height * scale)))
    resized = img.resize(new_size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, (255, 255, 255))
    left = (canvas_w - new_size[0]) // 2
    top = (canvas_h - new_size[1]) // 2
    canvas.paste(resized, (left, top))
    return canvas


def add_image_contours(ax: plt.Axes, img: Image.Image) -> None:
    """Overlay visual iso-contours estimated from the cloud-map image itself."""
    gray = img.convert("L").filter(ImageFilter.GaussianBlur(radius=2.0))
    field = np.asarray(gray, dtype=float)
    low, high = np.percentile(field, [18, 86])
    if high <= low:
        return
    levels = np.linspace(low, high, 6)
    x = np.arange(field.shape[1])
    y = np.arange(field.shape[0])
    ax.contour(x, y, field, levels=levels, colors="#111827", linewidths=0.45, alpha=0.32)
    ax.contour(x, y, field, levels=levels, colors="#ffffff", linewidths=0.22, alpha=0.55)


def metric_values(row: pd.Series) -> dict[str, float]:
    dtout = float(row["T_out"] - row["T_in"])
    return {
        "Nu": float(row["Nu"]),
        "f": float(row["f"]),
        "eta": float(row["target_param"]),
        "Q_total": float(row["Q_total"]),
        "Delta_T_out": dtout,
        "Delta_p": float(row["delta_p"]),
    }


def percent_change(base: dict[str, float], opt: dict[str, float]) -> dict[str, float]:
    return {key: (opt[key] - base[key]) / base[key] * 100.0 for key in base}


def save_summary_csv(base: pd.Series, opt: pd.Series) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    base_m = metric_values(base)
    opt_m = metric_values(opt)
    change = percent_change(base_m, opt_m)
    out = OUT_DIR / "heat_dissipation_summary.csv"
    rows = []
    for key in ["Nu", "f", "eta", "Q_total", "Delta_T_out", "Delta_p"]:
        rows.append({
            "metric": key,
            "baseline_case": int(base["case_id"]),
            "baseline_value": base_m[key],
            "optimal_case": int(opt["case_id"]),
            "optimal_value": opt_m[key],
            "percent_change": change[key],
        })
    with out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    return out


def make_evidence_figure(base: pd.Series, opt: pd.Series) -> None:
    base_id = int(base["case_id"])
    opt_id = int(opt["case_id"])

    fig, axes = plt.subplots(2, 2, figsize=(12.8, 4.9), dpi=180)
    img_specs = [
        (0, 0, base_id, "velocity_magnitude.png", f"{ZH['baseline']}  {ZH['velocity']}"),
        (0, 1, base_id, "temperature.png", f"{ZH['baseline']}  {ZH['temperature']}"),
        (1, 0, opt_id, "velocity_magnitude.png", f"{ZH['optimal']}  {ZH['velocity']}"),
        (1, 1, opt_id, "temperature.png", f"{ZH['optimal']}  {ZH['temperature']}"),
    ]
    for r, c, case_id, file_name, title in img_specs:
        ax = axes[r, c]
        img = fit_to_canvas(case_image(case_id, file_name))
        ax.imshow(img)
        add_image_contours(ax, img)
        ax.set_title(title, fontsize=10.2, pad=4)
        ax.axis("off")
    fig.subplots_adjust(left=0.02, right=0.99, top=0.92, bottom=0.04, wspace=0.04, hspace=0.16)
    fig.savefig(OUT_DIR / "Fig9_Heat_Dissipation_Evidence.png", dpi=300)
    fig.savefig(OUT_DIR / "Fig9_Heat_Dissipation_Evidence.svg")
    plt.close(fig)


def make_metrics_figure(base: pd.Series, opt: pd.Series) -> None:
    base_id = int(base["case_id"])
    opt_id = int(opt["case_id"])
    base_m = metric_values(base)
    opt_m = metric_values(opt)
    change = percent_change(base_m, opt_m)

    fig = plt.figure(figsize=(10.8, 6.4), dpi=180)
    gs = fig.add_gridspec(2, 2, height_ratios=[1.0, 0.92], width_ratios=[1.15, 0.85], hspace=0.34, wspace=0.26)

    heat_keys = ["Nu", "Q_total", "eta", "Delta_T_out"]
    heat_labels = ["Nu", "Q_total", "\u03b7", "\u0394T_out"]
    heat_vals = [change[k] for k in heat_keys]
    ax_heat = fig.add_subplot(gs[0, 0])
    bars = ax_heat.bar(heat_labels, heat_vals, color=["#1f5fd0", "#2f7d32", "#009688", "#f07a22"], width=0.58)
    ax_heat.axhline(0, color="#333333", lw=0.9)
    ax_heat.set_ylabel(ZH["percent_change"])
    ax_heat.set_title(ZH["heat_metrics"], fontsize=11.5, color="#083b91", weight="bold")
    ax_heat.grid(False)
    ax_heat.set_ylim(0, max(heat_vals) * 1.28)
    for bar, val in zip(bars, heat_vals):
        ax_heat.text(bar.get_x() + bar.get_width() / 2, val + 0.15, f"{val:+.2f}%", ha="center", va="bottom", fontsize=9.5)
    for spine in ["top", "right"]:
        ax_heat.spines[spine].set_visible(False)

    penalty_keys = ["f", "Delta_p"]
    penalty_labels = ["f", "\u0394p"]
    penalty_vals = [change[k] for k in penalty_keys]
    ax_penalty = fig.add_subplot(gs[0, 1])
    bars = ax_penalty.bar(penalty_labels, penalty_vals, color=["#d9480f", "#c62828"], width=0.48)
    ax_penalty.axhline(0, color="#333333", lw=0.9)
    ax_penalty.set_ylabel(ZH["percent_change"])
    ax_penalty.set_title(ZH["penalty"], fontsize=11.5, color="#c62828", weight="bold")
    ax_penalty.grid(False)
    ax_penalty.set_ylim(0, max(penalty_vals) * 1.35)
    for bar, val in zip(bars, penalty_vals):
        ax_penalty.text(bar.get_x() + bar.get_width() / 2, val + 0.15, f"{val:+.2f}%", ha="center", va="bottom", fontsize=9.5)
    for spine in ["top", "right"]:
        ax_penalty.spines[spine].set_visible(False)

    ax_table = fig.add_subplot(gs[1, :])
    ax_table.axis("off")
    rows = [
        [ZH["nu"], f"{base_m['Nu']:.3f}", f"{opt_m['Nu']:.3f}", f"{change['Nu']:+.2f}%"],
        [ZH["qtotal"], f"{base_m['Q_total']:.1f}", f"{opt_m['Q_total']:.1f}", f"{change['Q_total']:+.2f}%"],
        [ZH["dtout"], f"{base_m['Delta_T_out']:.3f} K", f"{opt_m['Delta_T_out']:.3f} K", f"{change['Delta_T_out']:+.2f}%"],
        [ZH["eta"], f"{base_m['eta']:.3f}", f"{opt_m['eta']:.3f}", f"{change['eta']:+.2f}%"],
        [ZH["f"], f"{base_m['f']:.5f}", f"{opt_m['f']:.5f}", f"{change['f']:+.2f}%"],
        [ZH["dp"], f"{base_m['Delta_p']:.3f} Pa", f"{opt_m['Delta_p']:.3f} Pa", f"{change['Delta_p']:+.2f}%"],
    ]
    table = ax_table.table(
        cellText=rows,
        colLabels=["\u6307\u6807", f"{ZH['baseline']} (Case {base_id})", f"{ZH['optimal']} (Case {opt_id})", "\u53d8\u5316"],
        loc="center",
        cellLoc="center",
        colLoc="center",
        colWidths=[0.34, 0.22, 0.22, 0.16],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9.5)
    table.scale(1.0, 1.38)
    for (r, c), cell in table.get_celld().items():
        cell.set_edgecolor("#cbd5e1")
        if r == 0:
            cell.set_facecolor("#eef5ff")
            cell.set_text_props(weight="bold", color="#083b91")
        elif c == 3 and "+" in cell.get_text().get_text():
            cell.set_text_props(color="#2f7d32", weight="bold")

    fig.tight_layout()
    fig.savefig(OUT_DIR / "Fig9_Heat_Dissipation_Metrics.png", dpi=300)
    fig.savefig(OUT_DIR / "Fig9_Heat_Dissipation_Metrics.svg")
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate heat-dissipation evidence figures.")
    parser.add_argument("--baseline-case", type=int, default=1)
    parser.add_argument("--optimal-case", type=int, default=None)
    return parser.parse_args()


def main() -> None:
    setup_matplotlib()
    args = parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    base, opt = read_cases(args.baseline_case, args.optimal_case)
    csv_path = save_summary_csv(base, opt)
    make_evidence_figure(base, opt)
    make_metrics_figure(base, opt)
    print(f"Baseline case: {int(base['case_id'])}")
    print(f"Optimal case : {int(opt['case_id'])}")
    print(f"Saved: {csv_path}")
    print(f"Saved: {OUT_DIR / 'Fig9_Heat_Dissipation_Evidence.png'}")
    print(f"Saved: {OUT_DIR / 'Fig9_Heat_Dissipation_Evidence.svg'}")
    print(f"Saved: {OUT_DIR / 'Fig9_Heat_Dissipation_Metrics.png'}")
    print(f"Saved: {OUT_DIR / 'Fig9_Heat_Dissipation_Metrics.svg'}")


if __name__ == "__main__":
    main()
