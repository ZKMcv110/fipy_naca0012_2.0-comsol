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
        "font.family": "DejaVu Sans",
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
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.7))

    ax = axes[0]
    _, _, _, _, _, _, foil = naca_airfoil(chord=0.8, ta=0.025, twa=0.42, tb=0.13)
    dx, dy, stagger = 1.05, 0.58, 0.32
    for row in range(3):
        for col in range(8):
            x_shift = col * dx + (stagger if row % 2 else 0)
            y_shift = (row - 1) * dy
            ax.add_patch(Polygon(foil + [x_shift, y_shift], closed=True, facecolor="#D9E7F5",
                                 edgecolor=COLORS["blue"], linewidth=0.8))

    ax.add_patch(Rectangle((-0.45, -1.25), 8.65, 2.5, fill=False, edgecolor=COLORS["dark"], linewidth=1.1))
    ax.annotate("", xy=(-0.1, 0), xytext=(-0.8, 0),
                arrowprops=dict(arrowstyle="-|>", color=COLORS["red"], lw=1.8))
    ax.text(-0.86, 0.18, r"$u_{in}, T_{in}$", color=COLORS["red"], fontsize=10)
    ax.text(8.35, 0.18, r"$p_{out}$", color=COLORS["gray"], fontsize=10)

    ax.annotate("", xy=(0, -1.05), xytext=(dx, -1.05),
                arrowprops=dict(arrowstyle="<->", color=COLORS["dark"], lw=1.1))
    ax.text(dx / 2, -1.17, r"$T_s c$", ha="center", va="top")
    ax.annotate("", xy=(7.2, -dy), xytext=(7.2, 0),
                arrowprops=dict(arrowstyle="<->", color=COLORS["dark"], lw=1.1))
    ax.text(7.32, -dy / 2, r"$T_t c$", va="center")
    ax.annotate("", xy=(2 * dx, 0.96), xytext=(2 * dx + stagger, 0.96),
                arrowprops=dict(arrowstyle="<->", color=COLORS["dark"], lw=1.1))
    ax.text(2 * dx + stagger / 2, 1.05, r"$T_{ad}c$", ha="center")
    ax.set_title("(a) 3 x 8 staggered airfoil-tube array")
    ax.set_aspect("equal")
    ax.set_xlim(-0.95, 8.55)
    ax.set_ylim(-1.38, 1.36)
    ax.axis("off")

    ax = axes[1]
    x, yc, xu, yu, xl, yl, coords = naca_airfoil(chord=1.0, ta=0.06, twa=0.4, tb=0.17)
    ax.add_patch(Polygon(coords, closed=True, facecolor="#EAF2FB", edgecolor=COLORS["blue"], linewidth=1.2))
    ax.plot(x, yc, "--", color=COLORS["red"], lw=1.2, label="Camber line")
    ax.plot([0, 1], [0, 0], "-.", color=COLORS["gray"], lw=1.0)
    idx = np.argmin(np.abs(x - 0.4))
    ax.scatter([x[idx]], [yc[idx]], s=24, color=COLORS["red"], zorder=5)
    ax.annotate("", xy=(0, -0.25), xytext=(1, -0.25),
                arrowprops=dict(arrowstyle="<->", color=COLORS["dark"], lw=1.1))
    ax.text(0.5, -0.29, "chord c", ha="center", va="top")
    ax.annotate("", xy=(-0.08, 0), xytext=(-0.08, yc[idx]),
                arrowprops=dict(arrowstyle="<->", color=COLORS["red"], lw=1.1))
    ax.text(-0.11, yc[idx] / 2, r"$T_a c$", ha="right", va="center", color=COLORS["red"])
    ax.annotate("", xy=(0, 0.25), xytext=(x[idx], 0.25),
                arrowprops=dict(arrowstyle="<->", color=COLORS["dark"], lw=1.1))
    ax.text(x[idx] / 2, 0.28, r"$T_{wa}c$", ha="center")
    thick_idx = np.argmin(np.abs(x - 0.3))
    ax.annotate("", xy=(1.12, yl[thick_idx]), xytext=(1.12, yu[thick_idx]),
                arrowprops=dict(arrowstyle="<->", color=COLORS["dark"], lw=1.1))
    ax.text(1.15, (yu[thick_idx] + yl[thick_idx]) / 2, r"$T_b c$", va="center")
    ax.set_title("(b) Airfoil geometry parameters")
    ax.set_aspect("equal")
    ax.set_xlim(-0.22, 1.34)
    ax.set_ylim(-0.36, 0.36)
    ax.axis("off")

    fig.tight_layout()
    save_svg(fig, "Fig1_Geometry_Schematic.svg")


