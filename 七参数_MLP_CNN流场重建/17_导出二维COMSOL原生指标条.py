#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""从已求解二维 COMSOL MPH 导出带原生指标条的 P/U/T 云图。"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any


PLOT_DEFINITIONS = {
    "velocity": ("spf.U", "速度大小", "0", "8"),
    "pressure": ("p", "压力", "-10", "50"),
    "temperature": ("T", "温度", "293.15", "345"),
}


def try_set(target: Any, key: str, value: Any) -> bool:
    try:
        target.set(key, value)
        return True
    except Exception:
        return False


def set_bool(target: Any, key: str, enabled: bool) -> None:
    try_set(target, key, "on" if enabled else "off")
    try_set(target, key, enabled)


def remove_node(container: Any, tag: str) -> None:
    try:
        container.remove(tag)
    except Exception:
        pass


def create_plot_group(java_model: Any, tag: str, expression: str, minimum: str, maximum: str) -> None:
    result = java_model.result()
    remove_node(result, tag)
    plot_group = result.create(tag, "PlotGroup2D")
    try_set(plot_group, "data", "my_dset")
    set_bool(plot_group, "showlegends", True)
    set_bool(plot_group, "showlegendsunit", True)
    set_bool(plot_group, "showlegendstitle", True)
    set_bool(plot_group, "showlegendsmaxmin", True)
    try_set(plot_group, "titletype", "none")

    surface = plot_group.create("surface", "Surface")
    surface.set("expr", expression)
    set_bool(surface, "colorlegend", True)
    try_set(surface, "rangecoloractive", "on")
    try_set(surface, "rangecolormin", minimum)
    try_set(surface, "rangecolormax", maximum)
    plot_group.run()


def export_plot(java_model: Any, tag: str, output_path: Path) -> None:
    result = java_model.result()
    export_tag = f"export_{tag}"
    remove_node(result.export(), export_tag)
    image = result.export().create(export_tag, "Image2D")
    image.set("plotgroup", tag)
    image.set("target", "file")
    image.set("filename", str(output_path.resolve()))
    image.set("width", "2200")
    image.set("height", "900")
    image.set("unit", "px")
    set_bool(image, "options2d", True)
    set_bool(image, "legend2d", True)
    try_set(image, "background", "color")
    try_set(image, "customcolor", [1.0, 1.0, 1.0])
    image.run()


def export_model(model_path: Path, output_dir: Path, prefix: str) -> None:
    import mph

    output_dir.mkdir(parents=True, exist_ok=True)
    client = mph.start(cores=4)
    try:
        model = client.load(str(model_path.resolve()))
        java_model = model.java
        for name, (expression, label, minimum, maximum) in PLOT_DEFINITIONS.items():
            tag = f"pg_native_{name}"
            create_plot_group(java_model, tag, expression, minimum, maximum)
            output_path = output_dir / f"{prefix}_{name}.png"
            export_plot(java_model, tag, output_path)
            print(f"[OK] {label}: {output_path}")
    finally:
        try:
            client.disconnect()
        except Exception:
            pass


def main() -> None:
    parser = argparse.ArgumentParser(description="导出二维 COMSOL 原生色标云图。")
    parser.add_argument("--model", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--prefix", required=True)
    args = parser.parse_args()
    export_model(Path(args.model), Path(args.output_dir), args.prefix)


if __name__ == "__main__":
    main()
