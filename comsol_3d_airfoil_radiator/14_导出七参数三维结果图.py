#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""导出七参数真实芯片散热器三维模型的内置图组。"""

from __future__ import annotations

import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_MODEL = (
    ROOT
    / "generated_7param_chip_heat_sink"
    / "pi_cbam_best"
    / "pi_cbam_best_realistic_airfoil_heat_sink.mph"
)

PLOT_GROUPS = {
    "appearance": "pg_geometry_preview",
    "temperature": "pg_clean_temp",
    "velocity": "pg_clean_vel",
    "pressure": "pg_clean_pressure",
    "mesh": "pg_mesh_check",
}


def export_plot(java_model, plot_tag: str, output_path: Path, width: int, height: int) -> None:
    result = java_model.result()
    java_model.result(plot_tag).run()
    export_tag = f"exp_{plot_tag}"
    try:
        result.export().remove(export_tag)
    except Exception:
        pass
    image = result.export().create(export_tag, "Image3D")
    image.set("plotgroup", plot_tag)
    image.set("pngfilename", str(output_path.resolve()))
    image.set("width", str(width))
    image.set("height", str(height))
    image.set("unit", "px")
    image.set("lockratio", "off")
    show_legend = plot_tag not in {"pg_geometry_preview", "pg_mesh_check"}
    image.set("options3d", "on" if show_legend else "off")
    image.set("legend3d", "on" if show_legend else "off")
    image.set("background", "color")
    image.set("customcolor", [1.0, 1.0, 1.0])
    image.run()


def main() -> None:
    parser = argparse.ArgumentParser(description="导出七参数三维模型图组。")
    parser.add_argument("--model", default=str(DEFAULT_MODEL))
    parser.add_argument("--out-dir", default=str(DEFAULT_MODEL.parent / "exports"))
    parser.add_argument("--prefix", default="pi_cbam_best", help="导出图片文件名前缀。")
    parser.add_argument("--width", type=int, default=1800)
    parser.add_argument("--height", type=int, default=1100)
    args = parser.parse_args()

    model_path = Path(args.model)
    if not model_path.exists():
        raise FileNotFoundError(model_path)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    import mph

    client = mph.start(cores=4)
    try:
        model = client.load(str(model_path.resolve()))
        java_model = model.java
        for name, plot_tag in PLOT_GROUPS.items():
            output = out_dir / f"{args.prefix}_{name}.png"
            try:
                export_plot(java_model, plot_tag, output, args.width, args.height)
                print(f"[INFO] exported {plot_tag}: {output}")
            except Exception as exc:
                print(f"[WARN] skip missing or invalid plot group {plot_tag}: {exc}")
    finally:
        try:
            client.disconnect()
        except Exception:
            pass


if __name__ == "__main__":
    main()
