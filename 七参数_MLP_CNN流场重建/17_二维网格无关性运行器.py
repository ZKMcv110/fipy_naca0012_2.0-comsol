#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""二维七参数翼型柱阵列网格无关性运行器。

默认只 dry-run，不调用 COMSOL。显式传入 ``--run`` 后，脚本会直接调用
旧七参数单工况 COMSOL 求解脚本，并为 baseline 与 DE_optimum 两个工况
分别计算 coarse/medium/fine 三档网格。
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
SINGLE_SCRIPT = PROJECT_ROOT / "七参数_几何掩码代理优化" / "02a_七参数COMSOL单工况求解.py"
BEST_JSON = ROOT / "optimization_results" / "mlp_cnn_de_multiloss_e10" / "best_params.json"
OUT_ROOT = ROOT / "analysis_results" / "grid_independence" / "two_d_runs"
GRID_INPUT_CSV = ROOT / "analysis_results" / "grid_independence" / "grid_independence_2d_real_results.csv"
RESULT_RE = re.compile(r"CFD_RESULT_DATA:\s*(.*)")
PARAM_NAMES = ("Ta", "Twa", "Tb", "Ts", "Tt", "Tad", "theta")
BASELINE_PARAMS = {
    "Ta": 0.0,
    "Twa": 0.40,
    "Tb": 0.12,
    "Ts": 1.10,
    "Tt": 0.85,
    "Tad": 0.0,
    "theta": 0.0,
}


@dataclass(frozen=True)
class MeshLevel:
    name: str
    hauto: int
    air_hmax: str = ""
    air_hmin: str = ""
    solid_hmax: str = ""
    solid_hmin: str = ""
    wall_bl_layers: int = 0
    wall_bl_hminfact: float = 3.0


@dataclass(frozen=True)
class CaseSpec:
    case: str
    level: MeshLevel
    params: dict[str, float]
    outdir: Path
    command: list[str]


def parse_levels(raw: str) -> tuple[MeshLevel, ...]:
    levels: list[MeshLevel] = []
    for item in raw.split(","):
        if not item.strip():
            continue
        parts = item.split(":")
        if len(parts) not in {2, 6}:
            raise ValueError("--levels 格式为 name:hauto 或 name:hauto:air_hmax:air_hmin:solid_hmax:solid_hmin")
        if len(parts) == 2:
            name, value = parts
            levels.append(MeshLevel(name.strip(), int(value)))
        else:
            name, value, air_hmax, air_hmin, solid_hmax, solid_hmin = parts
            levels.append(MeshLevel(name.strip(), int(value), air_hmax, air_hmin, solid_hmax, solid_hmin))
    if not levels:
        raise ValueError("--levels 至少需要一档网格")
    return tuple(levels)


def load_best_params() -> dict[str, float]:
    data = json.loads(BEST_JSON.read_text(encoding="utf-8"))
    raw = data["best_params"]
    return {name: float(raw[name]) for name in PARAM_NAMES}


def parse_levels_v2(raw: str) -> tuple[MeshLevel, ...]:
    """解析网格档位。

    支持：
    - name:hauto
    - name:hauto:air_hmax:air_hmin:solid_hmax:solid_hmin
    - name:hauto:air_hmax:air_hmin:solid_hmax:solid_hmin:wall_bl_layers:wall_bl_hminfact
    """
    levels: list[MeshLevel] = []
    for item in raw.split(","):
        if not item.strip():
            continue
        parts = item.split(":")
        if len(parts) == 2:
            name, value = parts
            levels.append(MeshLevel(name.strip(), int(value)))
        elif len(parts) == 6:
            name, value, air_hmax, air_hmin, solid_hmax, solid_hmin = parts
            levels.append(MeshLevel(name.strip(), int(value), air_hmax, air_hmin, solid_hmax, solid_hmin))
        elif len(parts) == 8:
            name, value, air_hmax, air_hmin, solid_hmax, solid_hmin, wall_bl_layers, wall_bl_hminfact = parts
            levels.append(
                MeshLevel(
                    name.strip(),
                    int(value),
                    air_hmax,
                    air_hmin,
                    solid_hmax,
                    solid_hmin,
                    int(wall_bl_layers),
                    float(wall_bl_hminfact),
                )
            )
        else:
            raise ValueError(
                "--levels 格式错误，应为 name:hauto、"
                "name:hauto:air_hmax:air_hmin:solid_hmax:solid_hmin 或 "
                "name:hauto:air_hmax:air_hmin:solid_hmax:solid_hmin:wall_bl_layers:wall_bl_hminfact"
            )
    if not levels:
        raise ValueError("--levels 至少需要一档网格")
    return tuple(levels)


