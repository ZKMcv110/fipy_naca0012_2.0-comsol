#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""七参数流程轻量冒烟测试。

该脚本只验证命令入口和预测权重能否正常调用，不训练模型、不运行差分进化、不调用 COMSOL。
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from common import ROOT, ensure_dir, write_json


TEST_COMMANDS = [
    {
        "name": "PI-CNN-CBAM预测",
        "args": ["10_预测_PI_CNN_CBAM性能.py"],
        "expect_text": "[OK]",
    },
    {
        "name": "LHS采样入口",
        "args": ["01_七参数LHS采样.py", "--help"],
        "expect_text": "生成七参数LHS采样表",
    },
    {
        "name": "COMSOL批量调度入口",
        "args": ["02_七参数COMSOL批量求解.py", "--help"],
        "expect_text": "dry-run",
    },
    {
        "name": "标签重建入口",
        "args": ["03_从COMSOL结果重建标签.py", "--help"],
        "expect_text": "重建七参数 labels_7param.csv",
    },
    {
        "name": "几何掩码生成入口",
        "args": ["04_生成几何掩码图.py", "--help"],
        "expect_text": "生成七参数几何掩码图",
    },
    {
        "name": "COMSOL复核入口",
        "args": ["08_COMSOL复核最优结构.py", "--help"],
        "expect_text": "COMSOL复核差分进化最优七参数",
    },
    {
        "name": "PI-CNN-CBAM差分进化入口",
        "args": ["11_差分进化优化_PI_CNN_CBAM七参数.py", "--help"],
        "expect_text": "PI-CNN-CBAM差分进化优化七参数",
    },
]


def run_command(args: list[str], timeout: int) -> dict[str, Any]:
    command = [sys.executable, str(ROOT / args[0]), *args[1:]]
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    completed = subprocess.run(
        command,
        cwd=ROOT.parent,
        env=env,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
        encoding="utf-8",
        errors="replace",
    )
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout_tail": completed.stdout[-1200:],
        "stderr_tail": completed.stderr[-1200:],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="运行七参数流程轻量冒烟测试")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "audit_results")
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args()

    output_dir = ensure_dir(args.output_dir)
    results = []
    for item in TEST_COMMANDS:
        result = run_command(item["args"], args.timeout)
        output_text = f"{result['stdout_tail']}\n{result['stderr_tail']}"
        passed = result["returncode"] == 0 and item["expect_text"] in output_text
        results.append(
            {
                "name": item["name"],
                "args": item["args"],
                "expect_text": item["expect_text"],
                "passed": passed,
                **result,
            }
        )

    passed_count = sum(1 for item in results if item["passed"])
    summary = {
        "status": "pass" if passed_count == len(results) else "fail",
        "passed_count": passed_count,
        "total_count": len(results),
        "results": results,
    }
    write_json(output_dir / "smoke_test_results.json", summary)

    print(f"状态: {summary['status']}")
    print(f"通过: {passed_count}/{len(results)}")
    print(f"报告: {output_dir / 'smoke_test_results.json'}")
    if summary["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