def plot_computational_domain():
    fig, ax = plt.subplots(figsize=(8.2, 3.2))
    ax.set_aspect("equal")
    ax.axis("off")

    domain = Rectangle((0, 0), 8.8, 2.8, facecolor="#F8FAFC", edgecolor=COLORS["dark"], linewidth=1.2)
    ax.add_patch(domain)
    _, _, _, _, _, _, foil = naca_airfoil(chord=0.65, ta=0.018, twa=0.4, tb=0.12)
    dx, dy, stagger = 0.9, 0.55, 0.28
    for row in range(3):
        for col in range(8):
            x_shift = 1.15 + col * dx + (stagger if row % 2 else 0)
            y_shift = 1.4 + (row - 1) * dy
            ax.add_patch(Polygon(foil + [x_shift, y_shift], closed=True, facecolor="#D9E7F5",
                                 edgecolor=COLORS["blue"], linewidth=0.7))

    ax.annotate("", xy=(0.75, 1.4), xytext=(-0.55, 1.4),
                arrowprops=dict(arrowstyle="-|>", lw=1.8, color=COLORS["red"]))
    ax.text(-0.55, 1.65, "velocity inlet\n$u_{in}, T_{in}$", color=COLORS["red"], fontsize=9, ha="left")
    ax.annotate("", xy=(9.25, 1.4), xytext=(8.45, 1.4),
                arrowprops=dict(arrowstyle="-|>", lw=1.5, color=COLORS["gray"]))
    ax.text(8.95, 1.65, "pressure outlet\n$p_{out}$", color=COLORS["gray"], fontsize=9, ha="center")
    ax.text(4.4, 2.98, "adiabatic / symmetry wall", ha="center", color=COLORS["gray"])
    ax.text(4.4, -0.28, "adiabatic / symmetry wall", ha="center", color=COLORS["gray"])
    ax.text(4.8, 0.42, "airfoil solid regions:\nvolumetric heat source", ha="center", fontsize=9,
            bbox=dict(boxstyle="round,pad=0.25", facecolor="#FFF2D8", edgecolor="#E6B85C"))
    ax.set_xlim(-0.75, 9.35)
    ax.set_ylim(-0.45, 3.18)
    ax.set_title("Computational domain and boundary conditions")
    save_svg(fig, "Fig2_Computational_Domain_BC.svg")


def plot_mesh_schematic():
    fig, ax = plt.subplots(figsize=(5.5, 3.4))
    ax.set_aspect("equal")
    ax.axis("off")

    rng = np.random.default_rng(42)
    outer_x, outer_y = np.meshgrid(np.linspace(-1.2, 2.3, 16), np.linspace(-0.9, 0.9, 9))
    points = np.column_stack([outer_x.ravel(), outer_y.ravel()])
    ring = []
    for radius, n in [(0.22, 36), (0.38, 44), (0.6, 56)]:
        theta = np.linspace(0, 2 * np.pi, n, endpoint=False)
        ring.append(np.column_stack([0.55 + 1.8 * radius * np.cos(theta), 0.35 * radius * np.sin(theta)]))
    points = np.vstack([points] + ring)
    points += rng.normal(scale=0.015, size=points.shape)
    triang = tri.Triangulation(points[:, 0], points[:, 1])
    ax.triplot(triang, color="#A9B4C2", linewidth=0.45)

    _, _, _, _, _, _, foil = naca_airfoil(chord=1.1, ta=0.02, twa=0.4, tb=0.13)
    ax.add_patch(Polygon(foil, closed=True, facecolor="#F8FAFC", edgecolor=COLORS["blue"], linewidth=1.4, zorder=5))
    ax.add_patch(Circle((0.28, 0.0), 0.18, fill=False, edgecolor=COLORS["red"], linewidth=1.1, linestyle="--"))
    ax.text(0.2, 0.33, "near-wall refinement", color=COLORS["red"], fontsize=9)
    ax.text(1.25, -0.58, "unstructured triangular mesh", color=COLORS["gray"], fontsize=9)
    ax.set_xlim(-1.0, 2.15)
    ax.set_ylim(-0.82, 0.82)
    ax.set_title("Schematic mesh refinement near the airfoil surface")
    save_svg(fig, "Fig3_Mesh_Schematic.svg")


