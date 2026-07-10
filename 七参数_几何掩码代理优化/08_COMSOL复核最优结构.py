#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""读取差分进化最优参数，调度COMSOL进行最终复核。

注意：COMSOL复核是最终物理验证步骤，不参与差分进化迭代。
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

from common import PARAM_COLS, ROOT, ensure_dir, eta_value, load_json, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description="COMSOL复核差分进化最优七参数")
    parser.add_argument("--best", default=str(ROOT / "optimization_results" / "best_params.json"))
    parser.add_argument("--output-dir", default=str(ROOT / "validation_results"))
    parser.add_argument("--batch-script", default=str(ROOT / "02_七参数COMSOL批量求解.py"))
    parser.add_argument("--single-script", default=None, help="可选：转发给批量脚本的单工况COMSOL脚本路径。")
    parser.add_argument("--single-script-ignores-theta", action="store_true", help="当手动指定旧六参数脚本时启用。")
    parser.add_argument("--allow-ignore-theta", action="store_true", help="仅调试用：允许旧六参数脚本忽略theta。")
    args = parser.parse_args()

    best = load_json(Path(args.best))
    params = best["best_params"]
    prediction = best.get("prediction", {})
    baseline = best.get("baseline", {"Nu0": 1.0, "f0": 1.0})

    out_dir = ensure_dir(Path(args.output_dir))
    sample_path = out_dir / "best_sample.csv"
    row = {"case_id": 1, **{name: params[name] for name in PARAM_COLS}}
    pd.DataFrame([row]).to_csv(sample_path, index=False, encoding="utf-8-sig")

    cmd = [
        sys.executable,
        str(Path(args.batch_script)),
        "--samples", str(sample_path),
        "--output-dir", str(out_dir / "comsol"),
        "--force",
    ]
    if args.allow_ignore_theta:
        cmd.append("--allow-ignore-theta")
    if args.single_script:
        cmd.extend(["--single-script", str(Path(args.single_script))])
    if args.single_script_ignores_theta:
        cmd.append("--single-script-ignores-theta")
    completed = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")

    result_path = out_dir / "comsol" / "case_1" / "result.json"
    result = load_json(result_path) if result_path.exists() else {"failure_reason": completed.stderr or completed.stdout}
    report = {
        "best_params": params,
        "proxy_prediction": prediction,
        "comsol_result": result,
        "note": "COMSOL复核用于验证代理模型优化结果；若失败，请优先检查COMSOL环境、边界选择和网格求解日志。",
    }
    if result.get("Nu") and result.get("f"):
        report["comsol_result"]["eta_cfd"] = eta_value(result["Nu"], result["f"], baseline["Nu0"], baseline["f0"])
        report["error"] = {
            "Nu_pred_minus_cfd": prediction.get("Nu_pred", 0.0) - result["Nu"],
            "f_pred_minus_cfd": prediction.get("f_pred", 0.0) - result["f"],
            "eta_pred_minus_cfd": prediction.get("eta_pred", 0.0) - report["comsol_result"]["eta_cfd"],
        }
    write_json(out_dir / "final_validation_report.json", report)
    lines = [
        "# 七参数最优结构COMSOL复核报告",
        "",
        "## 最优参数",
        json.dumps(params, ensure_ascii=False, indent=2),
        "",
        "## 代理模型预测",
        json.dumps(prediction, ensure_ascii=False, indent=2),
        "",
        "## COMSOL复核结果",
        json.dumps(result, ensure_ascii=False, indent=2),
    ]
    (out_dir / "final_validation_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[OK] 复核报告已生成: {out_dir / 'final_validation_report.md'}")


if __name__ == "__main__":
    main()
