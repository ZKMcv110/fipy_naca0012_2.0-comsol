#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""按七参数 PI-CNN-CBAM 最优结果构建真实芯片散热器三维模型。

本脚本只作为七参数三维验证入口：
- 参数来源固定为 `七参数_几何掩码代理优化/optimization_results_pi_cbam/best_params.json`；
- 建模实现复用 `12_真实感翼型柱散热器建模.py`；
- 输出目录独立为 `generated_7param_chip_heat_sink`，避免覆盖旧三维结果。
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
SOURCE_SCRIPT = ROOT / "12_真实感翼型柱散热器建模.py"
BEST_PARAMS_PATH = PROJECT_ROOT / "七参数_几何掩码代理优化" / "optimization_results_pi_cbam" / "best_params.json"
OUT_ROOT = ROOT / "generated_7param_chip_heat_sink"
PARAM_NAMES = ("Ta", "Twa", "Tb", "Ts", "Tt", "Tad", "theta")


def load_realistic_builder():
    spec = importlib.util.spec_from_file_location("realistic_airfoil_heat_sink", SOURCE_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载建模脚本: {SOURCE_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_params(params_path: Path) -> dict[str, float]:
    data = json.loads(params_path.read_text(encoding="utf-8"))
    raw_params = data.get("best_params", data)
    missing = [name for name in PARAM_NAMES if name not in raw_params]
    if missing:
        raise RuntimeError(f"七参数最优文件缺少字段: {missing}")
    return {name: float(raw_params[name]) for name in PARAM_NAMES}


def main() -> None:
    parser = argparse.ArgumentParser(description="构建七参数真实芯片散热器三维模型。")
    parser.add_argument("--case-name", default="pi_cbam_best", help="输出工况名。")
    parser.add_argument("--params-json", type=Path, default=BEST_PARAMS_PATH, help="七参数JSON路径，支持 best_params 包装格式。")
    parser.add_argument("--theta", type=float, default=None, help="临时覆盖参数文件中的theta，单位为度。")
    parser.add_argument("--mesh-hauto", type=int, default=5)
    parser.add_argument("--skip-mesh", action="store_true", help="只生成几何、材料、物理场和研究。")
    parser.add_argument("--solve", action="store_true", help="生成后立即求解。")
    args = parser.parse_args()

    builder = load_realistic_builder()
    builder.OUT_ROOT = OUT_ROOT
    params = load_params(args.params_json)
    if args.theta is not None:
        params["theta"] = float(args.theta)
    print("[INFO] 七参数来源:", args.params_json)
    print("[INFO] 七参数:", json.dumps(params, ensure_ascii=False))
    saved = builder.build_case(args.case_name, args.mesh_hauto, args.solve, args.skip_mesh, params)
    print("[INFO] 七参数三维模型已保存:", saved)


if __name__ == "__main__":
    main()
