#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Build Fig. 8: baseline vs optimal CFD velocity/temperature field comparison.

The figure uses the verified COMSOL/CFD outputs under consol_cfddata, not CNN
prediction screenshots. By default, case 1 is used as the baseline and the
highest target_param in labels.csv is used as the optimal case.
"""

from __future__ import annotations

import argparse
import base64
import csv
import html
import os
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


DATA_DIR = Path("consol_cfddata")
OUT_DIR = Path("paper_figures_svg")
SVG_OUT = OUT_DIR / "Fig8_Baseline_Optimal_Field_Comparison.svg"
PNG_OUT = OUT_DIR / "Fig8_Baseline_Optimal_Field_Comparison.png"

W, H = 1500, 940
BLUE = "#1f5fd0"
BLUE_DARK = "#083b91"
GREEN = "#2f7d32"
GREEN_LIGHT = "#f2fbef"
INK = "#111827"
MUTED = "#5f6b7a"
GRID = "#d4dce8"
WHITE = "#ffffff"
RED = "#c62828"

T = {
    "vel": "\u901f\u5ea6\u573a\u4e91\u56fe",
    "temp": "\u6e29\u5ea6\u573a\u4e91\u56fe",
    "baseline": "\u57fa\u51c6\u7ed3\u6784",
    "optimal": "\u6700\u4f18\u7ed3\u6784",
    "eta": "\u03b7",
}


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def text(
    x: float,
    y: float,
    body: str,
    size: int = 24,
    fill: str = INK,
    weight: str = "400",
    anchor: str = "middle",
) -> str:
    return (
        f'<text x="{x}" y="{y}" fill="{fill}" font-size="{size}" '
        f'font-weight="{weight}" text-anchor="{anchor}">{esc(body)}</text>'
    )


def rounded(x: float, y: float, w: float, h: float, stroke: str, fill: str = WHITE, r: int = 12) -> str:
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" ry="{r}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="2"/>'
    )


def image_to_data_uri(path: Path, max_size: tuple[int, int]) -> tuple[str, int, int]:
    img = trim_whitespace(Image.open(path).convert("RGB"))
    img.thumbnail(max_size, Image.LANCZOS)
    canvas = Image.new("RGB", max_size, "white")
    x = (max_size[0] - img.width) // 2
    y = (max_size[1] - img.height) // 2
    canvas.paste(img, (x, y))
    buf = BytesIO()
    canvas.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii"), max_size[0], max_size[1]


def trim_whitespace(img: Image.Image, threshold: int = 248, pad: int = 8) -> Image.Image:
    """Trim near-white margins from matplotlib/COMSOL PNG exports."""
    px = img.convert("RGB")
    width, height = px.size
    data = px.load()
    xs: list[int] = []
    ys: list[int] = []
    for y in range(height):
        for x in range(width):
            r, g, b = data[x, y]
            if min(r, g, b) < threshold:
                xs.append(x)
                ys.append(y)
    if not xs or not ys:
        return img
    left = max(0, min(xs) - pad)
    top = max(0, min(ys) - pad)
    right = min(width, max(xs) + pad)
    bottom = min(height, max(ys) + pad)
    return img.crop((left, top, right, bottom))


def read_labels() -> list[dict[str, str]]:
    labels_path = DATA_DIR / "labels.csv"
    if not labels_path.exists():
        raise FileNotFoundError(f"Missing {labels_path}")
    with labels_path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def has_required_images(case_id: int) -> bool:
    case_dir = DATA_DIR / f"case_{case_id}_cfd_solution"
    return (case_dir / "velocity_magnitude.png").exists() and (case_dir / "temperature.png").exists()


def best_case_id(rows: list[dict[str, str]]) -> int:
    valid: list[tuple[float, int]] = []
    for row in rows:
        try:
            case_id = int(float(row["case_id"]))
            complete = str(row.get("image_complete", "True")).lower() in {"true", "1", "yes"}
            target = float(row["target_param"])
        except (KeyError, TypeError, ValueError):
            continue
        if complete and has_required_images(case_id):
            valid.append((target, case_id))
    if not valid:
        raise RuntimeError("No valid CFD cases with complete velocity and temperature images.")
    return max(valid)[1]


def row_by_case(rows: list[dict[str, str]], case_id: int) -> dict[str, str]:
    for row in rows:
        try:
            if int(float(row["case_id"])) == case_id:
                return row
        except (KeyError, TypeError, ValueError):
            continue
    raise KeyError(f"case_id {case_id} not found in labels.csv")


def metric_line(row: dict[str, str]) -> str:
    nu = float(row["Nu"])
    f_val = float(row["f"])
    eta = float(row.get("target_param", nu / (f_val ** (1 / 3))))
    return f"Nu={nu:.3f}    f={f_val:.5f}    {T['eta']}={eta:.3f}"


def panel_label(prefix: str, name: str, case_id: int) -> str:
    return f"{prefix} {name}  Case {case_id}"


def build_svg(baseline_case: int, optimal_case: int, baseline_row: dict[str, str], optimal_row: dict[str, str]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    panel_w, panel_h = 555, 270
    x1, x2 = 250, 860
    y1, y2 = 165, 505

    images = {
        "base_vel": DATA_DIR / f"case_{baseline_case}_cfd_solution" / "velocity_magnitude.png",
        "base_temp": DATA_DIR / f"case_{baseline_case}_cfd_solution" / "temperature.png",
        "opt_vel": DATA_DIR / f"case_{optimal_case}_cfd_solution" / "velocity_magnitude.png",
        "opt_temp": DATA_DIR / f"case_{optimal_case}_cfd_solution" / "temperature.png",
    }

    svg: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
        "<defs>",
        '<marker id="arrow" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto" markerUnits="strokeWidth">',
        '<path d="M2,2 L10,6 L2,10 z" fill="#c62828"/>',
        "</marker>",
        "<style><![CDATA[",
        'text{font-family:"Microsoft YaHei","SimHei","Noto Sans CJK SC",Arial,sans-serif;}',
        "]]></style>",
        "</defs>",
        f'<rect width="{W}" height="{H}" fill="{WHITE}"/>',
        text(x1 + panel_w / 2, 85, T["vel"], size=30, fill=BLUE_DARK, weight="700"),
        text(x2 + panel_w / 2, 85, T["temp"], size=30, fill=BLUE_DARK, weight="700"),
        text(120, y1 + 128, T["baseline"], size=28, fill=BLUE_DARK, weight="700"),
        text(120, y1 + 165, f"Case {baseline_case}", size=23, fill=MUTED, weight="700"),
        text(120, y2 + 128, T["optimal"], size=28, fill=GREEN, weight="700"),
        text(120, y2 + 165, f"Case {optimal_case}", size=23, fill=MUTED, weight="700"),
    ]

    for x, y, key, label in [
        (x1, y1, "base_vel", panel_label("(a)", T["baseline"], baseline_case)),
        (x2, y1, "base_temp", panel_label("(b)", T["baseline"], baseline_case)),
        (x1, y2, "opt_vel", panel_label("(c)", T["optimal"], optimal_case)),
        (x2, y2, "opt_temp", panel_label("(d)", T["optimal"], optimal_case)),
    ]:
        uri, iw, ih = image_to_data_uri(images[key], (panel_w, panel_h))
        svg.append(rounded(x - 8, y - 8, panel_w + 16, panel_h + 16, stroke=GRID, fill="#fbfdff", r=8))
        svg.append(f'<image x="{x}" y="{y}" width="{iw}" height="{ih}" href="{uri}"/>')
        svg.append(text(x + panel_w / 2, y + panel_h + 38, label, size=21, fill=INK, weight="700"))

    svg.append(rounded(245, 840, 500, 48, stroke=BLUE, fill="#f7fbff", r=10))
    svg.append(text(495, 872, f"{T['baseline']}: {metric_line(baseline_row)}", size=20, fill=INK, weight="700"))
    svg.append(rounded(805, 840, 520, 48, stroke=GREEN, fill=GREEN_LIGHT, r=10))
    svg.append(text(1065, 872, f"{T['optimal']}: {metric_line(optimal_row)}", size=20, fill=INK, weight="700"))
    svg.append("</svg>")

    SVG_OUT.write_text("\n".join(svg), encoding="utf-8", newline="\n")


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
        Path("C:/Windows/Fonts/simsun.ttc"),
        Path("C:/Windows/Fonts/arial.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def paste_fit(canvas: Image.Image, img_path: Path, box: tuple[int, int, int, int]) -> None:
    x, y, w, h = box
    img = trim_whitespace(Image.open(img_path).convert("RGB"))
    img.thumbnail((w, h), Image.LANCZOS)
    canvas.paste(img, (x + (w - img.width) // 2, y + (h - img.height) // 2))


def build_png(baseline_case: int, optimal_case: int, baseline_row: dict[str, str], optimal_row: dict[str, str]) -> None:
    panel_w, panel_h = 555, 270
    x1, x2 = 250, 860
    y1, y2 = 165, 505
    canvas = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(canvas)
    font_head = load_font(30)
    font_row = load_font(28)
    font_label = load_font(21)
    font_metric = load_font(20)
    font_note = load_font(17)

    def center(x: int, y: int, body: str, font: ImageFont.ImageFont, fill: str) -> None:
        bbox = draw.textbbox((0, 0), body, font=font)
        draw.text((x - (bbox[2] - bbox[0]) / 2, y), body, fill=fill, font=font)

    center(x1 + panel_w // 2, 55, T["vel"], font_head, BLUE_DARK)
    center(x2 + panel_w // 2, 55, T["temp"], font_head, BLUE_DARK)
    center(120, y1 + 110, T["baseline"], font_row, BLUE_DARK)
    center(120, y1 + 145, f"Case {baseline_case}", font_label, MUTED)
    center(120, y2 + 110, T["optimal"], font_row, GREEN)
    center(120, y2 + 145, f"Case {optimal_case}", font_label, MUTED)

    for x, y, path, label in [
        (x1, y1, DATA_DIR / f"case_{baseline_case}_cfd_solution" / "velocity_magnitude.png", panel_label("(a)", T["baseline"], baseline_case)),
        (x2, y1, DATA_DIR / f"case_{baseline_case}_cfd_solution" / "temperature.png", panel_label("(b)", T["baseline"], baseline_case)),
        (x1, y2, DATA_DIR / f"case_{optimal_case}_cfd_solution" / "velocity_magnitude.png", panel_label("(c)", T["optimal"], optimal_case)),
        (x2, y2, DATA_DIR / f"case_{optimal_case}_cfd_solution" / "temperature.png", panel_label("(d)", T["optimal"], optimal_case)),
    ]:
        draw.rounded_rectangle((x - 8, y - 8, x + panel_w + 8, y + panel_h + 8), radius=8, outline=GRID, width=2, fill="#fbfdff")
        paste_fit(canvas, path, (x, y, panel_w, panel_h))
        center(x + panel_w // 2, y + panel_h + 18, label, font_label, INK)

    draw.rounded_rectangle((245, 840, 745, 888), radius=10, outline=BLUE, width=2, fill="#f7fbff")
    center(495, 852, f"{T['baseline']}: {metric_line(baseline_row)}", font_metric, INK)
    draw.rounded_rectangle((805, 840, 1325, 888), radius=10, outline=GREEN, width=2, fill=GREEN_LIGHT)
    center(1065, 852, f"{T['optimal']}: {metric_line(optimal_row)}", font_metric, INK)
    canvas.save(PNG_OUT)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Fig. 8 CFD baseline vs optimal comparison.")
    parser.add_argument("--baseline-case", type=int, default=1, help="Baseline CFD case id.")
    parser.add_argument("--optimal-case", type=int, default=None, help="Optimal CFD case id. Defaults to max target_param.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = read_labels()
    baseline_case = args.baseline_case
    optimal_case = args.optimal_case or best_case_id(rows)
    if not has_required_images(baseline_case):
        raise FileNotFoundError(f"case {baseline_case} is missing velocity_magnitude.png or temperature.png")
    if not has_required_images(optimal_case):
        raise FileNotFoundError(f"case {optimal_case} is missing velocity_magnitude.png or temperature.png")

    baseline_row = row_by_case(rows, baseline_case)
    optimal_row = row_by_case(rows, optimal_case)
    build_svg(baseline_case, optimal_case, baseline_row, optimal_row)
    build_png(baseline_case, optimal_case, baseline_row, optimal_row)

    print(f"Baseline case: {baseline_case}  {metric_line(baseline_row)}")
    print(f"Optimal case : {optimal_case}  {metric_line(optimal_row)}")
    print(f"Saved SVG: {SVG_OUT}")
    print(f"Saved PNG: {PNG_OUT}")


if __name__ == "__main__":
    main()
