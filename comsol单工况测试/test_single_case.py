#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Run one fixed COMSOL case for debugging the single-case pipeline."""

from pathlib import Path
import subprocess
import sys


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
COMSOL_SINGLE_SCRIPT = PROJECT_ROOT / "comsol单次执行脚本.py"
OUTPUT_DIR = HERE / "test_case_debug"


def test_single_case() -> None:
    print("=" * 60)
    print("Test one COMSOL case")
    print("=" * 60)

    if not COMSOL_SINGLE_SCRIPT.exists():
        raise FileNotFoundError(f"Missing COMSOL single-case script: {COMSOL_SINGLE_SCRIPT}")

    cmd = [
        sys.executable,
        str(COMSOL_SINGLE_SCRIPT),
        "--Ta", "0.025",
        "--Twa", "0.40",
        "--Tb", "0.115",
        "--Tt", "0.85",
        "--Ts", "1.00",
        "--Tad", "0.50",
        "--outdir", str(OUTPUT_DIR),
    ]

    print("\nCommand:")
    print(" ".join(cmd))
    print("\n" + "-" * 60)

    try:
        result = subprocess.run(
            cmd,
            capture_output=False,
            text=True,
            timeout=600,
            cwd=PROJECT_ROOT,
        )

        print("\n" + "=" * 60)
        if result.returncode == 0:
            print(f"Test succeeded. Output directory: {OUTPUT_DIR}")
        else:
            print(f"Test failed. Return code: {result.returncode}")
        print("=" * 60)

    except subprocess.TimeoutExpired:
        print("\nCalculation timed out (>600s)")
    except Exception as exc:
        print(f"\nExecution error: {exc}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_single_case()
