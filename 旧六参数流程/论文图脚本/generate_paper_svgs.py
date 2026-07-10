#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Generate paper-ready SVG figures except CFD contour/cloud maps.

This script intentionally does not redraw COMSOL field contours. Those should
come from the actual CFD case folders. Everything else in the paper figure set
is generated here as true SVG.
"""

import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(errors="replace")

import matplotlib.pyplot as plt
from matplotlib import tri
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Polygon, Rectangle
import numpy as np
import pandas as pd
from PIL import Image


RESULTS_DIR = "ai_cnn_model_results"
OUTPUT_DIR = "paper_figures_svg"

COLORS = {
    "blue": "#2F6B9A",
    "orange": "#D9822B",
    "green": "#3A7D44",
    "red": "#B04A3A",
    "gray": "#5E6472",
    "light_gray": "#EEF1F4",
    "dark": "#1F2933",
}

PARAM_BOUNDS = {
    "Ta": (0.00, 0.05),
    "Twa": (0.20, 0.60),
    "Tb": (0.08, 0.15),
    "Ts": (0.50, 1.50),
    "Tt": (0.50, 1.20),
    "Tad": (0.00, 1.00),
}


def naca_airfoil(chord=1.0, ta=0.03, twa=0.4, tb=0.12, n=120):
    x = np.linspace(0, chord, n)
    xc = x / chord
    yt = (tb / 0.2) * chord * (
        0.2969 * np.sqrt(np.maximum(xc, 1e-9))
        - 0.1260 * xc
        - 0.3516 * xc**2
        + 0.2843 * xc**3
        - 0.1015 * xc**4
    )
    yc = np.zeros_like(x)
    dyc_dx = np.zeros_like(x)
    if ta > 0:
        for i, value in enumerate(xc):
            if value < twa:
                yc[i] = (ta * chord / twa**2) * (2 * twa * value - value**2)
                dyc_dx[i] = (ta / twa**2) * (2 * twa - 2 * value)
            else:
                yc[i] = (ta * chord / (1 - twa) ** 2) * ((1 - 2 * twa) + 2 * twa * value - value**2)
                dyc_dx[i] = (ta / (1 - twa) ** 2) * (2 * twa - 2 * value)
    theta = np.arctan(dyc_dx)
    xu = x - yt * np.sin(theta)
    yu = yc + yt * np.cos(theta)
    xl = x + yt * np.sin(theta)
    yl = yc - yt * np.cos(theta)
    coords = np.vstack([np.column_stack([xu, yu]), np.column_stack([xl[::-1], yl[::-1]])])
    return x, yc, xu, yu, xl, yl, coords


def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def save_svg(fig, filename):
    ensure_output_dir()
    path = os.path.join(OUTPUT_DIR, filename)
    fig.savefig(path, format="svg", bbox_inches="tight")
    plt.close(fig)
    print(f"[INFO] Saved {path}")


def setup_style():
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Arial Unicode MS", "DejaVu Sans"],
        "font.size": 10,
        "axes.titlesize": 11,
        "axes.labelsize": 10,
        "legend.fontsize": 9,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "svg.fonttype": "none",
        "axes.spines.top": False,
        "axes.spines.right": False,
    })


def plot_geometry_schematic():
    fig, axes = plt.subplots(
        1, 2, figsize=(10.8, 4.1), gridspec_kw={"width_ratios": [1.68, 1.0]}
    )
    label_box = dict(boxstyle="round,pad=0.18", facecolor="white", edgecolor="none", alpha=0.92)
    arrow_dim = dict(arrowstyle="<->", color=COLORS["dark"], lw=1.25, mutation_scale=15)

    ax = axes[0]
    _, _, _, _, _, _, foil = naca_airfoil(chord=0.8, ta=0.025, twa=0.42, tb=0.13)
    dx, dy, stagger = 1.05, 0.58, 0.32
    for row in range(3):
        for col in range(8):
            x_shift = col * dx + (stagger if row % 2 else 0)
            y_shift = (row - 1) * dy
            ax.add_patch(Polygon(foil + [x_shift, y_shift], closed=True, facecolor="#D9E7F5",
                                 edgecolor=COLORS["blue"], linewidth=0.8))

    ax.add_patch(Rectangle((-0.42, -1.12), 8.75, 2.24, fill=False, edgecolor=COLORS["dark"], linewidth=1.1))
    ax.annotate("", xy=(-0.06, 0), xytext=(-0.78, 0),
                arrowprops=dict(arrowstyle="-|>", color=COLORS["red"], lw=1.8))
    ax.text(-0.82, 0.23, r"$u_{in}, T_{in}$", color=COLORS["red"], fontsize=10,
            ha="left", va="bottom", bbox=label_box)
    ax.text(8.18, 0.22, r"$p_{out}$", color=COLORS["gray"], fontsize=10,
            ha="left", va="bottom", bbox=label_box)

    ts_y = 0.84
    ts_x0, ts_x1 = 0.08, dx + 0.08
    ax.annotate("", xy=(ts_x0, ts_y), xytext=(ts_x1, ts_y), arrowprops=arrow_dim)
    ax.plot([ts_x0, ts_x0], [0.68, 0.93], color=COLORS["dark"], lw=0.85)
    ax.plot([ts_x1, ts_x1], [0.68, 0.93], color=COLORS["dark"], lw=0.85)
    ax.text((ts_x0 + ts_x1) / 2, ts_y + 0.08, r"$S_s=(1+T_s)c$", ha="center", va="bottom",
            bbox=label_box)

    ax.annotate("", xy=(8.62, -dy), xytext=(8.62, 0),
                arrowprops=arrow_dim)
    ax.plot([8.50, 8.72], [-dy, -dy], color=COLORS["dark"], lw=0.8)
    ax.plot([8.50, 8.72], [0, 0], color=COLORS["dark"], lw=0.8)
    ax.text(8.78, -dy / 2, r"$S_t=T_t c$", va="center", ha="left", bbox=label_box)

    tad_x0, tad_x1, tad_y = 2 * dx + 0.05, 2 * dx + stagger + 0.05, 0.84
    ax.plot([tad_x0, tad_x1], [tad_y, tad_y], color=COLORS["dark"], lw=1.45)
    ax.plot([tad_x0, tad_x0], [0.68, 0.93], color=COLORS["dark"], lw=0.95)
    ax.plot([tad_x1, tad_x1], [0.44, 0.93], color=COLORS["dark"], lw=0.95)
    tick_h = 0.07
    ax.plot([tad_x0, tad_x0], [tad_y - tick_h, tad_y + tick_h], color=COLORS["dark"], lw=1.45)
    ax.plot([tad_x1, tad_x1], [tad_y - tick_h, tad_y + tick_h], color=COLORS["dark"], lw=1.45)
    ax.text((tad_x0 + tad_x1) / 2, tad_y + 0.08, r"$S_d=T_{ad}c$", ha="center",
            va="bottom", bbox=label_box)
    ax.set_title("（a）3×8 交错翼型管阵列")
    ax.set_aspect("equal")
    ax.set_xlim(-0.95, 9.05)
    ax.set_ylim(-1.62, 1.68)
    ax.axis("off")

    ax = axes[1]
    x, yc, xu, yu, xl, yl, coords = naca_airfoil(chord=1.0, ta=0.06, twa=0.4, tb=0.17)
    ax.add_patch(Polygon(coords, closed=True, facecolor="#EAF2FB", edgecolor=COLORS["blue"], linewidth=1.2))
    ax.plot(x, yc, "--", color=COLORS["red"], lw=1.2, label="弯度线")
    ax.plot([0, 1], [0, 0], "-.", color=COLORS["gray"], lw=1.0)
    idx = np.argmin(np.abs(x - 0.4))
    ax.scatter([x[idx]], [yc[idx]], s=24, color=COLORS["red"], zorder=5)
    ax.annotate("", xy=(0, -0.31), xytext=(1, -0.31),
                arrowprops=dict(arrowstyle="<->", color=COLORS["dark"], lw=1.1))
    ax.plot([0, 0], [-0.25, -0.36], color=COLORS["dark"], lw=0.8)
    ax.plot([1, 1], [-0.25, -0.36], color=COLORS["dark"], lw=0.8)
    ax.text(0.5, -0.36, "弦长 c", ha="center", va="top", bbox=label_box)

    ax.annotate("", xy=(-0.13, 0), xytext=(-0.13, yc[idx]),
                arrowprops=dict(arrowstyle="<->", color=COLORS["red"], lw=1.1))
    ax.plot([-0.17, -0.02], [0, 0], color=COLORS["red"], lw=0.75)
    ax.plot([-0.17, x[idx]], [yc[idx], yc[idx]], color=COLORS["red"], lw=0.75)
    ax.text(-0.18, yc[idx] / 2, r"$m=T_a c$", ha="right", va="center",
            color=COLORS["red"], bbox=label_box)

    ax.annotate("", xy=(0, 0.30), xytext=(x[idx], 0.30),
                arrowprops=dict(arrowstyle="<->", color=COLORS["dark"], lw=1.1))
    ax.plot([0, 0], [0.22, 0.35], color=COLORS["dark"], lw=0.8)
    ax.plot([x[idx], x[idx]], [yc[idx] + 0.02, 0.35], color=COLORS["dark"], lw=0.8)
    ax.text(x[idx] / 2, 0.35, r"$p=T_{wa}c$", ha="center", va="bottom", bbox=label_box)
    thick_idx = np.argmin(np.abs(x - 0.3))
    ax.annotate("", xy=(1.20, yl[thick_idx]), xytext=(1.20, yu[thick_idx]),
                arrowprops=dict(arrowstyle="<->", color=COLORS["dark"], lw=1.1))
    ax.plot([x[thick_idx], 1.25], [yl[thick_idx], yl[thick_idx]], color=COLORS["dark"], lw=0.8)
    ax.plot([x[thick_idx], 1.25], [yu[thick_idx], yu[thick_idx]], color=COLORS["dark"], lw=0.8)
    ax.text(1.27, (yu[thick_idx] + yl[thick_idx]) / 2, r"$t=T_b c$",
            va="center", ha="left", bbox=label_box)
    ax.set_title("（b）翼型几何参数")
    ax.set_aspect("equal")
    ax.set_xlim(-0.30, 1.48)
    ax.set_ylim(-0.43, 0.43)
    ax.axis("off")

    fig.tight_layout(w_pad=2.2)
    save_svg(fig, "Fig1_Geometry_Schematic.svg")


def plot_computational_domain():
    fig, ax = plt.subplots(figsize=(11.4, 3.35))
    ax.set_aspect("equal")
    ax.axis("off")
    label_box = dict(boxstyle="round,pad=0.22", facecolor="white", edgecolor="#CBD5E1", alpha=0.96)
    callout = dict(arrowstyle="-|>", lw=1.15, color=COLORS["gray"], mutation_scale=12)

    c = 1.0
    ta, tb, tt, ts, tad = 0.035, 0.12, 0.85, 1.10, 0.50
    domain_x = -5.0 * c
    domain_y = -(tt + ta + tb + 0.35) * c
    domain_w = (8 * (1 + ts) + tad + 15) * c
    domain_h = 2 * (tt + ta + tb + 0.35) * c
    domain_right = domain_x + domain_w

    domain = Rectangle((domain_x, domain_y), domain_w, domain_h,
                       facecolor="#F8FAFC", edgecolor=COLORS["dark"], linewidth=1.2)
    ax.add_patch(domain)
    _, _, _, _, _, _, foil = naca_airfoil(chord=0.92, ta=ta, twa=0.4, tb=tb)
    dx, dy, stagger = (1 + ts) * c, tt * c, tad * c
    for row in range(3):
        for col in range(8):
            x_shift = col * dx + (stagger if row % 2 else 0)
            y_shift = (row - 1) * dy
            ax.add_patch(Polygon(foil + [x_shift, y_shift], closed=True, facecolor="#D9E7F5",
                                 edgecolor=COLORS["blue"], linewidth=0.7))

    ax.annotate("", xy=(-0.25, 0), xytext=(domain_x + 0.45, 0),
                arrowprops=dict(arrowstyle="-|>", lw=2.0, color=COLORS["red"], mutation_scale=15))
    ax.annotate("", xy=(domain_right + 0.65, 0), xytext=(domain_right - 1.10, 0),
                arrowprops=dict(arrowstyle="-|>", lw=1.8, color=COLORS["gray"], mutation_scale=15))

    ax.annotate("速度入口\n$u_{in}, T_{in}$", xy=(domain_x + 0.35, 0.0),
                xytext=(domain_x + 0.38, domain_y + domain_h + 0.82),
                color=COLORS["red"], fontsize=9, ha="left", va="bottom",
                bbox=label_box, arrowprops=dict(arrowstyle="-|>", lw=1.15, color=COLORS["red"], mutation_scale=12))
    ax.annotate("压力出口\n$p_{out}$", xy=(domain_right - 0.35, 0.0),
                xytext=(domain_right - 0.35, domain_y + domain_h + 0.82),
                color=COLORS["gray"], fontsize=9, ha="right", va="bottom",
                bbox=label_box, arrowprops=callout)

    for boundary_y in [domain_y + domain_h, domain_y]:
        ax.plot([domain_x + 0.10, domain_right - 0.10], [boundary_y, boundary_y], color=COLORS["gray"],
                lw=1.0, linestyle=(0, (5, 4)))
    x_mid = (domain_x + domain_right) / 2
    ax.annotate("对称边界", xy=(x_mid, domain_y + domain_h), xytext=(x_mid, domain_y + domain_h + 0.42),
                ha="center", va="bottom", color=COLORS["gray"], fontsize=9,
                bbox=label_box, arrowprops=callout)
    ax.annotate("对称边界", xy=(x_mid, domain_y), xytext=(x_mid, domain_y - 0.42),
                ha="center", va="top", color=COLORS["gray"], fontsize=9,
                bbox=label_box, arrowprops=callout)

    ax.annotate("翼型固体区域：\n体积热源", xy=(4.45, 0.0), xytext=(3.25, domain_y - 0.78),
                ha="center", va="top", fontsize=8.6,
                bbox=dict(boxstyle="round,pad=0.25", facecolor="#FFF2D8", edgecolor="#E6B85C"),
                arrowprops=dict(arrowstyle="-|>", lw=1.15, color="#B7791F", mutation_scale=12))
    ax.set_xlim(domain_x - 0.62, domain_right + 0.72)
    ax.set_ylim(domain_y - 1.12, domain_y + domain_h + 1.20)
    save_svg(fig, "Fig2_Computational_Domain_BC.svg")


def plot_mesh_schematic():
    fig, ax = plt.subplots(figsize=(11.4, 3.45))
    ax.set_aspect("equal")
    ax.axis("off")
    label_box = dict(boxstyle="round,pad=0.20", facecolor="white", edgecolor="#CBD5E1", alpha=0.96)
    callout = dict(arrowstyle="-|>", lw=1.05, color=COLORS["gray"], mutation_scale=11)

    # Full computational domain with a dense triangular mesh.
    domain_x, domain_y = -5.0, -1.355
    domain_w, domain_h = 32.3, 2.71
    ax.add_patch(Rectangle((domain_x, domain_y), domain_w, domain_h, facecolor="#FBFDFF",
                           edgecolor=COLORS["dark"], linewidth=1.0))
    rng = np.random.default_rng(42)
    gx, gy = np.meshgrid(np.linspace(domain_x, domain_x + domain_w, 100),
                         np.linspace(domain_y, domain_y + domain_h, 15))
    points = np.column_stack([gx.ravel(), gy.ravel()])
    points += rng.normal(scale=0.028, size=points.shape)
    points[:, 0] = np.clip(points[:, 0], domain_x, domain_x + domain_w)
    points[:, 1] = np.clip(points[:, 1], domain_y, domain_y + domain_h)
    triang = tri.Triangulation(points[:, 0], points[:, 1])
    ax.triplot(triang, color="#BCC7D4", linewidth=0.24, zorder=1)

    _, _, _, _, _, _, foil = naca_airfoil(chord=0.92, ta=0.035, twa=0.4, tb=0.12)
    dx, dy, stagger = 2.10, 0.85, 0.50
    tube_centers = []
    for row in range(3):
        for col in range(8):
            x_shift = col * dx + (stagger if row % 2 else 0)
            y_shift = (row - 1) * dy
            tube_centers.append((x_shift + 0.24, y_shift))
            ax.add_patch(Polygon(foil + [x_shift, y_shift], closed=True, facecolor="#F8FAFC",
                                 edgecolor=COLORS["blue"], linewidth=0.75, zorder=5))

    ax.plot([domain_x, domain_x + domain_w], [domain_y + domain_h, domain_y + domain_h],
            color=COLORS["gray"], lw=0.9, linestyle=(0, (5, 4)))
    ax.plot([domain_x, domain_x + domain_w], [domain_y, domain_y],
            color=COLORS["gray"], lw=0.9, linestyle=(0, (5, 4)))
    ax.annotate("对称边界", xy=(domain_x + domain_w / 2, domain_y + domain_h),
                xytext=(domain_x + domain_w / 2, domain_y + domain_h + 0.30),
                color=COLORS["gray"], fontsize=8.8, ha="center", va="bottom",
                bbox=label_box, arrowprops=callout)
    ax.annotate("对称边界", xy=(domain_x + domain_w / 2, domain_y),
                xytext=(domain_x + domain_w / 2, domain_y - 0.30),
                color=COLORS["gray"], fontsize=8.8, ha="center", va="top",
                bbox=label_box, arrowprops=callout)
    ax.text(domain_x + 0.20, domain_y + domain_h + 0.42, "（a）计算域整体网格",
            fontsize=9.4, color=COLORS["dark"], ha="left", va="bottom", bbox=label_box)

    # Zoom box and near-wall refinement inset.
    zoom_x, zoom_y, zoom_w, zoom_h = 3.6, -0.55, 2.25, 1.25
    ax.add_patch(Rectangle((zoom_x, zoom_y), zoom_w, zoom_h, fill=False,
                           edgecolor=COLORS["red"], linewidth=1.0, linestyle="--", zorder=8))
    inset_x, inset_y = 28.4, -1.05
    inset_w, inset_h = 4.2, 2.35
    ax.add_patch(Rectangle((inset_x, inset_y), inset_w, inset_h, facecolor="#FBFDFF",
                           edgecolor=COLORS["red"], linewidth=1.1))
    ax.plot([zoom_x + zoom_w, inset_x], [zoom_y + zoom_h, inset_y + inset_h],
            color=COLORS["red"], lw=0.8, linestyle="--")
    ax.plot([zoom_x + zoom_w, inset_x], [zoom_y, inset_y],
            color=COLORS["red"], lw=0.8, linestyle="--")

    outer_x, outer_y = np.meshgrid(np.linspace(inset_x + 0.12, inset_x + inset_w - 0.12, 15),
                                  np.linspace(inset_y + 0.16, inset_y + inset_h - 0.16, 10))
    local_points = np.column_stack([outer_x.ravel(), outer_y.ravel()])
    for radius, n in [(0.18, 40), (0.29, 52), (0.42, 64), (0.58, 76)]:
        theta = np.linspace(0, 2 * np.pi, n, endpoint=False)
        local_points = np.vstack([
            local_points,
            np.column_stack([
                inset_x + 1.96 + 1.85 * radius * np.cos(theta),
                inset_y + 1.16 + 0.56 * radius * np.sin(theta),
            ]),
        ])
    local_points += rng.normal(scale=0.01, size=local_points.shape)
    local_triang = tri.Triangulation(local_points[:, 0], local_points[:, 1])
    ax.triplot(local_triang, color="#A9B4C2", linewidth=0.34, zorder=1)
    _, _, _, _, _, _, zoom_foil = naca_airfoil(chord=1.55, ta=0.035, twa=0.4, tb=0.12)
    ax.add_patch(Polygon(zoom_foil + [inset_x + 1.18, inset_y + 1.16], closed=True,
                         facecolor="#F8FAFC", edgecolor=COLORS["blue"], linewidth=1.2, zorder=6))
    ax.text(inset_x + 0.10, domain_y + domain_h + 0.44, "（b）翼型近壁面局部加密",
            fontsize=9.4, color=COLORS["dark"], ha="left", va="bottom", bbox=label_box)
    ax.annotate("边界层\n加密", xy=(inset_x + 2.75, inset_y + 1.18),
                xytext=(inset_x + inset_w + 0.28, inset_y + 0.40),
                fontsize=8.5, color=COLORS["red"], ha="left", va="center",
                bbox=label_box, arrowprops=dict(arrowstyle="-|>", lw=1.05, color=COLORS["red"], mutation_scale=11))

    ax.set_xlim(domain_x - 0.35, inset_x + inset_w + 1.10)
    ax.set_ylim(domain_y - 0.58, domain_y + domain_h + 0.82)
    save_svg(fig, "Fig3_Mesh_Schematic.svg")


def plot_architecture():
    fig, ax = plt.subplots(figsize=(10.0, 4.6))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    def box(x, y, w, h, title, subtitle, color):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.014,rounding_size=0.02",
                                    facecolor=color, edgecolor=COLORS["dark"], linewidth=1.0))
        ax.text(x + w / 2, y + h * 0.63, title, ha="center", va="center", fontweight="bold", fontsize=9.5)
        ax.text(x + w / 2, y + h * 0.33, subtitle, ha="center", va="center", fontsize=8.1)

    def arrow(a, b):
        ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=16, linewidth=1.35, color=COLORS["gray"]))

    def elbow(points, color=COLORS["gray"]):
        xs, ys = zip(*points)
        ax.plot(xs, ys, color=color, linewidth=1.25)
        arrow(points[-2], points[-1])

    box(0.05, 0.66, 0.16, 0.16, "Field images", "velocity / pressure / temperature", "#DCEBFA")
    box(0.29, 0.66, 0.17, 0.16, "Image features", "statistics + spatial signatures", "#FFF2D8")
    box(0.05, 0.30, 0.16, 0.16, "Geometry", "Ta, Twa, Tb, Ts, Tt, Tad", "#E5F3E6")
    box(0.29, 0.30, 0.17, 0.16, "Standardization", "train-set scaling", "#E8EAF6")
    box(0.56, 0.48, 0.17, 0.18, "Feature fusion", "concatenate modalities", "#F5E4E0")
    box(0.80, 0.48, 0.17, 0.18, "Regressor", "validation-selected FeatureMLP", "#DCEBFA")
    box(0.80, 0.18, 0.17, 0.14, "Outputs", "Nu and f", "#E5F3E6")
    box(0.80, 0.78, 0.17, 0.14, "Baseline", "geometry-only MLP", "#EEF1F4")

    arrow((0.21, 0.74), (0.29, 0.74))
    arrow((0.21, 0.38), (0.29, 0.38))
    elbow([(0.46, 0.74), (0.51, 0.74), (0.51, 0.58), (0.56, 0.58)])
    elbow([(0.46, 0.38), (0.51, 0.38), (0.51, 0.54), (0.56, 0.54)])
    arrow((0.73, 0.57), (0.80, 0.57))
    elbow([(0.885, 0.48), (0.885, 0.40), (0.885, 0.32)])
    elbow([(0.885, 0.78), (0.885, 0.72), (0.885, 0.66)])

    ax.text(0.5, 0.95, "Multimodal feature-fusion surrogate model", ha="center",
            va="center", fontsize=13, fontweight="bold", color=COLORS["dark"])
    save_svg(fig, "Fig5_Multimodal_Fusion_Architecture.svg")


def r2_score_np(y_true, y_pred):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    return 1.0 - ss_res / ss_tot


def mae_np(y_true, y_pred):
    return float(np.mean(np.abs(np.asarray(y_true) - np.asarray(y_pred))))


def plot_prediction_scatter():
    path = os.path.join(RESULTS_DIR, "multimodal_feature_predictions.csv")
    if not os.path.exists(path):
        path = os.path.join(RESULTS_DIR, "test_predictions.csv")
    df = pd.read_csv(path)

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.2))
    panels = [
        (axes[0], "true_Nu", "pred_Nu", "Nu", COLORS["blue"], 1.8),
        (axes[1], "true_f", "pred_f", "f", COLORS["orange"], 0.00045),
    ]

    for ax, true_col, pred_col, label, color, pad in panels:
        x = df[true_col].to_numpy()
        y = df[pred_col].to_numpy()
        r2 = r2_score_np(x, y)
        mae = mae_np(x, y)
        low = min(x.min(), y.min()) - pad
        high = max(x.max(), y.max()) + pad
        ax.scatter(x, y, s=32, color=color, edgecolor="white", linewidth=0.6, alpha=0.82)
        ax.plot([low, high], [low, high], "--", color=COLORS["red"], lw=1.4, label="Ideal")
        ax.set_xlim(low, high)
        ax.set_ylim(low, high)
        ax.set_xlabel(f"CFD true {label}")
        ax.set_ylabel(f"Predicted {label}")
        ax.text(0.04, 0.95, f"{label}\nR2={r2:.3f}, MAE={mae:.4g}", transform=ax.transAxes,
                ha="left", va="top", fontsize=8.8, linespacing=1.15,
                bbox=dict(boxstyle="round,pad=0.22", facecolor="white", edgecolor="none", alpha=0.88))
        ax.grid(False)
        ax.legend(frameon=False, loc="lower right")

    fig.tight_layout()
    save_svg(fig, "Fig6_Test_Prediction.svg")
    # Keep the old filename because the paper markdown already references it.
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.2))
    for ax, true_col, pred_col, label, color, pad in [
        (axes[0], "true_Nu", "pred_Nu", "Nu", COLORS["blue"], 1.8),
        (axes[1], "true_f", "pred_f", "f", COLORS["orange"], 0.00045),
    ]:
        x = df[true_col].to_numpy()
        y = df[pred_col].to_numpy()
        r2 = r2_score_np(x, y)
        mae = mae_np(x, y)
        low = min(x.min(), y.min()) - pad
        high = max(x.max(), y.max()) + pad
        ax.scatter(x, y, s=32, color=color, edgecolor="white", linewidth=0.6, alpha=0.82)
        ax.plot([low, high], [low, high], "--", color=COLORS["red"], lw=1.4, label="Ideal")
        ax.set_xlim(low, high)
        ax.set_ylim(low, high)
        ax.set_xlabel(f"CFD true {label}")
        ax.set_ylabel(f"Predicted {label}")
        ax.text(0.04, 0.95, f"{label}\nR2={r2:.3f}, MAE={mae:.4g}", transform=ax.transAxes,
                ha="left", va="top", fontsize=8.8, linespacing=1.15,
                bbox=dict(boxstyle="round,pad=0.22", facecolor="white", edgecolor="none", alpha=0.88))
        ax.grid(False)
        ax.legend(frameon=False, loc="lower right")
    fig.tight_layout()
    save_svg(fig, "Fig6_CNN_Test_Prediction.svg")


def plot_model_comparison():
    path = os.path.join(RESULTS_DIR, "paper_table8_model_comparison.csv")
    df = pd.read_csv(path)

    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.25))
    model_order = [model for model in ["MLP", "Multimodal-Fusion", "CBAM-CNN"] if model in set(df["model"])]
    target_order = ["Nu", "f"]
    color_map = {"CBAM-CNN": COLORS["blue"], "MLP": COLORS["green"], "Multimodal-Fusion": COLORS["orange"]}

    width = 0.7 / max(1, len(model_order))
    x = np.arange(len(target_order))

    for i, model in enumerate(model_order):
        sub = df[df["model"] == model].set_index("target").loc[target_order]
        offset = (i - (len(model_order) - 1) / 2) * width
        axes[0].bar(x + offset, sub["R2"], width, label=model, color=color_map.get(model, COLORS["gray"]))
        axes[1].bar(x + offset, sub["MAPE_percent"], width, label=model, color=color_map.get(model, COLORS["gray"]))

    axes[0].set_ylabel("R2")
    axes[0].set_ylim(0.88, 1.0)
    axes[0].set_xticks(x, target_order)
    axes[0].text(0.03, 0.94, "Coefficient of determination", transform=axes[0].transAxes,
                 ha="left", va="top", fontsize=9.2,
                 bbox=dict(boxstyle="round,pad=0.22", facecolor="white", edgecolor="none", alpha=0.88))
    axes[0].grid(False)

    axes[1].set_ylabel("MAPE (%)")
    axes[1].set_xticks(x, target_order)
    axes[1].text(0.03, 0.94, "Mean absolute percentage error", transform=axes[1].transAxes,
                 ha="left", va="top", fontsize=9.2,
                 bbox=dict(boxstyle="round,pad=0.22", facecolor="white", edgecolor="none", alpha=0.88))
    axes[1].grid(False)

    for ax in axes:
        ax.legend(frameon=False, loc="best")

    fig.tight_layout()
    save_svg(fig, "Fig8_Model_Comparison.svg")


def plot_mlp_loss():
    path = os.path.join(RESULTS_DIR, "mlp_baseline_history.csv")
    df = pd.read_csv(path)

    fig, ax = plt.subplots(figsize=(5.8, 3.2))
    ax.plot(df["epoch"], df["train_loss"], color=COLORS["blue"], lw=1.6, label="训练损失")
    ax.plot(df["epoch"], df["val_loss"], color=COLORS["orange"], lw=1.6, label="验证损失")
    ax.set_xlabel("迭代轮数")
    ax.set_ylabel("归一化 MSE 损失")
    ax.grid(False)
    ax.legend(frameon=False)
    fig.tight_layout()
    save_svg(fig, "Fig_MLP_Baseline_Loss.svg")


def extract_loss_history_from_png(path, epochs=50):
    """Approximate old loss history from the legacy PNG when CSV is missing."""
    img = np.asarray(Image.open(path).convert("RGB"))
    h, w = img.shape[:2]
    dark = (img[:, :, 0] < 80) & (img[:, :, 1] < 80) & (img[:, :, 2] < 80)
    row_candidates = np.where(dark.sum(axis=1) > 0.25 * w)[0]
    col_candidates = np.where(dark.sum(axis=0) > 0.25 * h)[0]
    if len(row_candidates) < 2 or len(col_candidates) < 2:
        raise RuntimeError("Could not detect plot axes in loss_curve.png")

    y_top = float(row_candidates.min())
    y_bottom = float(row_candidates.max())
    x_left = float(col_candidates.min())
    x_right = float(col_candidates.max())

    yy, xx = np.indices((h, w))
    exclude_legend = (xx > 0.66 * w) & (yy < 0.28 * h)
    in_plot = (xx > x_left) & (xx < x_right) & (yy > y_top) & (yy < y_bottom) & ~exclude_legend

    colors = {
        "train_loss": np.array([31, 119, 180], dtype=float),
        "val_loss": np.array([255, 127, 14], dtype=float),
    }
    histories = {}
    y_min, y_max = -0.03, 1.45
    for name, color in colors.items():
        dist = np.linalg.norm(img.astype(float) - color, axis=2)
        mask = (dist < 75) & in_plot
        ys, xs = np.where(mask)
        if len(xs) < epochs:
            raise RuntimeError(f"Could not detect enough {name} pixels in loss_curve.png")
        x_start = np.percentile(xs, 1)
        x_end = np.percentile(xs, 99)
        values = []
        for x in np.linspace(x_start, x_end, epochs):
            local = ys[np.abs(xs - x) <= 14]
            if len(local) == 0:
                values.append(values[-1] if values else np.nan)
                continue
            y = float(np.median(local))
            value = y_min + (y_bottom - y) / (y_bottom - y_top) * (y_max - y_min)
            values.append(max(0.0, float(value)))
        histories[name] = values

    return pd.DataFrame({
        "epoch": np.arange(1, epochs + 1),
        "train_loss": histories["train_loss"],
        "val_loss": histories["val_loss"],
        "source": "digitized_from_loss_curve_png",
    })


def plot_cbam_cnn_loss():
    history_path = os.path.join(RESULTS_DIR, "cnn_training_history.csv")
    legacy_png_path = os.path.join(RESULTS_DIR, "loss_curve.png")
    if os.path.exists(history_path):
        df = pd.read_csv(history_path)
    elif os.path.exists(legacy_png_path):
        df = extract_loss_history_from_png(legacy_png_path)
        digitized_path = os.path.join(RESULTS_DIR, "cnn_training_history_digitized.csv")
        df.to_csv(digitized_path, index=False, encoding="utf-8-sig")
        print(f"[WARN] cnn_training_history.csv not found; digitized old PNG into {digitized_path}")
    else:
        print("[WARN] Skipped Fig_CBAM_CNN_Loss.svg: no cnn_training_history.csv or loss_curve.png")
        return

    fig, ax = plt.subplots(figsize=(5.8, 3.2))
    ax.plot(df["epoch"], df["train_loss"], color=COLORS["blue"], lw=1.6, label="训练损失")
    ax.plot(df["epoch"], df["val_loss"], color=COLORS["orange"], lw=1.6, label="验证损失")
    ax.set_xlabel("迭代轮数")
    ax.set_ylabel("归一化 MSE 损失")
    ax.grid(False)
    ax.legend(frameon=False)
    fig.tight_layout()
    save_svg(fig, "Fig_CBAM_CNN_Loss.svg")


def add_box(ax, xy, width, height, title, subtitle, color):
    box = FancyBboxPatch(
        xy,
        width,
        height,
        boxstyle="round,pad=0.015,rounding_size=0.025",
        facecolor=color,
        edgecolor=COLORS["dark"],
        linewidth=1.0,
    )
    ax.add_patch(box)
    x, y = xy
    ax.text(x + width / 2, y + height * 0.62, title, ha="center", va="center",
            fontsize=10, fontweight="bold", color=COLORS["dark"])
    ax.text(x + width / 2, y + height * 0.32, subtitle, ha="center", va="center",
            fontsize=8.5, color=COLORS["dark"])


def add_arrow(ax, start, end):
    arrow = FancyArrowPatch(
        start,
        end,
        arrowstyle="-|>",
        mutation_scale=12,
        linewidth=1.2,
        color=COLORS["gray"],
    )
    ax.add_patch(arrow)


def plot_workflow():
    fig, ax = plt.subplots(figsize=(9.2, 3.6))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    boxes = [
        ((0.03, 0.58), "LHS sampling", "6 design variables", "#DCEBFA"),
        ((0.23, 0.58), "COMSOL CFD", "batch simulation", "#E5F3E6"),
        ((0.43, 0.58), "Raw outputs", "result.json + fields", "#FFF2D8"),
        ((0.63, 0.58), "Labels rebuild", "unified labels.csv", "#F5E4E0"),
        ((0.83, 0.58), "Dataset split", "train / val / test", "#E8EAF6"),
        ((0.23, 0.18), "Multimodal CNN", "fields + geometry", "#DCEBFA"),
        ((0.43, 0.18), "MLP baseline", "geometry only", "#E5F3E6"),
        ((0.63, 0.18), "Model metrics", "R2, RMSE, MAE", "#FFF2D8"),
        ((0.83, 0.18), "CFD verification", "optimal design check", "#F5E4E0"),
    ]
    w, h = 0.14, 0.2
    for xy, title, subtitle, color in boxes:
        add_box(ax, xy, w, h, title, subtitle, color)

    top_y = 0.68
    bottom_y = 0.28
    for x0, x1 in [(0.17, 0.23), (0.37, 0.43), (0.57, 0.63), (0.77, 0.83)]:
        add_arrow(ax, (x0, top_y), (x1, top_y))
    add_arrow(ax, (0.90, 0.58), (0.90, 0.38))
    add_arrow(ax, (0.83, bottom_y), (0.77, bottom_y))
    add_arrow(ax, (0.63, bottom_y), (0.57, bottom_y))
    add_arrow(ax, (0.43, bottom_y), (0.37, bottom_y))

    save_svg(fig, "Fig2_Workflow.svg")


def main():
    setup_style()
    plot_geometry_schematic()
    plot_computational_domain()
    plot_mesh_schematic()
    plot_architecture()
    plot_prediction_scatter()
    plot_model_comparison()
    plot_cbam_cnn_loss()
    plot_mlp_loss()
    plot_workflow()


if __name__ == "__main__":
    main()