def plot_architecture():
    fig, ax = plt.subplots(figsize=(9.2, 4.0))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    def box(x, y, w, h, title, subtitle, color):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.014,rounding_size=0.02",
                                    facecolor=color, edgecolor=COLORS["dark"], linewidth=1.0))
        ax.text(x + w / 2, y + h * 0.63, title, ha="center", va="center", fontweight="bold", fontsize=9.5)
        ax.text(x + w / 2, y + h * 0.33, subtitle, ha="center", va="center", fontsize=8.1)

    def arrow(a, b):
        ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=12, linewidth=1.15, color=COLORS["gray"]))

    box(0.04, 0.64, 0.15, 0.16, "Field images", "velocity / pressure / temperature", "#DCEBFA")
    box(0.25, 0.64, 0.16, 0.16, "Image features", "statistics + spatial signatures", "#FFF2D8")
    box(0.04, 0.28, 0.15, 0.16, "Geometry", "Ta, Twa, Tb, Ts, Tt, Tad", "#E5F3E6")
    box(0.25, 0.28, 0.16, 0.16, "Standardization", "train-set scaling", "#E8EAF6")
    box(0.49, 0.46, 0.16, 0.18, "Feature fusion", "concatenate modalities", "#F5E4E0")
    box(0.72, 0.46, 0.18, 0.18, "Regressor", "validation-selected FeatureMLP", "#DCEBFA")
    box(0.72, 0.16, 0.18, 0.14, "Outputs", "Nu and f", "#E5F3E6")
    box(0.72, 0.75, 0.18, 0.14, "Baseline", "geometry-only MLP", "#EEF1F4")

    arrow((0.19, 0.72), (0.25, 0.72))
    arrow((0.19, 0.36), (0.25, 0.36))
    arrow((0.41, 0.72), (0.49, 0.58))
    arrow((0.41, 0.36), (0.49, 0.52))
    arrow((0.65, 0.55), (0.72, 0.55))
    arrow((0.81, 0.46), (0.81, 0.30))
    arrow((0.81, 0.75), (0.81, 0.64))

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
        ax.set_title(f"{label}: R2={r2:.3f}, MAE={mae:.4g}")
        ax.grid(True, linestyle=":", color="#B8C0C8", alpha=0.8)
        ax.legend(frameon=False, loc="upper left")

    fig.suptitle("Test-set prediction accuracy of the multimodal fusion model", y=1.04, fontsize=12)
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
        ax.set_title(f"{label}: R2={r2:.3f}, MAE={mae:.4g}")
        ax.grid(True, linestyle=":", color="#B8C0C8", alpha=0.8)
        ax.legend(frameon=False, loc="upper left")
    fig.suptitle("Test-set prediction accuracy of the multimodal fusion model", y=1.04, fontsize=12)
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
    axes[0].set_title("Coefficient of determination")
    axes[0].grid(True, axis="y", linestyle=":", color="#B8C0C8", alpha=0.8)

    axes[1].set_ylabel("MAPE (%)")
    axes[1].set_xticks(x, target_order)
    axes[1].set_title("Mean absolute percentage error")
    axes[1].grid(True, axis="y", linestyle=":", color="#B8C0C8", alpha=0.8)

    for ax in axes:
        ax.legend(frameon=False, loc="best")

    fig.suptitle("Scalar-only MLP baseline versus multimodal fusion model", y=1.04, fontsize=12)
    fig.tight_layout()
    save_svg(fig, "Fig8_Model_Comparison.svg")


def plot_mlp_loss():
    path = os.path.join(RESULTS_DIR, "mlp_baseline_history.csv")
    df = pd.read_csv(path)

    fig, ax = plt.subplots(figsize=(5.8, 3.2))
    ax.plot(df["epoch"], df["train_loss"], color=COLORS["blue"], lw=1.6, label="Training loss")
    ax.plot(df["epoch"], df["val_loss"], color=COLORS["orange"], lw=1.6, label="Validation loss")
    ax.set_xlabel("Epoch")
    ax.set_ylabel("MSE loss (normalized)")
    ax.set_title("Scalar-only MLP baseline convergence")
    ax.grid(True, linestyle=":", color="#B8C0C8", alpha=0.8)
    ax.legend(frameon=False)
    fig.tight_layout()
    save_svg(fig, "Fig_MLP_Baseline_Loss.svg")


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

    ax.text(0.5, 0.96, "CFD-driven surrogate modeling and verification workflow",
            ha="center", va="center", fontsize=13, fontweight="bold", color=COLORS["dark"])
    save_svg(fig, "Fig2_Workflow.svg")


def main():
    setup_style()
    plot_geometry_schematic()
    plot_computational_domain()
    plot_mesh_schematic()
    plot_architecture()
    plot_prediction_scatter()
    plot_model_comparison()
    plot_mlp_loss()
    plot_workflow()


if __name__ == "__main__":
    main()
