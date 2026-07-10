#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""七参数COMSOL批量求解调度脚本。

本脚本不修改旧的 `comsol单次执行脚本.py`，默认调用本目录下复制改造后的
`02a_七参数COMSOL单工况求解.py`。该单工况脚本在翼型坐标生成后加入
theta整体旋转，并继续输出 CFD_RESULT_DATA。
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd

from common import PARAM_COLS, PROJECT_ROOT, ROOT, ensure_dir, write_json


RESULT_RE = re.compile(r"CFD_RESULT_DATA:\s*(.*)")
REQUIRED_IMAGE_NAMES = ["velocity_magnitude.png", "pressure.png", "temperature.png"]
MIN_IMAGE_BYTES = 20_000


def parse_stdout(stdout: str) -> dict:
    match = RESULT_RE.search(stdout)
    if not match:
        raise ValueError("未在stdout中找到 CFD_RESULT_DATA")
    result = {}
    for part in match.group(1).split(","):
        if "=" not in part:
            continue
        key, value = part.strip().split("=", 1)
        try:
            result[key] = float(value)
        except ValueError:
            result[key] = value
    if "Nu" not in result or "f" not in result:
        raise ValueError(f"CFD_RESULT_DATA 缺少 Nu 或 f: {result}")
    return result


def run_case(row: pd.Series, args) -> dict:
    case_id = int(row["case_id"])
    case_dir = ensure_dir(Path(args.output_dir) / f"case_{case_id}")
    result_path = case_dir / "result.json"
    if result_path.exists() and not args.force:
        return json.loads(result_path.read_text(encoding="utf-8"))

    params = {name: float(row[name]) for name in PARAM_COLS}
    base = {"case_id": case_id, **params, "image_complete": False, "failure_reason": ""}

    if abs(params["theta"]) > 1e-12 and args.single_script_ignores_theta and not args.allow_ignore_theta:
        base["failure_reason"] = "当前单工况COMSOL脚本未实现theta倾斜角；未求解，避免生成错误标签。"
        write_json(result_path, base)
        return base

    single_script = Path(args.single_script)
    if not single_script.exists():
        base["failure_reason"] = f"单工况脚本不存在: {single_script}"
        write_json(result_path, base)
        return base

    cfd_outdir = ensure_dir(case_dir / "cfd_solution")
    cmd = [
        sys.executable,
        str(single_script),
        "--Ta", str(params["Ta"]),
        "--Twa", str(params["Twa"]),
        "--Tb", str(params["Tb"]),
        "--Ts", str(params["Ts"]),
        "--Tt", str(params["Tt"]),
        "--Tad", str(params["Tad"]),
        "--outdir", str(cfd_outdir),
    ]
    if args.pass_theta:
        cmd.extend(["--theta", str(params["theta"])])
    if args.q_heat:
        cmd.extend(["--Q_heat", str(args.q_heat)])

    try:
        completed = subprocess.run(cmd, capture_output=True, text=True, timeout=args.timeout, encoding="utf-8", errors="replace")
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr or completed.stdout)
        parsed = parse_stdout(completed.stdout)
        image_status = check_cfd_images(cfd_outdir)
        result = {
            **base,
            "Nu": parsed.get("Nu"),
            "f": parsed.get("f"),
            "delta_p": abs(float(parsed.get("p_in", 0.0)) - float(parsed.get("p_out", 0.0))),
            "delta_T": float(parsed.get("delta_T", float(parsed.get("T_wing", 0.0)) - float(parsed.get("T_in", 0.0)))),
            "Q_total": parsed.get("Q_total"),
            "image_complete": image_status["complete"],
            "image_status": image_status,
            "failure_reason": "",
            "cfd_outdir": str(cfd_outdir),
        }
    except Exception as exc:
        result = {**base, "failure_reason": str(exc)}

    write_json(result_path, result)
    return result


