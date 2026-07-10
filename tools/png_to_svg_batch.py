#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""批量将 PNG 图片转换为 SVG。

说明：
1. PNG 是栅格图，无法无损还原为真正的可编辑矢量图。
2. 安装 vtracer 后，本脚本会输出近似矢量路径，适合在 Inkscape/AI 中编辑。
3. 未安装 vtracer 时，本脚本只生成内嵌 PNG 的 SVG，版面可用但图形内容不可编辑。

默认输入：
    大论文初稿/完整论文初稿_图片汇总

默认输出：
    大论文初稿/完整论文初稿_图片汇总_svg
"""

from __future__ import annotations

import argparse
import base64
import json
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_DIR = ROOT / "大论文初稿" / "完整论文初稿_图片汇总"
DEFAULT_OUTPUT_DIR = ROOT / "大论文初稿" / "完整论文初稿_图片汇总_svg"


def load_image_size(path: Path) -> tuple[int, int]:
    """读取 PNG 宽高，优先使用 Pillow；没有 Pillow 时解析 PNG 头。"""
    try:
        from PIL import Image

        with Image.open(path) as image:
            return int(image.width), int(image.height)
    except Exception:
        data = path.read_bytes()
        if len(data) >= 24 and data[:8] == b"\x89PNG\r\n\x1a\n":
            width = int.from_bytes(data[16:20], "big")
            height = int.from_bytes(data[20:24], "big")
            return width, height
        raise RuntimeError(f"无法读取图片尺寸: {path}")


def write_embedded_svg(source: Path, target: Path) -> dict[str, Any]:
    width, height = load_image_size(source)
    encoded = base64.b64encode(source.read_bytes()).decode("ascii")
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">\n'
        f'  <image href="data:image/png;base64,{encoded}" width="{width}" height="{height}"/>\n'
        "</svg>\n"
    )
    target.write_text(svg, encoding="utf-8")
    return {
        "mode": "embedded_png",
        "editable": False,
        "note": "未安装 vtracer，SVG 仅内嵌原 PNG，图形内容不可编辑。",
    }


def convert_with_vtracer(source: Path, target: Path) -> dict[str, Any]:
    import vtracer

    vtracer.convert_image_to_svg_py(
        str(source),
        str(target),
        colormode="color",
        hierarchical="stacked",
        mode="spline",
        filter_speckle=4,
        color_precision=6,
        layer_difference=16,
        corner_threshold=60,
        length_threshold=4.0,
        max_iterations=10,
        splice_threshold=45,
        path_precision=3,
    )
    return {
        "mode": "vtracer",
        "editable": True,
        "note": "由 vtracer 近似矢量化，路径可编辑，但与原 PNG 不保证完全一致。",
    }


def convert_one(source: Path, output_dir: Path, force_embed: bool) -> dict[str, Any]:
    target = output_dir / f"{source.stem}.svg"
    output_dir.mkdir(parents=True, exist_ok=True)

    if force_embed:
        result = write_embedded_svg(source, target)
    else:
        try:
            result = convert_with_vtracer(source, target)
        except ModuleNotFoundError:
            result = write_embedded_svg(source, target)
        except Exception as exc:
            result = write_embedded_svg(source, target)
            result["vectorize_error"] = str(exc)

    result.update(
        {
            "source": str(source),
            "target": str(target),
            "source_size_bytes": source.stat().st_size,
            "target_size_bytes": target.stat().st_size,
        }
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="批量将 PNG 图片转换为 SVG。")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--force-embed", action="store_true", help="强制生成内嵌 PNG 的 SVG。")
    args = parser.parse_args()

    input_dir = args.input_dir.resolve()
    output_dir = args.output_dir.resolve()
    if not input_dir.exists():
        raise FileNotFoundError(input_dir)

    png_files = sorted(input_dir.glob("*.png"))
    records = [convert_one(path, output_dir, args.force_embed) for path in png_files]
    manifest = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "total_png": len(png_files),
        "editable_svg": sum(1 for row in records if row["editable"]),
        "embedded_svg": sum(1 for row in records if not row["editable"]),
        "records": records,
    }
    manifest_path = output_dir / "conversion_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] PNG 数量: {len(png_files)}")
    print(f"[OK] 可编辑矢量 SVG: {manifest['editable_svg']}")
    print(f"[OK] 内嵌 PNG SVG: {manifest['embedded_svg']}")
    print(f"[OK] 输出目录: {output_dir}")
    print(f"[OK] 转换清单: {manifest_path}")


if __name__ == "__main__":
    main()
