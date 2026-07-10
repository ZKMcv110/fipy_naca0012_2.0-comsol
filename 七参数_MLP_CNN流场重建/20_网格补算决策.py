#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""根据真实网格补算结果生成下一步决策。

该脚本不运行 COMSOL，也不修改原始结果。它的作用是把当前 G3/G4/G5
和三维 coarse/medium/fine 的误差转成明确判断：是否还值得继续全域/域级加密，
还是必须切换到壁面边界层、尾迹局部区域和后处理截面一致性检查。
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "七参数_MLP_CNN流场重建"
GRID_DIR = PROJECT / "analysis_results" / "grid_independence"
SUMMARY_CSV = GRID_DIR / "grid_independence_summary.csv"
OUT_MD = GRID_DIR / "grid_independence_next_action.md"
OUT_JSON = GRID_DIR / "grid_independence_next_action.json"


@dataclass(frozen=True)
class Rule:
    metric: str
    threshold: float


RULES = {
    "2D": [Rule("Nu", 2.0), Rule("f", 3.0)],
    "3D": [Rule("Tmax", 1.0), Rule("pressure_drop", 5.0)],
}


LEVEL_ORDER = {
    "coarse": 0,
    "medium": 1,
    "fine": 2,
    "finer": 3,
    "g1": 10,
    "g2": 11,
    "g3": 12,
    "g4": 13,
    "g5": 14,
}


def read_rows() -> list[dict[str, str]]:
    if not SUMMARY_CSV.exists():
        return []
    with SUMMARY_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def to_float(value: Any) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def relative_error(coarser: float, finer: float) -> float:
    return abs(finer - coarser) / max(abs(finer), 1e-12) * 100.0


def level_key(row: dict[str, str]) -> int:
    return LEVEL_ORDER.get(row.get("mesh_level", "").strip().lower(), 999)


def metric_trend(values: list[float]) -> str:
    if len(values) < 2:
        return "数据不足"
    increases = all(b >= a for a, b in zip(values, values[1:]))
    decreases = all(b <= a for a, b in zip(values, values[1:]))
    if increases and not decreases:
        return "随网格细化单调增大"
    if decreases and not increases:
        return "随网格细化单调减小"
    return "随网格细化非单调"


def analyze_case(dimension: str, case: str, rows: list[dict[str, str]]) -> dict[str, Any]:
    ordered = sorted(
        [
            row
            for row in rows
            if row.get("dimension") == dimension
            and row.get("case") == case
            and row.get("mesh_level", "").strip().lower() in LEVEL_ORDER
        ],
        key=level_key,
    )
    metrics: list[dict[str, Any]] = []
    for rule in RULES.get(dimension, []):
        series = [
            {
                "level": row.get("mesh_level", ""),
                "value": to_float(row.get(rule.metric)),
            }
            for row in ordered
            if to_float(row.get(rule.metric)) is not None
        ]
        if len(series) < 2:
            metrics.append({"metric": rule.metric, "status": "missing"})
            continue
        left, right = series[-2], series[-1]
        error = relative_error(float(left["value"]), float(right["value"]))
        metrics.append(
            {
                "metric": rule.metric,
                "threshold_percent": rule.threshold,
                "last_pair": f"{left['level']}/{right['level']}",
                "last_error_percent": error,
                "passed": error <= rule.threshold,
                "trend": metric_trend([float(item["value"]) for item in series]),
                "series": series,
            }
        )
    return {"dimension": dimension, "case": case, "levels": [row.get("mesh_level", "") for row in ordered], "metrics": metrics}