def check_cfd_images(cfd_outdir: Path) -> dict:
    """检查云图是否存在且不是明显空文件。"""
    files = {}
    missing_or_small = []
    for name in REQUIRED_IMAGE_NAMES:
        path = cfd_outdir / name
        size_bytes = path.stat().st_size if path.exists() else 0
        valid = path.exists() and size_bytes >= MIN_IMAGE_BYTES
        files[name] = {"exists": path.exists(), "size_bytes": size_bytes, "valid": valid}
        if not valid:
            missing_or_small.append(name)
    return {"complete": not missing_or_small, "min_image_bytes": MIN_IMAGE_BYTES, "files": files, "invalid": missing_or_small}


def main() -> None:
    parser = argparse.ArgumentParser(description="七参数COMSOL批量求解调度器")
    parser.add_argument("--samples", default=str(ROOT / "samples" / "samples_7param.csv"))
    parser.add_argument("--output-dir", default=str(ROOT / "comsol_results"))
    parser.add_argument("--single-script", default=str(ROOT / "02a_七参数COMSOL单工况求解.py"))
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--q-heat", type=float, default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--pass-theta", action=argparse.BooleanOptionalAction, default=True, help="调用单工况脚本时是否传入 --theta。")
    parser.add_argument("--single-script-ignores-theta", action="store_true", help="当手动指定旧六参数脚本时启用，防止theta非零样本被错误求解。")
    parser.add_argument("--allow-ignore-theta", action="store_true", help="允许theta非零时仍调用旧六参数脚本；仅调试用，不建议生成论文标签。")
    parser.add_argument("--start-index", type=int, default=0, help="从样本表的第几行开始调度，0表示从第一行开始。")
    parser.add_argument("--limit", type=int, default=0, help="最多调度多少行，0表示调度从start-index开始的全部样本。")
    parser.add_argument("--dry-run", action="store_true", help="只检查样本并生成调度计划，不调用COMSOL、不写result.json。")
    args = parser.parse_args()

    df = pd.read_csv(args.samples)
    ensure_dir(Path(args.output_dir))
    missing_cols = [name for name in ["case_id"] + PARAM_COLS if name not in df.columns]
    if missing_cols:
        raise ValueError(f"样本表缺少列: {missing_cols}")
    if args.start_index < 0:
        raise ValueError("--start-index 不能小于0")
    if args.limit < 0:
        raise ValueError("--limit 不能小于0")

    sliced_df = df.iloc[args.start_index :]
    limit_df = sliced_df.head(args.limit) if args.limit else sliced_df

    if args.dry_run:
        plan_rows = []
        for _, row in limit_df.iterrows():
            case_id = int(row["case_id"])
            params = {name: float(row[name]) for name in PARAM_COLS}
            plan_rows.append(
                {
                    "case_id": case_id,
                    **params,
                    "case_dir": str(Path(args.output_dir) / f"case_{case_id}"),
                    "will_pass_theta": bool(args.pass_theta),
                    "single_script": str(Path(args.single_script)),
                }
            )
        plan = pd.DataFrame(plan_rows)
        plan_path = Path(args.output_dir) / "dry_run_plan.csv"
        plan.to_csv(plan_path, index=False, encoding="utf-8-sig")
        print(f"[DRY-RUN] 未调用COMSOL，仅生成计划: {plan_path}")
        print(f"[DRY-RUN] 计划样本数: {len(plan)}")
        if len(plan):
            print(f"[DRY-RUN] theta范围: {plan['theta'].min():.4f} 到 {plan['theta'].max():.4f} deg")
        return

    rows = [run_case(row, args) for _, row in limit_df.iterrows()]
    summary = pd.DataFrame(rows)
    summary.to_csv(Path(args.output_dir) / "summary.csv", index=False, encoding="utf-8-sig")
    print(f"[OK] 批量调度完成: {Path(args.output_dir) / 'summary.csv'}")
    print(f"[OK] 成功数: {(summary.get('failure_reason', '') == '').sum()} / {len(summary)}")


if __name__ == "__main__":
    main()
