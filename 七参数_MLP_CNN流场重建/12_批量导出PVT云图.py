#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""批量导出 PVT 三个场的 COMSOL 风格云图。

该脚本复用 11_导出COMSOL风格单变量图.py 的单变量绘图函数，
只负责把论文主线需要的压力场 p、速度大小 U、温度场 T 一次导出。
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
SINGLE_EXPORT_SCRIPT = ROOT / "11_导出COMSOL风格单变量图.py"
DEFAULT_VARIABLES = ["p", "U", "T"]


def load_single_export_module():
    spec = importlib.util.spec_from_file_location("comsol_style_export", SINGLE_EXPORT_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载导图脚本: {SINGLE_EXPORT_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_variables(value: str) -> list[str]:
    variables = [item.strip() for item in value.split(",") if item.strip()]
    allowed = {"u", "v", "U", "p", "T"}
    invalid = [item for item in variables if item not in allowed]
    if invalid:
        raise ValueError(f"不支持的变量: {invalid}，可选: {sorted(allowed)}")
    return variables


def export_variable(mod, args, variable: str) -> list[dict[str, str]]:
    field_dir = Path(args.field_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    data, extent, domain = mod.load_physical_grid(field_dir, args.case_id)
    polygons = mod.make_airfoil_polygons(mod.load_case_params(args.case_id))
    truth = mod.read_variable(data, variable, domain.shape)
    pred = None
    field_names: list[str] = []
    if not args.truth_only:
        train_mod = mod.load_train_module()
        pred_fields, field_names = mod.predict_case(
            train_mod,
            Path(args.model_dir),
            Path(args.dataset),
            field_dir,
            args.case_id,
        )
        if variable not in field_names:
            raise ValueError(f"模型数据集没有 {variable} 通道，当前通道: {field_names}")
        pred = pred_fields[field_names.index(variable)]

    if pred is None:
        vmin = float(np.nanmin(truth))
        vmax = float(np.nanmax(truth))
    else:
        both = np.concatenate([truth.ravel(), pred.ravel()])
        vmin = float(np.nanmin(both))
        vmax = float(np.nanmax(both))

    prefix = f"case_{args.case_id}_{variable}"
    outputs: list[dict[str, str]] = []
    truth_path = output_dir / f"{prefix}_comsol_sample_style.png"
    mod.draw_single_field(truth, domain, extent, truth_path, args.cmap, vmin, vmax, not args.no_solid_outline, polygons)
    outputs.append({"variable": variable, "kind": "comsol_sample", "path": str(truth_path)})

    if pred is not None:
        pred_path = output_dir / f"{prefix}_pred_style.png"
        error_path = output_dir / f"{prefix}_error_style.png"
        mod.draw_single_field(pred, domain, extent, pred_path, args.cmap, vmin, vmax, not args.no_solid_outline, polygons)
        mod.draw_single_field(pred - truth, domain, extent, error_path, "coolwarm", None, None, not args.no_solid_outline, polygons)
        outputs.extend(
            [
                {"variable": variable, "kind": "pred", "path": str(pred_path)},
                {"variable": variable, "kind": "error", "path": str(error_path)},
            ]
        )
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description="批量导出 PVT 三场 COMSOL 风格云图")
    parser.add_argument("--case-id", type=int, default=20009)
    parser.add_argument("--variables", default=",".join(DEFAULT_VARIABLES), help="逗号分隔变量，默认 p,U,T")
    parser.add_argument("--field-dir", default=str(PROJECT_ROOT / "七参数_PDE_PINN尝试" / "field_data_320x96"))
    parser.add_argument("--dataset", default=str(ROOT / "data" / "field_reconstruction_dataset_320x96_first20.npz"))
    parser.add_argument("--model-dir", default=str(ROOT / "results" / "unet_overfit_case_20009_e300"))
    parser.add_argument("--output-dir", default=str(ROOT / "results" / "pvt_comsol_style_exports"))
    parser.add_argument("--cmap", default="jet")
    parser.add_argument("--no-solid-outline", action="store_true")
    parser.add_argument("--truth-only", action="store_true")
    args = parser.parse_args()

    mod = load_single_export_module()
    outputs: list[dict[str, str]] = []
    for variable in parse_variables(args.variables):
        outputs.extend(export_variable(mod, args, variable))

    summary = {
        "case_id": args.case_id,
        "variables": parse_variables(args.variables),
        "truth_only": bool(args.truth_only),
        "dataset": str(Path(args.dataset).resolve()),
        "field_dir": str(Path(args.field_dir).resolve()),
        "model_dir": str(Path(args.model_dir).resolve()),
        "outputs": outputs,
    }
    summary_path = Path(args.output_dir) / f"case_{args.case_id}_pvt_export_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
