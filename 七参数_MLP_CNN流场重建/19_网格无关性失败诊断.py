#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""分析网格无关性未通过的原因。

本脚本只读取已经生成的真实网格结果，不运行 COMSOL，也不修改原始 CSV。
输出用于论文和答辩说明：哪些指标没有收敛、可能原因是什么、结论边界在哪里。
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "七参数_MLP_CNN流场重建"
GRID_CSV = PROJECT / "analysis_results" / "grid_independence" / "grid_independence_summary.csv"
REPORT_DIR = PROJECT / "analysis_results" / "grid_independence"
OUT_MD = REPORT_DIR / "grid_independence_failure_diagnosis.md"
OUT_JSON = REPORT_DIR / "grid_independence_failure_diagnosis.json"

LEVEL_ORDER = {
    "coarse": 0,
    "medium": 1,
    "fine": 2,
    "veryfine": 3,
    "finer": 4,
    "g1": 10,
    "g2": 11,
    "g3": 12,
    "g4": 13,
    "g5": 14,
}


@dataclass(frozen=True)
class MetricRule:
    name: str
    threshold: float
    unit: str


RULES = {
    "2D": [MetricRule("Nu", 2.0, "%"), MetricRule("f", 3.0, "%")],
    "3D": [MetricRule("Tmax", 1.0, "%"), MetricRule("pressure_drop", 5.0, "%")],
}


def to_float(value: Any) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def read_rows() -> list[dict[str, str]]:
    if not GRID_CSV.exists():
        return []
    with GRID_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def level_order(level: str) -> tuple[int, int | str]:
    normalized = level.strip().lower()
    if normalized in LEVEL_ORDER:
        return (0, LEVEL_ORDER[normalized])
    match = re.fullmatch(r"g(\d+)", normalized)
    if match:
        return (1, int(match.group(1)))
    return (2, normalized)


def relative_error(coarser: float, finer: float) -> float:
    return abs(finer - coarser) / max(abs(finer), 1e-12) * 100.0


def trend(values: list[float]) -> str:
    if len(values) < 2:
        return "数据不足"
    increases = sum(b > a for a, b in zip(values, values[1:]))
    decreases = sum(b < a for a, b in zip(values, values[1:]))
    if increases and not decreases:
        return "随细化单调增大"
    if decreases and not increases:
        return "随细化单调减小"
    return "随细化非单调波动"


def diagnose() -> dict[str, Any]:
    rows = [
        row
        for row in read_rows()
        if row.get("mesh_level", "").lower() in LEVEL_ORDER
    ]
    grouped: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in rows:
        key = (row.get("dimension", ""), row.get("case", ""))
        grouped.setdefault(key, []).append(row)

    cases: list[dict[str, Any]] = []
    for (dimension, case), case_rows in sorted(grouped.items()):
        ordered = sorted(case_rows, key=lambda row: level_order(row.get("mesh_level", "")))
        metrics: list[dict[str, Any]] = []
        for rule in RULES.get(dimension, []):
            series = [
                {
                    "level": row.get("mesh_level", ""),
                    "value": to_float(row.get(rule.name)),
                }
                for row in ordered
                if to_float(row.get(rule.name)) is not None
            ]
            errors = []
            for left, right in zip(series, series[1:]):
                if left["value"] is None or right["value"] is None:
                    continue
                errors.append(
                    {
                        "from": left["level"],
                        "to": right["level"],
                        "relative_error_percent": relative_error(left["value"], right["value"]),
                    }
                )
            last_error = errors[-1]["relative_error_percent"] if errors else None
            metrics.append(
                {
                    "metric": rule.name,
                    "threshold_percent": rule.threshold,
                    "series": series,
                    "adjacent_errors": errors,
                    "last_error_percent": last_error,
                    "passed_last_pair": bool(last_error is not None and last_error <= rule.threshold),
                    "trend": trend([item["value"] for item in series if item["value"] is not None]),
                }
            )
        cases.append({"dimension": dimension, "case": case, "metrics": metrics})

    return {
        "source": str(GRID_CSV),
        "cases": cases,
        "conclusion": "当前网格细化序列中仍存在超过阈值的相邻网格差异，不能宣称网格无关性通过。",
        "likely_causes": [
            "二维 Nu/f 对局部边界层、尾迹和压降积分较敏感，自动网格 hauto 细化可能没有保证翼型柱壁面附近的边界层网格一致细化。",
            "三维 Tmax 对网格变化较稳定，但压降依赖入口/出口平均压力和流道局部速度梯度，对网格和后处理截面更敏感。",
            "粗、中、细网格由全局 hauto 控制，缺少边界层网格、局部尺寸和后处理截面一致性约束时，相邻档位可能出现非单调变化。",
        ],
        "paper_boundary": "论文中只能写已完成真实网格补算并发现网格敏感性风险，最终性能结论以正式 CFD 复算和三维迁移验证为准；不能写成已通过网格无关性验证。",
    }


def write_md(data: dict[str, Any]) -> None:
    lines = [
        "# 网格无关性未通过诊断",
        "",
        f"数据来源：`{Path(data['source']).relative_to(ROOT)}`",
        "",
        data["conclusion"],
        "",
        "## 指标序列",
        "",
    ]
    for case in data["cases"]:
        lines.extend([f"### {case['dimension']} - {case['case']}", ""])
        lines.append("| 指标 | 网格序列 | 相邻误差 | 阈值 | 末端是否通过 | 趋势 |")
        lines.append("|---|---|---|---:|---|---|")
        for metric in case["metrics"]:
            series_text = " -> ".join(f"{item['level']}={item['value']:.6g}" for item in metric["series"])
            error_text = "; ".join(
                f"{item['from']}/{item['to']}={item['relative_error_percent']:.3f}%"
                for item in metric["adjacent_errors"]
            )
            lines.append(
                f"| {metric['metric']} | {series_text} | {error_text} | {metric['threshold_percent']:.3g}% | {'是' if metric['passed_last_pair'] else '否'} | {metric['trend']} |"
            )
        lines.append("")
    lines.extend(["## 可能原因", ""])
    lines.extend(f"- {item}" for item in data["likely_causes"])
    lines.extend(["", "## 论文写法边界", "", data["paper_boundary"], ""])
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    data = diagnose()
    OUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    write_md(data)
    print(OUT_MD)


if __name__ == "__main__":
    main()
