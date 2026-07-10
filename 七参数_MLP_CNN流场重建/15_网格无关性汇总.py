#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""汇总网格无关性证据。

当前仓库已有正式二维 CFD 复算和三维迁移验证结果，但没有发现
粗/中/细三档网格的完整复算指标。因此本脚本不会伪造网格无关性，
而是生成一份可复查报告：已有结果写入数值，缺少的粗/细网格复算
明确标记为“待补算”。
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "七参数_MLP_CNN流场重建" / "analysis_results" / "grid_independence"
CSV_PATH = OUT_DIR / "grid_independence_summary.csv"
MD_PATH = OUT_DIR / "grid_independence_summary.md"
TODO_PATH = OUT_DIR / "grid_independence_todo.md"
TEMPLATE_PATH = OUT_DIR / "grid_independence_input_template.csv"
TWO_D_REPORT = ROOT / "七参数_MLP_CNN流场重建" / "validation_results" / "mlp_cnn_de_multiloss_e10" / "final_validation_report.json"
THREE_D_CSV = ROOT / "comsol_3d_airfoil_radiator" / "generated_chip_airfoil_heat_sink" / "results" / "seven_param_3d_summary.csv"
GRID_COLUMNS = [
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


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_three_d_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def relative_error(medium: float, fine: float) -> float:
    return abs(fine - medium) / max(abs(fine), 1e-12) * 100.0


def to_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def read_input_rows(paths: list[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in paths:
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            rows.extend(dict(row) for row in csv.DictReader(f))
    return rows


def level_sort_key(level: str) -> tuple[int, int | str]:
    normalized = level.strip().lower()
    fixed = {"coarse": 0, "medium": 1, "fine": 2, "veryfine": 3, "finer": 4}
    if normalized in fixed:
        return (0, fixed[normalized])
    match = re.fullmatch(r"g(\d+)", normalized)
    if match:
        return (1, int(match.group(1)))
    return (2, normalized)


def choose_comparison_pair(
    by_level: dict[str, dict[str, Any]],
    comparison_level: str,
    reference_level: str,
) -> tuple[str, str, dict[str, Any], dict[str, Any]] | None:
    comparison = by_level.get(comparison_level)
    reference = by_level.get(reference_level)
    if comparison is not None and reference is not None:
        return comparison_level, reference_level, comparison, reference

    comparison = by_level.get("medium")
    reference = by_level.get("fine")
    if comparison is not None and reference is not None:
        return "medium", "fine", comparison, reference

    ordered_levels = sorted(by_level, key=level_sort_key)
    if len(ordered_levels) < 2:
        return None
    comparison_name, reference_name = ordered_levels[-2], ordered_levels[-1]
    return comparison_name, reference_name, by_level[comparison_name], by_level[reference_name]


def assess_grid_rows(
    rows: list[dict[str, Any]],
    comparison_level: str = "medium",
    reference_level: str = "fine",
) -> list[dict[str, Any]]:
    """对用户录入的网格结果做相邻细化误差判定。

    默认保持论文计划中的 medium/fine 判定；当继续补 veryfine 等更细网格时，
    可通过命令行改为 fine/veryfine，避免覆盖已有三档网格证据。
    """

    grouped: dict[tuple[str, str], dict[str, dict[str, Any]]] = {}
    for row in rows:
        key = (str(row.get("dimension", "")).strip(), str(row.get("case", "")).strip())
        level = str(row.get("mesh_level", "")).strip().lower()
        grouped.setdefault(key, {})[level] = row

    assessed: list[dict[str, Any]] = []
    for row in rows:
        copy = dict(row)
        copy.setdefault("status", "已录入，等待同工况 medium/fine 判定")
        assessed.append(copy)

    for (dimension, case), by_level in grouped.items():
        pair = choose_comparison_pair(by_level, comparison_level, reference_level)
        if pair is None:
            continue
        active_comparison, active_reference, comparison, reference = pair

        checks: list[tuple[str, float, float, float]] = []
        if dimension == "2D":
            nu_comparison, nu_reference = to_float(comparison.get("Nu")), to_float(reference.get("Nu"))
            f_comparison, f_reference = to_float(comparison.get("f")), to_float(reference.get("f"))
            if nu_comparison is not None and nu_reference is not None:
                checks.append(("Nu", relative_error(nu_comparison, nu_reference), 2.0, nu_reference))
            if f_comparison is not None and f_reference is not None:
                checks.append(("f", relative_error(f_comparison, f_reference), 3.0, f_reference))
        elif dimension == "3D":
            t_comparison, t_reference = to_float(comparison.get("Tmax")), to_float(reference.get("Tmax"))
            p_comparison, p_reference = to_float(comparison.get("pressure_drop")), to_float(reference.get("pressure_drop"))
            if t_comparison is not None and t_reference is not None:
                checks.append(("Tmax", relative_error(t_comparison, t_reference), 1.0, t_reference))
            if p_comparison is not None and p_reference is not None:
                checks.append(("pressure_drop", relative_error(p_comparison, p_reference), 5.0, p_reference))

        if not checks:
            continue
        passed = all(error <= threshold for _, error, threshold, _ in checks)
        detail = "; ".join(
            f"{name}{active_comparison}/{active_reference}误差={error:.3f}%<= {threshold:g}%"
            for name, error, threshold, _ in checks
        )
        status = f"通过：{detail}" if passed else f"未通过：{detail}"
        max_error = max(error for _, error, _, _ in checks)
        for item in assessed:
            if item.get("dimension") == dimension and item.get("case") == case and str(item.get("mesh_level", "")).lower() in {active_comparison, active_reference}:
                item["relative_to_fine_percent"] = f"{max_error:.6f}"
                item["status"] = status
    return assessed


def build_rows(
    input_csvs: list[Path] | None = None,
    comparison_level: str = "medium",
    reference_level: str = "fine",
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    input_rows = assess_grid_rows(read_input_rows(input_csvs or []), comparison_level, reference_level)
    input_cases = {(row.get("dimension"), row.get("case")) for row in input_rows}
    rows.extend(input_rows)
    report = read_json(TWO_D_REPORT)
    cfd = report.get("comsol_result", {})
    if cfd:
        rows.append({
            "dimension": "2D",
            "case": "DE_optimum",
            "mesh_level": "formal",
            "element_count": "",
            "Nu": cfd.get("Nu"),
            "f": cfd.get("f"),
            "eta": cfd.get("eta_cfd"),
            "Tmax": "",
            "Tavg": "",
            "pressure_drop": cfd.get("delta_p"),
            "thermal_resistance": "",
            "relative_to_fine_percent": "",
            "status": "已有正式网格复算；粗/中/细网格对照见上表" if ("2D", "DE_optimum") in input_cases else "已有正式网格复算；缺少粗/中/细网格对照",
        })
    else:
        rows.append({
            "dimension": "2D",
            "case": "DE_optimum",
            "mesh_level": "formal",
            "status": "缺失正式二维复算结果",
        })

    for item in read_three_d_rows(THREE_D_CSV):
        rows.append({
            "dimension": "3D",
            "case": item.get("case", ""),
            "mesh_level": "formal",
            "element_count": "",
            "Nu": item.get("nu_3d", ""),
            "f": item.get("f_3d", ""),
            "eta": item.get("eta_3d", ""),
            "Tmax": item.get("t_chip_max_k", ""),
            "Tavg": item.get("t_chip_avg_k", ""),
            "pressure_drop": item.get("delta_p_pa", ""),
            "thermal_resistance": item.get("r_th_k_per_w", ""),
            "relative_to_fine_percent": "",
            "status": "已有正式三维迁移结果；粗/中/细网格对照见上表" if ("3D", item.get("case", "")) in input_cases else "已有正式三维迁移结果；缺少粗/中/细网格对照",
        })

    if not input_rows:
        rows.extend([
            {
                "dimension": "2D",
                "case": "baseline_and_DE_optimum",
                "mesh_level": "coarse/medium/fine",
                "status": "待补算：需要同一工况三档网格 Nu/f/eta",
            },
            {
                "dimension": "3D",
                "case": "baseline_and_optimized",
                "mesh_level": "coarse/medium/fine",
                "status": "待补算：需要同一工况三档网格 Tmax/Tavg/压降/热阻",
            },
        ])
    return rows


def write_csv(rows: list[dict[str, Any]]) -> None:
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def write_md(rows: list[dict[str, Any]]) -> None:
    has_grid_rows = any(str(row.get("mesh_level", "")).lower() not in {"formal", ""} for row in rows)
    has_pending = any("待补算" in str(row.get("status", "")) or "缺少粗/中/细" in str(row.get("status", "")) for row in rows)
    has_failed = any(str(row.get("status", "")).startswith("未通过") for row in rows)
    if has_failed:
        summary = "当前已有真实网格细化结果，但相邻细化网格差异未满足阈值，因此不能作为网格无关性通过结论。"
    elif has_grid_rows and has_pending:
        summary = "当前已有部分粗/中/细真实网格结果，但仍存在未补齐工况，因此不能作为网格无关性通过结论。"
    elif has_grid_rows:
        summary = "当前已读取粗/中/细真实网格结果；是否可写成网格无关性验证完成，以表中状态为准。"
    else:
        summary = "当前尚未发现粗/中/细三档网格复算指标，因此不能作为网格无关性通过结论。"
    if has_pending:
        boundary = "当前只能写：本文已完成正式网格下的二维 CFD 复算和三维迁移验证；已补算的粗/中/细网格结果以表中状态为准，仍缺失的工况需要补充。不能把当前结果写成已完成网格无关性。"
    elif has_failed:
        boundary = "当前只能写：本文已完成二维和三维真实网格补算，但相邻细化网格误差未全部满足阈值，因此不能写成已完成网格无关性。正式性能结论仍以已有正式 CFD 复算和三维迁移验证为准。"
    else:
        boundary = "当前粗/中/细真实网格结果已全部满足阈值，可作为网格无关性验证证据写入论文。"

    lines = [
        "# 网格无关性证据汇总",
        "",
        f"本报告只汇总当前工作区中的真实结果。{summary}",
        "",
        "## 判定标准",
        "",
        "- 二维：中细网格 Nu 相对差异不超过 2%，f 相对差异不超过 3%。",
        "- 三维：中细网格 Tmax 相对差异不超过 1%，压降相对差异不超过 5%。",
        "",
        "## 当前证据",
        "",
        "| 维度 | 工况 | 网格 | Nu | f | eta | Tmax | Tavg | 压降 | 热阻 | 状态 |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            "| {dimension} | {case} | {mesh_level} | {Nu} | {f} | {eta} | {Tmax} | {Tavg} | {pressure_drop} | {thermal_resistance} | {status} |".format(
                dimension=row.get("dimension", ""),
                case=row.get("case", ""),
                mesh_level=row.get("mesh_level", ""),
                Nu=row.get("Nu", ""),
                f=row.get("f", ""),
                eta=row.get("eta", ""),
                Tmax=row.get("Tmax", ""),
                Tavg=row.get("Tavg", ""),
                pressure_drop=row.get("pressure_drop", ""),
                thermal_resistance=row.get("thermal_resistance", ""),
                status=row.get("status", ""),
            )
        )
    lines.extend([
        "",
        "## 论文写法边界",
        "",
        boundary,
        "",
        "## 后续补算表格格式",
        "",
        "补算后将粗、中、细三档结果追加到 `grid_independence_summary.csv`，并计算中细网格相对差异：",
        "",
        "```python",
        "relative_error = abs(value_reference - value_comparison) / max(abs(value_reference), 1e-12) * 100",
        "```",
        "",
    ])
    MD_PATH.write_text("\n".join(lines), encoding="utf-8")


def write_todo() -> None:
    lines = [
        "# 网格无关性补算任务书",
        "",
        "本任务书用于补齐论文中尚未完成的粗/中/细三档网格无关性验证。所有数值必须来自真实 COMSOL 求解，不得手工编造。",
        "",
        "## 二维 CFD 补算",
        "",
        "目标工况：baseline 与 DE_optimum。每个工况至少计算 coarse、medium、fine 三档网格。",
        "",
        "| 工况 | 网格档位 | 建议网格设置 | 必须导出指标 |",
        "|---|---|---|---|",
        "| baseline | coarse | 当前正式网格更粗一档 | Nu、f、eta、delta_p、单元数 |",
        "| baseline | medium | 当前正式网格或论文采用网格 | Nu、f、eta、delta_p、单元数 |",
        "| baseline | fine | 当前正式网格更细一档 | Nu、f、eta、delta_p、单元数 |",
        "| DE_optimum | coarse | 当前正式网格更粗一档 | Nu、f、eta、delta_p、单元数 |",
        "| DE_optimum | medium | 当前正式网格或论文采用网格 | Nu、f、eta、delta_p、单元数 |",
        "| DE_optimum | fine | 当前正式网格更细一档 | Nu、f、eta、delta_p、单元数 |",
        "",
        "推荐使用已封装的二维网格无关性运行器。默认 dry-run，只检查命令链；显式传入 `--run` 才会启动 COMSOL 求解：",
        "",
        "```powershell",
        "python \"七参数_MLP_CNN流场重建\\17_二维网格无关性运行器.py\"",
        "python \"七参数_MLP_CNN流场重建\\17_二维网格无关性运行器.py\" --run",
        "python \"七参数_MLP_CNN流场重建\\15_网格无关性汇总.py\" --input-csv \"七参数_MLP_CNN流场重建\\analysis_results\\grid_independence\\grid_independence_2d_real_results.csv\"",
        "```",
        "",
        "二维验收阈值：",
        "",
        "```text",
        "abs(Nu_fine - Nu_medium) / abs(Nu_fine) <= 2%",
        "abs(f_fine - f_medium) / abs(f_fine) <= 3%",
        "```",
        "",
        "## 三维迁移模型补算",
        "",
        "目标工况：baseline 与 chip_mlp_cnn_de_multiloss_e10。每个工况至少计算 coarse、medium、fine 三档网格。",
        "",
        "| 工况 | 网格档位 | 可参考脚本参数 | 必须导出指标 |",
        "|---|---|---|---|",
        "| baseline | coarse | `--mesh-hauto` 较粗设置 | Tmax、Tavg、delta_p、r_th、eta3D、单元数 |",
        "| baseline | medium | 当前正式设置 | Tmax、Tavg、delta_p、r_th、eta3D、单元数 |",
        "| baseline | fine | 更细设置 | Tmax、Tavg、delta_p、r_th、eta3D、单元数 |",
        "| optimized | coarse | `--mesh-hauto` 较粗设置 | Tmax、Tavg、delta_p、r_th、eta3D、单元数 |",
        "| optimized | medium | 当前正式设置 | Tmax、Tavg、delta_p、r_th、eta3D、单元数 |",
        "| optimized | fine | 更细设置 | Tmax、Tavg、delta_p、r_th、eta3D、单元数 |",
        "",
        "推荐使用已封装的三维网格无关性运行器。默认 dry-run，只检查命令链；显式传入 `--run` 才会启动 COMSOL 求解：",
        "",
        "```text",
        "python \"comsol_3d_airfoil_radiator\\20_三维网格无关性运行器.py\"",
        "python \"comsol_3d_airfoil_radiator\\20_三维网格无关性运行器.py\" --run --skip-existing",
        "python \"七参数_MLP_CNN流场重建\\15_网格无关性汇总.py\" --input-csv \"七参数_MLP_CNN流场重建\\analysis_results\\grid_independence\\grid_independence_3d_real_results.csv\"",
        "```",
        "",
        "运行器内部复用以下三维建模和后处理脚本：",
        "",
        "```text",
        "comsol_3d_airfoil_radiator/18_芯片级翼型鳍片散热器建模.py",
        "comsol_3d_airfoil_radiator/15_提取七参数三维指标.py",
        "comsol_3d_airfoil_radiator/build_airfoil_pillar_heat_sink.py",
        "comsol_3d_airfoil_radiator/build_realistic_airfoil_heat_sink.py",
        "comsol_3d_airfoil_radiator/05_结果后处理.py",
        "```",
        "",
        "三维验收阈值：",
        "",
        "```text",
        "abs(Tmax_fine - Tmax_medium) / abs(Tmax_fine) <= 1%",
        "abs(delta_p_fine - delta_p_medium) / abs(delta_p_fine) <= 5%",
        "```",
        "",
        "## 补算后写入格式",
        "",
        "将真实结果追加到：",
        "",
        "```text",
        "七参数_MLP_CNN流场重建/analysis_results/grid_independence/grid_independence_input_template.csv",
        "```",
        "",
        "字段至少包括：",
        "",
        "```text",
        "dimension,case,mesh_level,element_count,Nu,f,eta,Tmax,Tavg,pressure_drop,thermal_resistance,relative_to_fine_percent,status",
        "```",
        "",
        "补算完成后重新运行：",
        "",
        "```powershell",
        "python \"七参数_MLP_CNN流场重建\\15_网格无关性汇总.py\" --input-csv \"七参数_MLP_CNN流场重建\\analysis_results\\grid_independence\\grid_independence_2d_real_results.csv\" --input-csv \"七参数_MLP_CNN流场重建\\analysis_results\\grid_independence\\grid_independence_3d_real_results.csv\"",
        "python \"七参数_MLP_CNN流场重建\\16_论文证据链汇总.py\"",
        "```",
        "",
    ]
    TODO_PATH.write_text("\n".join(lines), encoding="utf-8")


def write_template() -> None:
    rows = []
    for dimension, cases in {
        "2D": ["baseline", "DE_optimum"],
        "3D": ["baseline", "chip_mlp_cnn_de_multiloss_e10"],
    }.items():
        for case in cases:
            for level in ["coarse", "medium", "fine"]:
                rows.append({
                    "dimension": dimension,
                    "case": case,
                    "mesh_level": level,
                    "element_count": "",
                    "Nu": "",
                    "f": "",
                    "eta": "",
                    "Tmax": "",
                    "Tavg": "",
                    "pressure_drop": "",
                    "thermal_resistance": "",
                    "relative_to_fine_percent": "",
                    "status": "待填入真实 COMSOL 求解结果",
                })
    with TEMPLATE_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=GRID_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="汇总并判定网格无关性结果")
    parser.add_argument(
        "--input-csv",
        action="append",
        default=[],
        help="粗/中/细三档网格真实补算结果 CSV；可重复传入二维和三维结果。",
    )
    parser.add_argument("--comparison-level", default="medium", help="用于误差判定的较粗参考档，默认 medium。")
    parser.add_argument("--reference-level", default="fine", help="用于误差判定的较细参考档，默认 fine。")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    input_csvs = [Path(item) for item in args.input_csv if item]
    rows = build_rows(input_csvs, args.comparison_level.strip().lower(), args.reference_level.strip().lower())
    write_csv(rows)
    write_md(rows)
    write_todo()
    if not input_csvs:
        write_template()
    print(MD_PATH)


if __name__ == "__main__":
    main()
