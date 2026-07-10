#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""审计论文 goal 完成度。

该脚本用于最终交付前复查证据链，不运行 COMSOL，也不推断缺失实验。
输出分为“已完成”“待补算”“禁止宣称”，用于防止论文把流程准备写成
真实数值验证。
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "七参数_MLP_CNN流场重建"
THESIS = ROOT / "大论文初稿" / "基于MLP-CNN流热场重建代理模型的翼型柱阵列散热器优化研究.md"
PPT = ROOT / "大论文初稿" / "七参数MLP-CNN流热场重建答辩PPT.pptx"
REPORT_DIR = PROJECT / "reports"
AUDIT_MD = REPORT_DIR / "论文完成度审计.md"
AUDIT_JSON = REPORT_DIR / "论文完成度审计.json"
GRID_SUMMARY = PROJECT / "analysis_results" / "grid_independence" / "grid_independence_summary.csv"


def exists(relative: str) -> bool:
    return (ROOT / relative).exists()


def load_json(path: Path) -> Any:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def has_missing_grid() -> bool:
    rows = read_csv(GRID_SUMMARY)
    return any(
        "待补算" in row.get("status", "")
        or "缺少粗/中/细" in row.get("status", "")
        for row in rows
    )


def has_failed_grid() -> bool:
    return any(row.get("status", "").startswith("未通过") for row in read_csv(GRID_SUMMARY))


def has_real_grid_results(dimension: str) -> bool:
    rows = [row for row in read_csv(GRID_SUMMARY) if row.get("dimension") == dimension]
    levels = {
        row.get("mesh_level", "").lower()
        for row in rows
        if row.get("mesh_level", "").lower() not in {"formal", "coarse/medium/fine"}
    }
    return len(levels) >= 3


def grid_case_passed(dimension: str) -> bool:
    rows = [row for row in read_csv(GRID_SUMMARY) if row.get("dimension") == dimension]
    real_rows = [
        row
        for row in rows
        if row.get("mesh_level", "").lower() not in {"formal", "coarse/medium/fine"}
    ]
    if not real_rows:
        return False
    return not any(row.get("status", "").startswith("未通过") for row in real_rows)


def thesis_contains_forbidden() -> list[str]:
    forbidden = [
        "完整PINN已完成",
        "已完成CBAM主模型",
        "高保真替代CFD",
        "三维全局最优",
        "几何掩码主线",
        "网格无关性已完成",
    ]
    if not THESIS.exists():
        return ["论文文件缺失"]
    text = THESIS.read_text(encoding="utf-8")
    return [item for item in forbidden if item in text]


def ppt_slide_count() -> int | None:
    if not PPT.exists():
        return None
    try:
        from pptx import Presentation

        return len(Presentation(str(PPT)).slides)
    except Exception:
        return None