def build_command(
    params: dict[str, float],
    outdir: Path,
    level: MeshLevel,
    *,
    wall_bl_explicit: bool = False,
) -> list[str]:
    command = [sys.executable, str(SINGLE_SCRIPT)]
    for name in PARAM_NAMES:
        command.extend([f"--{name}", f"{params[name]:.12g}"])
    command.extend(["--mesh_hauto", str(level.hauto), "--outdir", str(outdir)])
    for key in ("air_hmax", "air_hmin", "solid_hmax", "solid_hmin"):
        value = getattr(level, key)
        if value:
            command.extend([f"--{key}", value])
    if level.wall_bl_layers > 0:
        command.extend(["--wall_bl_layers", str(level.wall_bl_layers)])
        command.extend(["--wall_bl_hminfact", f"{level.wall_bl_hminfact:g}"])
        command.append("--wall_bl_required")
        if wall_bl_explicit:
            command.append("--wall_bl_explicit")
    return command


def build_specs(
    levels: tuple[MeshLevel, ...],
    selected_cases: set[str] | None = None,
    *,
    wall_bl_explicit: bool = False,
) -> list[CaseSpec]:
    optimized = load_best_params()
    specs: list[CaseSpec] = []
    for level in levels:
        for case, params in [("baseline", BASELINE_PARAMS), ("DE_optimum", optimized)]:
            if selected_cases and case not in selected_cases:
                continue
            outdir = OUT_ROOT / case / level.name / "cfd_solution"
            specs.append(
                CaseSpec(
                    case=case,
                    level=level,
                    params=params,
                    outdir=outdir,
                    command=build_command(params, outdir, level, wall_bl_explicit=wall_bl_explicit),
                )
            )
    return specs


def parse_stdout(stdout: str) -> dict[str, float]:
    match = RESULT_RE.search(stdout)
    if not match:
        raise ValueError("未在 stdout 中找到 CFD_RESULT_DATA")
    result: dict[str, float] = {}
    for part in match.group(1).split(","):
        if "=" not in part:
            continue
        key, value = part.strip().split("=", 1)
        result[key] = float(value)
    return result