def build_decision(cases: list[dict[str, Any]]) -> dict[str, Any]:
    two_d_cases = [case for case in cases if case["dimension"] == "2D"]
    three_d_cases = [case for case in cases if case["dimension"] == "3D"]
    two_d_failed = any(
        metric.get("passed") is False
        for case in two_d_cases
        for metric in case["metrics"]
    )
    two_d_monotonic = all(
        "单调" in str(metric.get("trend", ""))
        for case in two_d_cases
        for metric in case["metrics"]
        if metric.get("status") != "missing"
    )
    three_d_pressure_failed = any(
        metric.get("metric") == "pressure_drop" and metric.get("passed") is False
        for case in three_d_cases
        for metric in case["metrics"]
    )
    three_d_tmax_passed = all(
        metric.get("passed") is True
        for case in three_d_cases
        for metric in case["metrics"]
        if metric.get("metric") == "Tmax"
    )

    actions = []
    if two_d_failed and two_d_monotonic:
        actions.append("停止继续单纯降低 air_hmax/solid_hmax；二维下一步必须建立翼型壁面边界层网格和尾迹局部细化区。")
    elif two_d_failed:
        actions.append("二维结果未通过，但趋势不是稳定单调；先复查后处理边界和求解残差，再决定是否补算。")
    else:
        actions.append("二维 Nu/f 已满足当前阈值，可作为网格无关性证据写入论文。")

    if three_d_pressure_failed and three_d_tmax_passed:
        actions.append("三维温度指标可作为稳定证据，压降不能写成网格无关；下一步应固定入口/出口截面并输出 p_in_avg、p_out_avg、delta_p。")
    elif three_d_pressure_failed:
        actions.append("三维温度和压降均需继续补算或修正后处理。")
    else:
        actions.append("三维 Tmax 和 pressure_drop 均满足当前阈值，可作为三维网格证据。")

    can_complete_grid = not two_d_failed and not three_d_pressure_failed
    return {
        "can_complete_grid_independence": can_complete_grid,
        "two_d_failed": two_d_failed,
        "three_d_pressure_failed": three_d_pressure_failed,
        "actions": actions,
    }


def write_report(cases: list[dict[str, Any]], decision: dict[str, Any]) -> None:
    lines = [
        "# 网格补算下一步决策",
        "",
        "本报告由 `七参数_MLP_CNN流场重建/20_网格补算决策.py` 生成，只基于当前真实网格结果，不运行 COMSOL。",
        "",
        f"- 是否可宣称网格无关性完成：{'是' if decision['can_complete_grid_independence'] else '否'}",
        "",
        "## 自动判断",
        "",
    ]
    lines.extend(f"- {item}" for item in decision["actions"])
    lines.extend(["", "## 当前末端误差", ""])
    for case in cases:
        lines.append(f"### {case['dimension']} - {case['case']}")
        lines.append("")
        lines.append("| 指标 | 末端档位 | 末端误差 | 阈值 | 是否通过 | 趋势 |")
        lines.append("|---|---|---:|---:|---|---|")
        for metric in case["metrics"]:
            if metric.get("status") == "missing":
                lines.append(f"| {metric['metric']} | - | - | - | 否 | 数据不足 |")
                continue
            lines.append(
                "| {metric} | {pair} | {error:.3f}% | {threshold:.3g}% | {passed} | {trend} |".format(
                    metric=metric["metric"],
                    pair=metric["last_pair"],
                    error=metric["last_error_percent"],
                    threshold=metric["threshold_percent"],
                    passed="是" if metric["passed"] else "否",
                    trend=metric["trend"],
                )
            )
        lines.append("")
    lines.extend(
        [
            "## 论文写法",
            "",
            "当前只能写：已完成二维和三维真实网格补算，但二维 Nu/f 与三维压降仍未满足严格阈值；二维结果显示单纯域级加密不足以稳定 Nu/f，后续需要壁面边界层网格、尾迹局部细化和固定后处理截面。",
            "",
        ]
    )
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    rows = read_rows()
    case_keys = sorted(
        {
            (row.get("dimension", ""), row.get("case", ""))
            for row in rows
            if row.get("mesh_level", "").strip().lower() in LEVEL_ORDER
        }
    )
    cases = [analyze_case(dimension, case, rows) for dimension, case in case_keys]
    decision = build_decision(cases)
    OUT_JSON.write_text(json.dumps({"cases": cases, "decision": decision}, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(cases, decision)
    print(OUT_MD)


if __name__ == "__main__":
    main()
