#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""为旧 COMSOL 复算脚本准备兼容输入。

本脚本只在当前新目录写文件，不修改旧优化目录和旧复算结果。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
PARAM_COLS = ["Ta", "Twa", "Tb", "Ts", "Tt", "Tad", "theta"]


def main() -> None:
    parser = argparse.ArgumentParser(description="准备 MLP-CNN DE 候选结构的 CFD 复算输入")
    parser.add_argument(
        "--best",
        default=str(ROOT / "optimization_results" / "mlp_cnn_de_multiloss_e10" / "best_params.json"),
        help="DE 输出的 best_params.json",
    )
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "cfd_validation_inputs" / "mlp_cnn_de_multiloss_e10"),
        help="兼容输入输出目录",
    )
    parser.add_argument(
        "--validation-dir",
        default=str(ROOT / "validation_results" / "mlp_cnn_de_multiloss_e10"),
        help="CFD 复算输出目录",
    )
    args = parser.parse_args()

    best_path = Path(args.best)
    data = json.loads(best_path.read_text(encoding="utf-8"))
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    compatible = {
        "best_params": data["best_params"],
        "prediction": data["prediction"],
        "baseline": {"Nu0": 30.366123, "f0": 0.092996},
        "model_source": data.get("model_dir", ""),
        "note": "MLP-CNN 流热场重建代理模型 DE 候选；必须使用 CFD 复算验证。",
    }
    compatible_path = out_dir / "best_params_compatible.json"
    compatible_path.write_text(json.dumps(compatible, ensure_ascii=False, indent=2), encoding="utf-8")

    row = {"case_id": 1, **{name: data["best_params"][name] for name in PARAM_COLS}}
    sample_path = out_dir / "best_sample.csv"
    pd.DataFrame([row]).to_csv(sample_path, index=False, encoding="utf-8-sig")

    validation_dir = Path(args.validation_dir)
    old_root = PROJECT_ROOT / "七参数_几何掩码代理优化"
    command = (
        "python "
        f"\"{old_root / '08_COMSOL复核最优结构.py'}\" "
        f"--best \"{compatible_path}\" "
        f"--output-dir \"{validation_dir}\" "
        f"--batch-script \"{old_root / '02_七参数COMSOL批量求解.py'}\" "
        f"--single-script \"{old_root / '02a_七参数COMSOL单工况求解.py'}\""
    )
    (out_dir / "run_cfd_validation.ps1").write_text(command + "\n", encoding="utf-8")
    summary = {
        "compatible_best": str(compatible_path),
        "best_sample": str(sample_path),
        "validation_output_dir": str(validation_dir),
        "run_command": command,
    }
    (out_dir / "README_validation.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
