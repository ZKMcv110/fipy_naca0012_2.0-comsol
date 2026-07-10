#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""把两组 COMSOL 原生云图并排排版，保留每个面板的原生指标条。"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/arial.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def compose(baseline: Path, optimized: Path, output: Path, title: str) -> None:
    left = Image.open(baseline).convert("RGB")
    right = Image.open(optimized).convert("RGB")
    panel_width = 1760
    panel_height = round(left.height * panel_width / left.width)
    left = left.resize((panel_width, panel_height), Image.Resampling.LANCZOS)
    right = right.resize((panel_width, panel_height), Image.Resampling.LANCZOS)

    header = 100
    gap = 40
    canvas = Image.new("RGB", (panel_width * 2 + gap, panel_height + header), "white")
    canvas.paste(left, (0, header))
    canvas.paste(right, (panel_width + gap, header))
    draw = ImageDraw.Draw(canvas)
    title_font = font(42)
    label_font = font(34)
    draw.text((canvas.width // 2, 18), title, fill=(20, 35, 60), font=title_font, anchor="ma")
    draw.text((panel_width // 2, 62), "(a) Baseline", fill=(20, 35, 60), font=label_font, anchor="ma")
    draw.text((panel_width + gap + panel_width // 2, 62), "(b) Optimized", fill=(20, 35, 60), font=label_font, anchor="ma")
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, format="PNG", optimize=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="合成保留 COMSOL 原生指标条的对比图。")
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--optimized", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--title", required=True)
    args = parser.parse_args()
    compose(args.baseline, args.optimized, args.output, args.title)
    print(f"[OK] {args.output}")


if __name__ == "__main__":
    main()