def build_audit() -> dict[str, Any]:
    metrics = load_json(PROJECT / "results" / "unet_pUt_320x96_full_e50" / "metrics.json")
    kfold = load_json(PROJECT / "results" / "pvt_unet_kfold_3_e20" / "kfold_summary.json")
    ablation = load_json(PROJECT / "results" / "pvt_ablation" / "ablation_summary.json")
    sensitivity = load_json(PROJECT / "analysis_results" / "sensitivity" / "sensitivity_summary.json")
    cfd = load_json(PROJECT / "validation_results" / "mlp_cnn_de_multiloss_e10" / "final_validation_report.json")
    slide_count = ppt_slide_count()
    forbidden = thesis_contains_forbidden()
    grid_missing = has_missing_grid()
    grid_failed = has_failed_grid()

    completed = {
        "pvt_dataset": exists("七参数_MLP_CNN流场重建/data/field_reconstruction_dataset_320x96_full_pUt.npz"),
        "main_model_metrics": bool(metrics),
        "kfold": bool(kfold),
        "ablation": bool(ablation),
        "sensitivity": bool(sensitivity),
        "two_d_cfd_validation": bool(cfd),
        "three_d_migration": exists("comsol_3d_airfoil_radiator/generated_chip_airfoil_heat_sink/results/seven_param_3d_summary.csv"),
        "thesis_md": THESIS.exists(),
        "ppt": slide_count is not None and slide_count >= 20,
        "grid_runners": exists("七参数_MLP_CNN流场重建/17_二维网格无关性运行器.py")
        and exists("comsol_3d_airfoil_radiator/20_三维网格无关性运行器.py"),
        "grid_logic_tests": exists("tests/test_grid_independence_summary.py"),
    }

    incomplete = {
        "formal_grid_independence": grid_missing or grid_failed,
        "two_d_coarse_medium_fine_real_results": not exists(
            "七参数_MLP_CNN流场重建/analysis_results/grid_independence/grid_independence_2d_real_results.csv"
        )
        or not has_real_grid_results("2D"),
        "three_d_coarse_medium_fine_real_results": not exists(
            "七参数_MLP_CNN流场重建/analysis_results/grid_independence/grid_independence_3d_real_results.csv"
        )
        or not has_real_grid_results("3D"),
        "two_d_grid_pass_thresholds": not grid_case_passed("2D"),
        "three_d_grid_pass_thresholds": not grid_case_passed("3D"),
    }

    return {
        "completed": completed,
        "incomplete": incomplete,
        "can_mark_goal_complete": all(completed.values()) and not any(incomplete.values()) and not forbidden,
        "forbidden_terms_found": forbidden,
        "main_metrics": {key: metrics.get(key) for key in ["Nu_R2", "f_R2", "eta_R2", "p_MAE", "U_MAE", "T_MAE"]},
        "kfold_summary_keys": sorted(kfold.keys()) if kfold else [],
        "ablation_groups": [row.get("group") for row in ablation] if isinstance(ablation, list) else sorted(ablation.keys()) if isinstance(ablation, dict) else [],
        "ppt_slide_count": slide_count,
        "thesis_path": str(THESIS),
        "ppt_path": str(PPT),
    }


def write_md(audit: dict[str, Any]) -> None:
    lines = [
        "# 论文完成度审计",
        "",
        "本审计只依据当前工作区真实文件、JSON、CSV 和 PPT 可打开性；不把待补算流程写成已完成实验。",
        "",
        "## 完成项",
        "",
        "| 项目 | 状态 |",
        "|---|---|",
    ]
    for name, ok in audit["completed"].items():
        lines.append(f"| {name} | {'完成' if ok else '缺失'} |")
    lines.extend(["", "## 未满足项", "", "| 项目 | 状态 |", "|---|---|"])
    status_text = {
        "formal_grid_independence": "未通过" if audit["incomplete"]["formal_grid_independence"] else "已满足",
        "two_d_coarse_medium_fine_real_results": "缺失" if audit["incomplete"]["two_d_coarse_medium_fine_real_results"] else "已补算",
        "three_d_coarse_medium_fine_real_results": "缺失" if audit["incomplete"]["three_d_coarse_medium_fine_real_results"] else "已补算",
        "two_d_grid_pass_thresholds": "未通过" if audit["incomplete"]["two_d_grid_pass_thresholds"] else "已满足",
        "three_d_grid_pass_thresholds": "未通过" if audit["incomplete"]["three_d_grid_pass_thresholds"] else "已满足",
    }
    for name in audit["incomplete"]:
        lines.append(f"| {name} | {status_text[name]} |")
    lines.extend(
        [
            "",
            "## 结论边界",
            "",
            f"- 是否可标记 goal 完成：{'是' if audit['can_mark_goal_complete'] else '否'}",
            f"- PPT 页数：{audit['ppt_slide_count']}",
            f"- 论文禁用表述命中：{audit['forbidden_terms_found'] or '无'}",
            "",
            "当前若网格无关性仍显示待补或未通过，只能报告真实补算结果和失败原因，不能写成网格无关性已完成。",
            "",
        ]
    )
    AUDIT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    audit = build_audit()
    AUDIT_JSON.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    write_md(audit)
    print(AUDIT_MD)
    if not audit["can_mark_goal_complete"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