def run_case(spec: CaseSpec, timeout: int) -> dict[str, str]:
    spec.outdir.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        spec.command,
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    log_path = spec.outdir.parent / "stdout.log"
    log_path.write_text((completed.stdout or "") + "\n" + (completed.stderr or ""), encoding="utf-8")
    if completed.returncode != 0:
        raise RuntimeError(f"{spec.case}/{spec.level.name} 求解失败，详见 {log_path}")
    parsed = parse_stdout(completed.stdout)
    row = {
        "dimension": "2D",
        "case": spec.case,
        "mesh_level": spec.level.name,
        "element_count": str(int(parsed.get("mesh", -1))),
        "Nu": f"{parsed.get('Nu', float('nan')):.9g}",
        "f": f"{parsed.get('f', float('nan')):.9g}",
        "eta": "",
        "Tmax": "",
        "Tavg": f"{parsed.get('T_wing', float('nan')):.9g}",
        "pressure_drop": f"{abs(parsed.get('p_in', 0.0) - parsed.get('p_out', 0.0)):.9g}",
        "thermal_resistance": "",
        "relative_to_fine_percent": "",
        "status": f"真实 COMSOL 求解；mesh_hauto={spec.level.hauto}; local_size={bool(spec.level.air_hmax or spec.level.solid_hmax)}",
    }
    (spec.outdir.parent / "grid_result.json").write_text(
        json.dumps({"case": spec.case, "level": spec.level.name, "params": spec.params, "parsed": parsed, "row": row}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return row


def load_existing_case(spec: CaseSpec) -> dict[str, str] | None:
    result_path = spec.outdir.parent / "grid_result.json"
    if not result_path.exists():
        return None
    data = json.loads(result_path.read_text(encoding="utf-8"))
    row = data.get("row")
    if not isinstance(row, dict):
        return None
    return {key: str(value) for key, value in row.items()}


def fill_eta(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    baseline_by_level = {
        row["mesh_level"]: row
        for row in rows
        if row["case"] == "baseline"
    }
    filled: list[dict[str, str]] = []
    for row in rows:
        copy = dict(row)
        if copy["case"] == "baseline":
            copy["eta"] = "1"
        else:
            baseline = baseline_by_level.get(copy["mesh_level"])
            if baseline:
                nu = float(copy["Nu"])
                f_value = float(copy["f"])
                nu0 = float(baseline["Nu"])
                f0 = float(baseline["f"])
                eta = (nu / max(nu0, 1e-12)) / ((max(f_value, 1e-12) / max(f0, 1e-12)) ** (1.0 / 3.0))
                copy["eta"] = f"{eta:.9g}"
        filled.append(copy)
    return filled


def write_rows(rows: list[dict[str, str]]) -> None:
    GRID_INPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "dimension",
        "case",
        "mesh_level",
        "element_count",
        "Nu",
        "f",
        "eta",
        "Tmax",
        "Tavg",
        "pressure_drop",
        "thermal_resistance",
        "relative_to_fine_percent",
        "status",
    ]
    with GRID_INPUT_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    GRID_INPUT_CSV.with_suffix(".json").write_text(
        json.dumps({"source": __file__, "output": str(GRID_INPUT_CSV)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="按粗/中/细三档网格运行二维 COMSOL 网格无关性验证。")
    parser.add_argument("--levels", default="coarse:5,medium:4,fine:3", help="格式：coarse:5 或 coarse:5:3[mm]:0.3[mm]:0.8[mm]:0.08[mm]；hauto 越大越粗。")
    parser.add_argument("--run", action="store_true", help="真正启动 COMSOL 求解。默认只 dry-run。")
    parser.add_argument("--skip-existing", action="store_true", help="已有 grid_result.json 时复用结果，只补缺失网格。")
    parser.add_argument("--cases", default="baseline,DE_optimum", help="逗号分隔的工况列表，默认 baseline,DE_optimum")
    parser.add_argument(
        "--wall-bl-explicit",
        "--wall_bl_explicit",
        action="store_true",
        help="边界层网格使用单工况脚本中的显式翼型壁面边界选择。",
    )
    parser.add_argument("--timeout", type=int, default=1200)
    args = parser.parse_args()

    selected_cases = {item.strip() for item in args.cases.split(",") if item.strip()}
    specs = build_specs(parse_levels_v2(args.levels), selected_cases, wall_bl_explicit=args.wall_bl_explicit)
    print("[INFO] 二维网格无关性计划：")
    for spec in specs:
        done = (spec.outdir.parent / "grid_result.json").exists()
        print(f"- {spec.case}/{spec.level.name}: hauto={spec.level.hauto}, done={done}")
        print("  " + " ".join(f'"{part}"' if " " in part else part for part in spec.command))

    if not args.run:
        print("[INFO] dry-run 完成；传入 --run 才会启动 COMSOL 求解。")
        return

    raw_rows: list[dict[str, str]] = []
    for spec in specs:
        existing = load_existing_case(spec) if args.skip_existing else None
        if existing is not None:
            print(f"[INFO] 复用已有二维结果: {spec.case}/{spec.level.name}")
            raw_rows.append(existing)
            continue
        raw_rows.append(run_case(spec, args.timeout))
    rows = fill_eta(raw_rows)
    write_rows(rows)
    print(f"[INFO] 已生成二维网格无关性输入: {GRID_INPUT_CSV}")
    print(f'python "七参数_MLP_CNN流场重建\\15_网格无关性汇总.py" --input-csv "{GRID_INPUT_CSV}"')


if __name__ == "__main__":
    main()
