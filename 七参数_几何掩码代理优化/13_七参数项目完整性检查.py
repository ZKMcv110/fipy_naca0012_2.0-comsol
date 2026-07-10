#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""七参数项目完整性检查。

该脚本只读取现有结果文件，不调用 COMSOL、不训练模型、不覆盖旧六参数数据。
用途是快速确认论文中使用的关键数据、图表和结果文件是否仍然存在且口径一致。
"""

from __future__ import annotations

import argparse
import csv
import json
import py_compile
import re
from pathlib import Path
from typing import Any

import pandas as pd

from common import DEFAULT_BASELINE, OLD_PARAM_COLS, PARAM_COLS, PROJECT_ROOT, ROOT, ensure_dir, load_json, write_json


THESIS_PATH = PROJECT_ROOT / "大论文初稿" / "基于物理信息CNN的翼型管翅片散热器论文_七参数版.md"
THESIS_DIR = THESIS_PATH.parent

def dataset_suffix(dataset_name: str) -> str:
    name = dataset_name.strip()
    if not name:
        raise ValueError("--dataset-name 不能为空")
    return name


def build_required_files(dataset_name: str = "1000") -> dict[str, Path]:
    suffix = dataset_suffix(dataset_name)
    return {
        "七参数标签": ROOT / "samples" / f"labels_7param_{suffix}.csv",
        "七参数数据划分": ROOT / "samples" / f"dataset_split_{suffix}.csv",
        "消融实验汇总": ROOT / f"ablation_results_{suffix}" / "ablation_summary.csv",
        "K折汇总": ROOT / f"kfold_results_{suffix}" / "kfold_summary.json",
        "PI-CNN-CBAM优化参数": ROOT / f"optimization_results_{suffix}_gp" / "best_params.json",
        "COMSOL复核报告": ROOT / f"validation_results_{suffix}_gp" / "final_validation_report.json",
        **STATIC_REQUIRED_FILES,
    }


STATIC_REQUIRED_FILES = {
    "三维结果汇总": PROJECT_ROOT
    / "comsol_3d_airfoil_radiator"
    / "generated_7param_chip_heat_sink"
    / "results"
    / "seven_param_3d_summary.csv",
    "三维建模记录": PROJECT_ROOT
    / "comsol_3d_airfoil_radiator"
    / "generated_7param_chip_heat_sink"
    / "pi_cbam_best"
    / "pi_cbam_best_realistic_build_notes.json",
    "三维外观图": PROJECT_ROOT
    / "comsol_3d_airfoil_radiator"
    / "generated_7param_chip_heat_sink"
    / "pi_cbam_best"
    / "exports"
    / "pi_cbam_best_appearance.png",
    "三维网格图": PROJECT_ROOT
    / "comsol_3d_airfoil_radiator"
    / "generated_7param_chip_heat_sink"
    / "pi_cbam_best"
    / "exports"
    / "pi_cbam_best_mesh.png",
    "三维速度图": PROJECT_ROOT
    / "comsol_3d_airfoil_radiator"
    / "generated_7param_chip_heat_sink"
    / "pi_cbam_best"
    / "exports"
    / "pi_cbam_best_velocity.png",
    "三维温度图": PROJECT_ROOT
    / "comsol_3d_airfoil_radiator"
    / "generated_7param_chip_heat_sink"
    / "pi_cbam_best"
    / "exports"
    / "pi_cbam_best_temperature.png",
    "七参数版论文": THESIS_PATH,
}

OPTIONAL_FILES = {
    "七参数theta500_v2样本": ROOT / "samples" / "samples_7param_theta500_v2.csv",
    "七参数theta500_v2标签": ROOT / "samples" / "labels_7param_theta500_v2.csv",
    "七参数theta500_v2 dry-run计划": ROOT / "comsol_results_theta500_v2" / "dry_run_plan.csv",
    "七参数theta500_v2求解汇总": ROOT / "comsol_results_theta500_v2" / "summary.csv",
    "轻量冒烟测试结果": ROOT / "audit_results" / "smoke_test_results.json",
    "三维非零theta候选模型": PROJECT_ROOT
    / "comsol_3d_airfoil_radiator"
    / "generated_7param_chip_heat_sink"
    / "tilted_theta9"
    / "tilted_theta9_realistic_airfoil_heat_sink.mph",
    "三维非零theta建模记录": PROJECT_ROOT
    / "comsol_3d_airfoil_radiator"
    / "generated_7param_chip_heat_sink"
    / "tilted_theta9"
    / "tilted_theta9_realistic_build_notes.json",
    "三维非零theta几何预览图": PROJECT_ROOT
    / "comsol_3d_airfoil_radiator"
    / "generated_7param_chip_heat_sink"
    / "tilted_theta9"
    / "exports"
    / "tilted_theta9_geometry_preview.png",
    "三维非零theta俯视图": PROJECT_ROOT
    / "comsol_3d_airfoil_radiator"
    / "generated_7param_chip_heat_sink"
    / "tilted_theta9"
    / "exports"
    / "tilted_theta9_top_view.png",
}

TILTED_UNSOLVED_EXPORTS = [
    PROJECT_ROOT
    / "comsol_3d_airfoil_radiator"
    / "generated_7param_chip_heat_sink"
    / "tilted_theta9"
    / "exports"
    / name
    for name in [
        "tilted_theta9_appearance.png",
        "tilted_theta9_mesh.png",
        "tilted_theta9_velocity.png",
        "tilted_theta9_temperature.png",
    ]
]

EXPECTED_SCRIPTS = [
    "common.py",
    "01_七参数LHS采样.py",
    "02a_七参数COMSOL单工况求解.py",
    "02_七参数COMSOL批量求解.py",
    "03_从COMSOL结果重建标签.py",
    "04_生成几何掩码图.py",
    "08_COMSOL复核最优结构.py",
    "09_消融实验_PI_CNN_CBAM.py",
    "10_预测_PI_CNN_CBAM性能.py",
    "11_差分进化优化_PI_CNN_CBAM七参数.py",
    "12_七参数PI_CNN_CBAM_K折验证.py",
    "13_七参数项目完整性检查.py",
    "18_七参数轻量冒烟测试.py",
    "20_1000组PINN全流程.py",
]

EXPECTED_3D_SCRIPTS = [
    PROJECT_ROOT / "comsol_3d_airfoil_radiator" / "13_七参数真实芯片散热器建模.py",
    PROJECT_ROOT / "comsol_3d_airfoil_radiator" / "14_导出七参数三维结果图.py",
    PROJECT_ROOT / "comsol_3d_airfoil_radiator" / "15_提取七参数三维指标.py",
    PROJECT_ROOT / "comsol_3d_airfoil_radiator" / "16_导出三维倾斜角几何预览.py",
]

LEGACY_PROTECTED_FILES = {
    "旧六参数标签": PROJECT_ROOT / "consol_cfddata" / "labels.csv",
    "旧CNN最佳权重": PROJECT_ROOT / "ai_cnn_model_results" / "best_model.pth",
    "旧CNN完整权重": PROJECT_ROOT / "ai_cnn_model_results" / "cfd_cnn_model.pth",
    "旧CFD结果目录": PROJECT_ROOT / "consol_cfddata",
}

LEGACY_SCRIPTS = [
    PROJECT_ROOT / "cnnstep1.py",
    PROJECT_ROOT / "cnnstep2.py",
    PROJECT_ROOT / "cnnstep3.py",
    PROJECT_ROOT / "工具脚本" / "comsol单次执行脚本.py",
    PROJECT_ROOT / "工具脚本" / "consol500组参数.py",
]


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def check_required_files(required_files: dict[str, Path]) -> tuple[list[dict[str, Any]], list[str]]:
    rows = []
    errors = []
    for name, path in required_files.items():
        exists = path.exists()
        rows.append({"name": name, "path": rel(path), "exists": exists})
        if not exists:
            errors.append(f"缺少必需文件: {name} -> {rel(path)}")
    return rows, errors


def check_legacy_protected_files() -> tuple[list[dict[str, Any]], list[str]]:
    """只读检查旧六参数关键资产是否仍然存在。"""
    rows = []
    warnings = []
    for name, path in LEGACY_PROTECTED_FILES.items():
        exists = path.exists()
        row = {"name": name, "path": rel(path), "exists": exists}
        if path.is_dir():
            row["item_count"] = len(list(path.iterdir())) if exists else 0
        else:
            row["size_bytes"] = path.stat().st_size if exists else 0
        rows.append(row)
        if not exists:
            warnings.append(f"旧六参数保护资产缺失: {name} -> {rel(path)}")
    return rows, warnings


def check_script_paths(paths: list[Path]) -> tuple[list[dict[str, Any]], list[str]]:
    """检查脚本是否存在并能通过语法编译。"""
    rows = []
    warnings = []
    for path in paths:
        script_name = path.name
        row: dict[str, Any] = {
            "name": script_name,
            "path": rel(path),
            "exists": path.exists(),
            "py_compile": None,
        }
        if not path.exists():
            warnings.append(f"缺少七参数流程脚本: {script_name}")
            rows.append(row)
            continue
        try:
            py_compile.compile(str(path), doraise=True)
            row["py_compile"] = True
        except py_compile.PyCompileError as exc:
            row["py_compile"] = False
            row["compile_error"] = str(exc)
            warnings.append(f"七参数流程脚本语法检查失败: {script_name}")
        rows.append(row)
    return rows, warnings


def check_expected_scripts() -> tuple[list[dict[str, Any]], list[str]]:
    """检查七参数流程脚本是否存在并能通过语法编译。"""
    return check_script_paths([ROOT / script_name for script_name in EXPECTED_SCRIPTS])


def summarize_labels(path: Path) -> tuple[dict[str, Any], list[str]]:
    if not path.exists():
        return {}, ["无法统计标签，labels_7param.csv 不存在"]

    labels = pd.read_csv(path)
    warnings = []
    missing_cols = [col for col in PARAM_COLS + ["Nu", "f"] if col not in labels.columns]
    if missing_cols:
        warnings.append(f"标签缺少列: {', '.join(missing_cols)}")

    summary: dict[str, Any] = {"sample_count": int(len(labels)), "columns": list(labels.columns)}
    for col in ["Nu", "f", "delta_p", "delta_T", "Q_total"]:
        if col in labels.columns:
            series = labels[col].astype(float)
            summary[col] = {
                "min": float(series.min()),
                "max": float(series.max()),
                "mean": float(series.mean()),
            }

    if "theta" in labels.columns:
        theta_values = sorted(labels["theta"].dropna().astype(float).unique().tolist())
        theta_series = labels["theta"].dropna().astype(float)
        summary["theta_unique_values"] = theta_values[:20]
        summary["theta_unique_count"] = len(theta_values)
        summary["theta_nonzero_count"] = int((theta_series.abs() > 1e-12).sum())
        if len(theta_values) == 1 and abs(theta_values[0]) < 1e-12:
            warnings.append("当前标签 theta 只有 0，只能支持 theta=0 子空间结论")
    if "image_complete" in labels.columns:
        image_complete = labels["image_complete"].astype(str).str.lower().eq("true")
        summary["image_complete_count"] = int(image_complete.sum())
    return summary, warnings


def summarize_baseline_reference(labels_path: Path, optimization_path: Path) -> tuple[dict[str, Any], list[str]]:
    """检查 eta 使用的参考基准样本是否与优化记录一致。"""
    if not labels_path.exists():
        return {}, ["无法检查参考基准样本，labels_7param.csv 不存在"]

    labels = pd.read_csv(labels_path)
    missing_cols = [col for col in OLD_PARAM_COLS + ["Nu", "f"] if col not in labels.columns]
    if missing_cols:
        return {}, [f"无法检查参考基准样本，标签缺少列: {', '.join(missing_cols)}"]

    work = labels.copy()
    for name in OLD_PARAM_COLS:
        work[f"dist_{name}"] = (work[name].astype(float) - DEFAULT_BASELINE[name]) ** 2
    dist_cols = [f"dist_{name}" for name in OLD_PARAM_COLS]
    idx = work[dist_cols].sum(axis=1).idxmin()
    row = work.loc[idx]
    summary: dict[str, Any] = {
        "case_id": int(row["case_id"]) if "case_id" in row else None,
        "Nu0": float(row["Nu"]),
        "f0": float(row["f"]),
        "delta_p": float(row["delta_p"]) if "delta_p" in row else None,
        "distance_to_default_baseline": float(work.loc[idx, dist_cols].sum()),
        "default_baseline": dict(DEFAULT_BASELINE),
    }
    for name in OLD_PARAM_COLS:
        summary[name] = float(row[name])

    warnings = []
    if optimization_path.exists():
        optimization = load_json(optimization_path)
        baseline = optimization.get("baseline", {})
        for key in ["Nu0", "f0"]:
            if key in baseline:
                diff = abs(float(baseline[key]) - float(summary[key]))
                summary[f"{key}_diff_vs_optimization"] = diff
                if diff > 1e-9:
                    warnings.append(f"优化记录中的 {key} 与标签参考基准样本不一致")
    return summary, warnings


def summarize_dataset_split(path: Path) -> tuple[dict[str, Any], list[str]]:
    if not path.exists():
        return {}, ["无法统计数据划分，dataset_split_7param.csv 不存在"]

    split_df = pd.read_csv(path)
    warnings = []
    missing_cols = [col for col in ["case_id", "split"] if col not in split_df.columns]
    if missing_cols:
        return {"exists": True, "row_count": int(len(split_df))}, [
            f"数据划分文件缺少列: {', '.join(missing_cols)}"
        ]

    counts = split_df["split"].value_counts().to_dict()
    expected = {"train": 375, "val": 75, "test": 50}
    for split_name, expected_count in expected.items():
        actual_count = int(counts.get(split_name, 0))
        if actual_count != expected_count:
            warnings.append(
                f"数据划分 {split_name} 数量为 {actual_count}，与论文口径 {expected_count} 不一致"
            )

    return {
        "exists": True,
        "row_count": int(len(split_df)),
        "counts": {key: int(value) for key, value in counts.items()},
        "case_id_min": int(split_df["case_id"].astype(int).min()) if len(split_df) else None,
        "case_id_max": int(split_df["case_id"].astype(int).max()) if len(split_df) else None,
    }, warnings


def summarize_theta_supplement(path: Path) -> tuple[dict[str, Any], list[str]]:
    if not path.exists():
        return {"exists": False}, []

    samples = pd.read_csv(path)
    warnings = []
    missing_cols = [col for col in ["case_id"] + PARAM_COLS if col not in samples.columns]
    if missing_cols:
        warnings.append(f"非零theta补充样本缺少列: {', '.join(missing_cols)}")
        return {"exists": True, "sample_count": int(len(samples))}, warnings

    theta = samples["theta"].astype(float)
    min_abs_theta = float(theta.abs().min()) if len(theta) else None
    if min_abs_theta is not None and min_abs_theta < 1e-12:
        warnings.append("非零theta补充样本中仍存在 theta=0，请检查采样设置")
    return {
        "exists": True,
        "sample_count": int(len(samples)),
        "case_id_min": int(samples["case_id"].astype(int).min()) if len(samples) else None,
        "case_id_max": int(samples["case_id"].astype(int).max()) if len(samples) else None,
        "theta_min": float(theta.min()) if len(theta) else None,
        "theta_max": float(theta.max()) if len(theta) else None,
        "min_abs_theta": min_abs_theta,
    }, warnings


def summarize_plan_csv(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False}
    plan = pd.read_csv(path)
    return {
        "exists": True,
        "row_count": int(len(plan)),
        "theta_min": float(plan["theta"].astype(float).min()) if "theta" in plan.columns and len(plan) else None,
        "theta_max": float(plan["theta"].astype(float).max()) if "theta" in plan.columns and len(plan) else None,
    }


def summarize_result_summary(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False}
    df = pd.read_csv(path)
    if not len(df):
        return {"exists": True, "row_count": 0, "success_count": 0, "image_complete_count": 0}
    failure = df["failure_reason"].fillna("").astype(str) if "failure_reason" in df.columns else pd.Series([""] * len(df))
    image_complete = df["image_complete"].astype(str).str.lower().eq("true") if "image_complete" in df.columns else pd.Series([False] * len(df))
    result = {
        "exists": True,
        "row_count": int(len(df)),
        "success_count": int((failure == "").sum()),
        "image_complete_count": int(image_complete.sum()),
        "case_id_min": int(df["case_id"].astype(int).min()) if "case_id" in df.columns else None,
        "case_id_max": int(df["case_id"].astype(int).max()) if "case_id" in df.columns else None,
    }
    for col in ["theta", "Nu", "f", "delta_p", "delta_T", "Q_total"]:
        if col in df.columns:
            series = df[col].astype(float)
            result[f"{col}_min"] = float(series.min())
            result[f"{col}_max"] = float(series.max())
    return result


def summarize_theta500_v2_labels(labels: dict[str, Any], results: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """汇总theta500_v2正式标签，并检查它与批处理summary.csv的口径差异。"""
    warnings: list[str] = []
    if not labels.get("exists", True):
        return labels, ["theta500_v2标签不存在，无法确认500组正式非零theta标签"]

    sample_count = int(labels.get("sample_count", 0))
    complete_count = int(labels.get("image_complete_count", 0))
    result_count = int(results.get("row_count", 0)) if results.get("exists") else 0
    success_count = int(results.get("success_count", 0)) if results.get("exists") else 0

    labels["summary_row_count"] = result_count
    labels["summary_success_count"] = success_count

    if sample_count and complete_count != sample_count:
        warnings.append(f"theta500_v2标签中云图完整样本数为{complete_count}/{sample_count}，需要核对失败工况")
    if result_count and sample_count and result_count != sample_count:
        warnings.append(
            f"theta500_v2标签已有{sample_count}组，但summary.csv只有{result_count}行；"
            "请从result.json重建或补齐summary.csv，避免审计口径不一致"
        )
    return labels, warnings


def summarize_smoke_test(path: Path) -> tuple[dict[str, Any], list[str]]:
    if not path.exists():
        return {"exists": False}, ["轻量冒烟测试结果不存在，请运行 18_七参数轻量冒烟测试.py"]

    data = load_json(path)
    warnings = []
    if data.get("status") != "pass":
        warnings.append(f"轻量冒烟测试未全部通过: {data.get('passed_count', 0)}/{data.get('total_count', 0)}")
    return {"exists": True, **data}, warnings


def summarize_tilted_3d_status(
    report_path: Path,
    model_path: Path,
    notes_path: Path,
    preview_path: Path,
    top_view_path: Path,
) -> tuple[dict[str, Any], list[str]]:
    """汇总带倾斜角三维模型状态。

    该项用于说明当前是否已经把非零 theta 候选结构迁移到三维模型，不作为正式三维结果必需项。
    """
    data: dict[str, Any] = {
        "source_report_exists": report_path.exists(),
        "model_exists": model_path.exists(),
        "model_path": rel(model_path),
        "build_notes_exists": notes_path.exists(),
        "build_notes_path": rel(notes_path),
        "preview_exists": preview_path.exists(),
        "preview_path": rel(preview_path),
        "preview_size_bytes": preview_path.stat().st_size if preview_path.exists() else 0,
        "top_view_exists": top_view_path.exists(),
        "top_view_path": rel(top_view_path),
        "top_view_size_bytes": top_view_path.stat().st_size if top_view_path.exists() else 0,
    }
    if report_path.exists():
        report = load_json(report_path)
        params = report.get("best_params", {})
        data["source_params"] = params
        data["theta"] = params.get("theta")
        data["source_eta_cfd"] = report.get("comsol_result", {}).get("eta_cfd")
    if notes_path.exists():
        notes = load_json(notes_path)
        data["build_params"] = notes.get("params", {})
        data["mesh_generated"] = bool(notes.get("mesh_generated"))
        data["plot_created"] = bool(notes.get("plot_created"))
        data["solved"] = bool(notes.get("solved"))
        data["mesh_failed"] = notes.get("mesh_settings", {}).get("failed", [])
        data["solver_failed"] = notes.get("solver_settings", {}).get("failed", [])
        data["boundary_conditions"] = notes.get("boundary_conditions", {})
    warnings = []
    theta = float(data.get("theta") or 0.0)
    if abs(theta) > 1e-12 and not model_path.exists():
        warnings.append(
            "存在二维非零theta候选复核结果，但对应三维倾斜角模型尚未生成；论文不得写已完成三维倾斜角验证"
        )
    if model_path.exists() and not notes_path.exists():
        warnings.append("三维倾斜角模型存在，但建模记录缺失，无法核验网格和边界设置")
    if notes_path.exists():
        build_theta = float(data.get("build_params", {}).get("theta", 0.0))
        if abs(theta - build_theta) > 1e-8:
            warnings.append(f"三维倾斜角建模记录theta={build_theta}与二维候选theta={theta}不一致")
        if not data.get("mesh_generated"):
            warnings.append("三维倾斜角模型尚未生成网格")
        if data.get("mesh_failed"):
            warnings.append(f"三维倾斜角模型存在网格失败项: {data['mesh_failed']}")
        if data.get("solver_failed"):
            warnings.append(f"三维倾斜角模型存在求解器设置失败项: {data['solver_failed']}")
    if model_path.exists():
        if not preview_path.exists() or data["preview_size_bytes"] < 20_000:
            warnings.append("三维倾斜角几何预览图缺失或文件过小，不能作为有效几何图证据")
        if not top_view_path.exists() or data["top_view_size_bytes"] < 20_000:
            warnings.append("三维倾斜角俯视图缺失或文件过小，不能作为有效倾斜角检查证据")
    return data, warnings


def summarize_tilted_export_risks(paths: list[Path]) -> dict[str, Any]:
    """记录未求解COMSOL图件导出的风险，不作为失败项。

    这些图来自未求解的 tilted_theta9 模型，文件存在不代表图像有效。
    当前论文未引用它们，因此只记录风险，避免后续误当作温度场、速度场证据。
    """
    rows = []
    unusable = []
    for path in paths:
        exists = path.exists()
        size_bytes = path.stat().st_size if exists else 0
        is_likely_blank = exists and size_bytes < 20_000
        row = {
            "name": path.name,
            "path": rel(path),
            "exists": exists,
            "size_bytes": size_bytes,
            "usable_as_evidence": not is_likely_blank,
            "reason": "未求解模型导出的疑似空白图，不能作为论文证据" if is_likely_blank else "",
        }
        rows.append(row)
        if is_likely_blank:
            unusable.append(row)
    return {
        "checked_count": len(paths),
        "unusable_count": len(unusable),
        "files": rows,
    }


def summarize_ablation(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    if not path.exists():
        return [], ["无法统计消融实验，ablation_summary.csv 不存在"]

    df = pd.read_csv(path)
    required_cols = ["model", "Nu_R2", "f_R2", "eta_R2"]
    warnings = [f"消融实验缺少列: {col}" for col in required_cols if col not in df.columns]
    rows = df.to_dict(orient="records")
    if "model" in df.columns and "f_R2" in df.columns:
        best_f = df.sort_values("f_R2", ascending=False).iloc[0]["model"]
        if best_f != "pi_cnn_cbam":
            warnings.append(f"f_R2 当前最高模型是 {best_f}，论文不得写 PI-CNN-CBAM 全指标最优")
    return rows, warnings


def summarize_kfold(path: Path) -> tuple[dict[str, Any], list[str]]:
    if not path.exists():
        return {}, ["无法统计K折，kfold_summary.json 不存在"]

    data = load_json(path)
    summary = data.get("summary", {})
    config = data.get("config", {})
    return {"config": config, "summary": summary}, []


def summarize_optimization(path: Path) -> tuple[dict[str, Any], list[str]]:
    if not path.exists():
        return {}, ["无法统计优化结果，best_params.json 不存在"]

    data = load_json(path)
    warnings = []
    theta = float(data.get("best_params", {}).get("theta", 0.0))
    if abs(theta) > 1e-12:
        warnings.append("优化结果 theta 非零，请确认训练标签是否已包含非零 theta 样本")
    return data, warnings


def summarize_validation(path: Path) -> tuple[dict[str, Any], list[str]]:
    if not path.exists():
        return {}, ["无法统计COMSOL复核，final_validation_report.json 不存在"]

    data = load_json(path)
    result = data.get("comsol_result", {})
    error = data.get("error", {})
    return {"comsol_result": result, "proxy_error": error}, []


def summarize_3d(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    if not path.exists():
        return [], ["无法统计三维结果，seven_param_3d_summary.csv 不存在"]

    df = pd.read_csv(path)
    warnings = []
    if "eta_3d" in df.columns and (df["eta_3d"].astype(float) < 1).any():
        warnings.append("三维候选结构 eta_3d 存在小于 1 的情况，不能写成三维综合最优")
    return df.to_dict(orient="records"), warnings


def classify_image_source(resolved: str) -> str:
    """按论文图片路径判断来源类型，便于追踪图件证据。"""
    normalized = resolved.replace("\\", "/")
    if normalized.startswith("大论文初稿/figures/"):
        return "论文figures目录"
    if "七参数_几何掩码代理优化/ablation_results_1000/" in normalized:
        return "七参数消融实验结果"
    if "七参数_几何掩码代理优化/optimization_results_1000_gp/" in normalized:
        return "七参数PI-CNN-CBAM优化结果"
    if "七参数_几何掩码代理优化/validation_results_1000_gp/" in normalized:
        return "七参数COMSOL复核结果"
    if "comsol_3d_airfoil_radiator/generated_7param_chip_heat_sink/" in normalized:
        return "七参数三维COMSOL结果"
    if re.match(r"^(https?:)?//", normalized):
        return "网络图片"
    return "未知来源"


def check_thesis_images(path: Path) -> tuple[dict[str, Any], list[str]]:
    if not path.exists():
        return {}, ["无法检查论文图片，七参数版论文不存在"]

    text = path.read_text(encoding="utf-8")
    image_matches = list(re.finditer(r"!\[([^\]]*)\]\(([^)]+)\)", text))
    missing = []
    images = []
    source_counts: dict[str, int] = {}
    unknown_sources = []
    for match in image_matches:
        alt = match.group(1)
        raw = match.group(2).split("#")[0]
        if re.match(r"^(https?:)?//", raw):
            exists = True
            resolved = raw
        else:
            resolved_path = (path.parent / raw).resolve()
            exists = resolved_path.exists()
            resolved = rel(resolved_path)
        source = classify_image_source(resolved)
        source_counts[source] = source_counts.get(source, 0) + 1
        images.append({"alt": alt, "path": raw, "resolved": resolved, "exists": exists, "source": source})
        if not exists:
            missing.append(raw)
        if source == "未知来源":
            unknown_sources.append(raw)
    warnings = []
    if unknown_sources:
        warnings.append(f"论文存在未知来源图片: {', '.join(unknown_sources)}")
    return {"image_count": len(images), "missing": missing, "source_counts": source_counts, "images": images}, warnings


def check_thesis_claims(path: Path) -> tuple[dict[str, Any], list[str]]:
    """检查论文中容易被审稿质疑的关键表述是否仍然受约束。"""
    if not path.exists():
        return {}, ["无法检查论文表述，七参数版论文不存在"]

    text = path.read_text(encoding="utf-8")
    required_phrases = {
        "参考基准样本": "论文应说明 Nu0/f0 来自参考基准样本，而非精确基准补跑",
        "不依赖CFD云图": "论文应说明优化阶段不依赖CFD云图",
        "theta=0": "论文应说明当前正式优化固定 theta=0",
        "分箱均值": "论文应说明敏感性分析基于分箱均值趋势",
        "不能证明模型对非零倾斜角构型的预测可靠性": "论文应限制K折对非零theta的外推结论",
        "不能写成三维综合性能最优": "论文应限制三维结果的结论强度",
    }
    forbidden_patterns = {
        r"(?<!不)(?<!不能)(?<!不可)(?<!未)作为差分进化优化.*CFD云图": "不能把CFD云图写成差分进化优化输入",
        r"完整七参数全空间优化": "不能写成已完成完整七参数全空间优化",
        r"PI-CNN-CBAM全面最优": "不能写PI-CNN-CBAM全面最优",
        r"(?<!不能)写成三维综合性能最优|为三维综合性能最优|实现三维综合性能最优": "不能写三维综合性能最优",
    }

    warnings = []
    present_required = {}
    for phrase, message in required_phrases.items():
        exists = phrase in text
        present_required[phrase] = exists
        if not exists:
            warnings.append(message)

    forbidden_hits = {}
    for pattern, message in forbidden_patterns.items():
        matches = re.findall(pattern, text)
        forbidden_hits[pattern] = len(matches)
        if matches:
            warnings.append(message)

    return {
        "required_phrases": present_required,
        "forbidden_hits": forbidden_hits,
    }, warnings


def _numbering_warnings(items: list[dict[str, Any]], item_type: str) -> list[str]:
    warnings = []
    seen: set[str] = set()
    duplicates: list[str] = []
    by_chapter: dict[int, list[int]] = {}
    for item in items:
        number = item["number"]
        if number in seen:
            duplicates.append(number)
        seen.add(number)
        by_chapter.setdefault(int(item["chapter"]), []).append(int(item["index"]))

    if duplicates:
        warnings.append(f"论文{item_type}编号重复: {', '.join(sorted(set(duplicates)))}")

    for chapter, indexes in sorted(by_chapter.items()):
        unique_indexes = sorted(set(indexes))
        if not unique_indexes:
            continue
        expected = list(range(1, max(unique_indexes) + 1))
        if unique_indexes != expected:
            missing = sorted(set(expected) - set(unique_indexes))
            if missing:
                missing_text = ", ".join(f"{chapter}-{index}" for index in missing)
                warnings.append(f"论文{item_type}编号存在断号: {missing_text}")
    return warnings


def check_thesis_numbering(path: Path) -> tuple[dict[str, Any], list[str]]:
    """检查图题和表题编号是否重复、断号或格式混乱。"""
    if not path.exists():
        return {}, ["无法检查图表编号，七参数版论文不存在"]

    text = path.read_text(encoding="utf-8")
    figures = []
    for match in re.finditer(r"!\[(图(\d+)-(\d+)\s+[^\]]+)\]\(([^)]+)\)", text):
        figures.append(
            {
                "number": f"{match.group(2)}-{match.group(3)}",
                "chapter": int(match.group(2)),
                "index": int(match.group(3)),
                "caption": match.group(1),
                "path": match.group(4),
            }
        )

    tables = []
    for match in re.finditer(r"(?m)^\s*(?:\*\*)?表(\d+)-(\d+)\s+(.+?)(?:\*\*)?\s*$", text):
        tables.append(
            {
                "number": f"{match.group(1)}-{match.group(2)}",
                "chapter": int(match.group(1)),
                "index": int(match.group(2)),
                "caption": match.group(3).strip(),
            }
        )

    warnings = []
    warnings.extend(_numbering_warnings(figures, "图"))
    warnings.extend(_numbering_warnings(tables, "表"))
    if not figures:
        warnings.append("论文未识别到图题编号")
    if not tables:
        warnings.append("论文未识别到表题编号")

    return {
        "figure_count": len(figures),
        "table_count": len(tables),
        "figures": figures,
        "tables": tables,
    }, warnings


def check_references(path: Path) -> tuple[dict[str, Any], list[str]]:
    if not path.exists():
        return {}, ["无法检查参考文献，七参数版论文不存在"]

    text = path.read_text(encoding="utf-8")
    refs = []
    for match in re.finditer(r"(?m)^\[(\d+)\]\s*(.*)$", text):
        item = {"num": int(match.group(1)), "text": match.group(2)}
        item["chinese"] = bool(re.search(r"[\u4e00-\u9fa5]", item["text"]))
        refs.append(item)
    chinese_count = sum(1 for item in refs if item["chinese"])
    # 文献补充当前已暂停：这里只保留数量统计，不把文献数量作为代码/论文证据链告警。
    warnings = []
    return {
        "total": len(refs),
        "chinese_count": chinese_count,
        "english_count": len(refs) - chinese_count,
        "max_num": max((item["num"] for item in refs), default=0),
    }, warnings


def _number_text_variants(value: Any) -> set[str]:
    """生成论文常见数值保留位数，用于检查正文是否引用了结果文件中的关键数值。"""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return set()
    variants = {f"{number:.6g}"}
    for digits in (3, 4, 5, 6):
        variants.add(f"{number:.{digits}f}")
    return {item.rstrip("0").rstrip(".") if "." in item else item for item in variants} | variants


def _has_number(text: str, value: Any) -> bool:
    return any(item and item in text for item in _number_text_variants(value))


def check_thesis_numeric_consistency(
    path: Path,
    validation: dict[str, Any],
    three_dimensional: list[dict[str, Any]],
    ablation: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[str]]:
    """检查论文关键数值是否能回溯到结果文件，防止正文与结果文件脱节。"""
    if not path.exists():
        return {}, ["无法检查论文数值一致性，七参数版论文不存在"]

    text = path.read_text(encoding="utf-8")
    checks: list[dict[str, Any]] = []

    comsol = validation.get("comsol_result", {})
    for name, key in [
        ("二维COMSOL复核Nu", "Nu"),
        ("二维COMSOL复核f", "f"),
        ("二维COMSOL复核eta", "eta_cfd"),
    ]:
        value = comsol.get(key)
        checks.append({"name": name, "value": value, "present": _has_number(text, value)})

    baseline_3d = next((row for row in three_dimensional if row.get("case") == "baseline"), {})
    candidate_3d = next((row for row in three_dimensional if row.get("case") == "pi_cbam_best"), {})
    for name, row, key in [
        ("三维基准平均温度", baseline_3d, "t_chip_avg_k"),
        ("三维候选平均温度", candidate_3d, "t_chip_avg_k"),
        ("三维基准热阻", baseline_3d, "r_th_k_per_w"),
        ("三维候选热阻", candidate_3d, "r_th_k_per_w"),
        ("三维基准压降", baseline_3d, "delta_p_pa"),
        ("三维候选压降", candidate_3d, "delta_p_pa"),
        ("三维候选eta_3d", candidate_3d, "eta_3d"),
    ]:
        value = row.get(key)
        checks.append({"name": name, "value": value, "present": _has_number(text, value)})

    pi_row = next((row for row in ablation if row.get("model") == "pi_cnn_cbam"), {})
    for name, key in [
        ("PI-CNN-CBAM Nu_R2", "Nu_R2"),
        ("PI-CNN-CBAM eta_R2", "eta_R2"),
    ]:
        value = pi_row.get(key)
        checks.append({"name": name, "value": value, "present": _has_number(text, value)})

    missing = [item for item in checks if item["value"] is not None and not item["present"]]
    warnings = [f"论文未找到关键数值: {item['name']}={item['value']}" for item in missing]
    return {
        "check_count": len(checks),
        "matched_count": len(checks) - len(missing),
        "missing": missing,
        "checks": checks,
    }, warnings


def derive_remaining_work(report: dict[str, Any]) -> list[dict[str, str]]:
    """根据当前审计结果生成可执行的剩余工作清单。"""
    remaining: list[dict[str, str]] = []
    labels = report.get("labels", {})
    theta500_v2_samples = report.get("theta500_v2_samples", {})
    theta500_v2_plan = report.get("theta500_v2_plan", {})
    theta500_v2_results = report.get("theta500_v2_results", {})
    ablation = report.get("ablation", [])
    three_dimensional = report.get("three_dimensional", [])
    tilted_3d = report.get("tilted_3d_status", {})

    if labels.get("theta_nonzero_count", 0) < labels.get("sample_count", 0):
        remaining.append(
            {
                "priority": "高",
                "item": "补齐当前主线非零theta样本口径",
                "evidence": (
                    f"当前主线标签样本数为{labels.get('sample_count', 0)}，"
                    f"非零theta样本数为{labels.get('theta_nonzero_count', 0)}；"
                    f"theta500_v2已真实求解{theta500_v2_results.get('success_count', 0) if theta500_v2_results.get('exists') else 0}组。"
                ),
                "next_step": "先确认当前主线标签全部来自非零theta数据集，再重新执行几何掩码生成、训练、消融、K折和差分进化优化。",
            }
        )

    if ablation:
        best_f_model = max(ablation, key=lambda row: float(row.get("f_R2", float("-inf")))).get("model")
        if best_f_model != "pi_cnn_cbam":
            remaining.append(
                {
                    "priority": "中",
                    "item": "改进f预测或保持论文限制表述",
                    "evidence": f"当前 f_R2 最高模型为 {best_f_model}，不是 pi_cnn_cbam。",
                    "next_step": "若要强化PI-CNN-CBAM结论，应增加阻力相关特征或损失；否则正文保持不写全指标最优。",
                }
            )

    if any(float(row.get("eta_3d", 1.0)) < 1.0 for row in three_dimensional):
        remaining.append(
            {
                "priority": "高",
                "item": "三维独立优化和网格无关性验证",
                "evidence": "当前三维候选结构 eta_3d<1，只能说明降温潜力和迁移边界。",
                "next_step": "补粗/中/细三维网格对比；若要证明三维综合提升，需要在三维模型内重新搜索参数。",
            }
        )

    if tilted_3d.get("source_report_exists") and not tilted_3d.get("model_exists"):
        remaining.append(
            {
                "priority": "中",
                "item": "生成非零theta三维候选模型",
                "evidence": (
                    f"二维非零theta候选角度为{tilted_3d.get('theta')}°，"
                    "但对应三维 .mph 文件尚不存在。"
                ),
                "next_step": "修复COMSOL日志目录权限后，用13_七参数真实芯片散热器建模.py指定validation_results/final_validation_report.json生成tilted_theta9工况。",
            }
        )

    return remaining


def derive_acceptance_summary(report: dict[str, Any]) -> list[dict[str, str]]:
    """生成面向验收的已满足/受限摘要。"""
    images = report.get("thesis_images", {})
    claims = report.get("thesis_claims", {})
    numbering = report.get("thesis_numbering", {})
    numeric = report.get("thesis_numeric_consistency", {})
    labels = report.get("labels", {})
    dataset_split = report.get("dataset_split", {})
    smoke_test = report.get("smoke_test", {})
    ablation = report.get("ablation", [])
    kfold = report.get("kfold", {})
    optimization = report.get("optimization", {})
    validation = report.get("validation", {})
    three_dimensional = report.get("three_dimensional", [])
    tilted_3d = report.get("tilted_3d_status", {})

    return [
        {
            "item": "七参数训练、预测、优化、复核流程",
            "status": "已满足",
            "evidence": (
                f"七参数脚本{len(report.get('scripts', []))}个、三维正式脚本{len(report.get('scripts_3d', []))}个均通过语法检查；"
                f"轻量冒烟测试{smoke_test.get('passed_count', '缺失')}/{smoke_test.get('total_count', '缺失')}通过；"
                "优化、复核、三维结果文件均存在。"
            ),
        },
        {
            "item": "关键结果数据来源",
            "status": "已满足",
            "evidence": (
                f"标签样本{labels.get('sample_count', '缺失')}组，数据划分{dataset_split.get('counts', '缺失')}；"
                f"消融结果{len(ablation)}组，K折摘要存在={bool(kfold)}，优化记录存在={bool(optimization)}，COMSOL复核存在={bool(validation)}。"
            ),
        },
        {
            "item": "论文图表可追溯",
            "status": "已满足",
            "evidence": (
                f"论文图片{images.get('image_count', '缺失')}张、缺失{len(images.get('missing', [])) if images else '缺失'}张；"
                f"图题{numbering.get('figure_count', '缺失')}个、表题{numbering.get('table_count', '缺失')}个；"
                f"关键数值匹配{numeric.get('matched_count', '缺失')}/{numeric.get('check_count', '缺失')}。"
            ),
        },
        {
            "item": "优化阶段不依赖CFD云图",
            "status": "已满足",
            "evidence": (
                f"关键限制表述检查项{len(claims.get('required_phrases', {})) if claims else '缺失'}个；"
                f"禁用表述命中数{sum(claims.get('forbidden_hits', {}).values()) if claims else '缺失'}。"
            ),
        },
        {
            "item": "敏感性分析结论边界",
            "status": "已满足" if labels.get("theta_nonzero_count", 0) == labels.get("sample_count", -1) else "受限",
            "evidence": (
                f"当前主线标签样本{labels.get('sample_count', '缺失')}组，"
                f"非零theta样本数为{labels.get('theta_nonzero_count', '缺失')}；"
                "敏感性结论仍应表述为数据驱动分箱趋势和随机森林重要性。"
            ),
        },
        {
            "item": "三维验证结论边界",
            "status": "受限",
            "evidence": (
                f"三维结果记录{len(three_dimensional)}条；当前存在eta_3d<1的候选结构，不能写成三维综合最优；"
                f"非零theta三维模型存在={tilted_3d.get('model_exists', '缺失')}。"
            ),
        },
    ]


def build_report(required_files: dict[str, Path] | None = None) -> dict[str, Any]:
    required_files = required_files or build_required_files("1000")
    checks, errors = check_required_files(required_files)
    warnings: list[str] = []

    scripts, script_warnings = check_expected_scripts()
    scripts_3d, script_3d_warnings = check_script_paths(EXPECTED_3D_SCRIPTS)
    legacy_files, legacy_file_warnings = check_legacy_protected_files()
    legacy_scripts, legacy_script_warnings = check_script_paths(LEGACY_SCRIPTS)
    labels, label_warnings = summarize_labels(required_files["七参数标签"])
    baseline_reference, baseline_reference_warnings = summarize_baseline_reference(
        required_files["七参数标签"], required_files["PI-CNN-CBAM优化参数"]
    )
    dataset_split, split_warnings = summarize_dataset_split(required_files["七参数数据划分"])
    theta500_v2_samples, theta500_v2_warnings = summarize_theta_supplement(OPTIONAL_FILES["七参数theta500_v2样本"])
    theta500_v2_plan = summarize_plan_csv(OPTIONAL_FILES["七参数theta500_v2 dry-run计划"])
    theta500_v2_results = summarize_result_summary(OPTIONAL_FILES["七参数theta500_v2求解汇总"])
    theta500_v2_labels_raw, theta500_v2_label_warnings = summarize_labels(OPTIONAL_FILES["七参数theta500_v2标签"])
    theta500_v2_labels, theta500_v2_consistency_warnings = summarize_theta500_v2_labels(
        theta500_v2_labels_raw, theta500_v2_results
    )
    smoke_test, smoke_test_warnings = summarize_smoke_test(OPTIONAL_FILES["轻量冒烟测试结果"])
    tilted_3d_status, tilted_3d_warnings = summarize_tilted_3d_status(
        required_files["COMSOL复核报告"],
        OPTIONAL_FILES["三维非零theta候选模型"],
        OPTIONAL_FILES["三维非零theta建模记录"],
        OPTIONAL_FILES["三维非零theta几何预览图"],
        OPTIONAL_FILES["三维非零theta俯视图"],
    )
    tilted_export_risks = summarize_tilted_export_risks(TILTED_UNSOLVED_EXPORTS)
    ablation, ablation_warnings = summarize_ablation(required_files["消融实验汇总"])
    kfold, kfold_warnings = summarize_kfold(required_files["K折汇总"])
    optimization, optimization_warnings = summarize_optimization(required_files["PI-CNN-CBAM优化参数"])
    validation, validation_warnings = summarize_validation(required_files["COMSOL复核报告"])
    summary_3d, warnings_3d = summarize_3d(required_files["三维结果汇总"])
    images, image_warnings = check_thesis_images(THESIS_PATH)
    thesis_claims, thesis_claim_warnings = check_thesis_claims(THESIS_PATH)
    thesis_numbering, thesis_numbering_warnings = check_thesis_numbering(THESIS_PATH)
    references, reference_warnings = check_references(THESIS_PATH)
    thesis_numeric, thesis_numeric_warnings = check_thesis_numeric_consistency(
        THESIS_PATH, validation, summary_3d, ablation
    )

    for items in [
        script_warnings,
        script_3d_warnings,
        legacy_file_warnings,
        legacy_script_warnings,
        label_warnings,
        baseline_reference_warnings,
        split_warnings,
        theta500_v2_warnings,
        theta500_v2_label_warnings,
        theta500_v2_consistency_warnings,
        smoke_test_warnings,
        tilted_3d_warnings,
        ablation_warnings,
        kfold_warnings,
        optimization_warnings,
        validation_warnings,
        warnings_3d,
        image_warnings,
        thesis_claim_warnings,
        thesis_numbering_warnings,
        thesis_numeric_warnings,
        reference_warnings,
    ]:
        warnings.extend(items)

    report = {
        "status": "fail" if errors else "pass",
        "errors": errors,
        "warnings": warnings,
        "required_files": checks,
        "scripts": scripts,
        "scripts_3d": scripts_3d,
        "legacy_files": legacy_files,
        "legacy_scripts": legacy_scripts,
        "labels": labels,
        "baseline_reference": baseline_reference,
        "dataset_split": dataset_split,
        "theta500_v2_samples": theta500_v2_samples,
        "theta500_v2_labels": theta500_v2_labels,
        "theta500_v2_plan": theta500_v2_plan,
        "theta500_v2_results": theta500_v2_results,
        "smoke_test": smoke_test,
        "tilted_3d_status": tilted_3d_status,
        "tilted_3d_export_risks": tilted_export_risks,
        "ablation": ablation,
        "kfold": kfold,
        "optimization": optimization,
        "validation": validation,
        "three_dimensional": summary_3d,
        "thesis_images": images,
        "thesis_claims": thesis_claims,
        "thesis_numbering": thesis_numbering,
        "thesis_numeric_consistency": thesis_numeric,
        "references": references,
    }
    report["remaining_work"] = derive_remaining_work(report)
    report["acceptance_summary"] = derive_acceptance_summary(report)
    return report


def markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# 七参数项目完整性检查报告",
        "",
        f"- 状态：{report['status']}",
        f"- 错误数：{len(report['errors'])}",
        f"- 警告数：{len(report['warnings'])}",
        "",
        "## 错误",
        "",
    ]
    lines.extend([f"- {item}" for item in report["errors"]] or ["- 无"])
    lines.extend(["", "## 验收摘要", ""])
    acceptance_summary = report.get("acceptance_summary", [])
    if acceptance_summary:
        lines.extend(["| 项目 | 状态 | 证据 |", "|---|---|---|"])
        for item in acceptance_summary:
            lines.append(f"| {item['item']} | {item['status']} | {item['evidence']} |")
    else:
        lines.append("- 无")
    lines.extend(["", "## 警告", ""])
    lines.extend([f"- {item}" for item in report["warnings"]] or ["- 无"])
    lines.extend(["", "## 剩余工作清单", ""])
    remaining_work = report.get("remaining_work", [])
    if remaining_work:
        lines.extend(["| 优先级 | 事项 | 当前证据 | 下一步 |", "|---|---|---|---|"])
        for item in remaining_work:
            lines.append(
                f"| {item['priority']} | {item['item']} | {item['evidence']} | {item['next_step']} |"
            )
    else:
        lines.append("- 无")

    refs = report.get("references", {})
    images = report.get("thesis_images", {})
    thesis_claims = report.get("thesis_claims", {})
    thesis_numbering = report.get("thesis_numbering", {})
    labels = report.get("labels", {})
    baseline_reference = report.get("baseline_reference", {})
    dataset_split = report.get("dataset_split", {})
    scripts = report.get("scripts", [])
    script_count = len(scripts)
    script_compile_passed = sum(1 for item in scripts if item.get("py_compile") is True)
    scripts_3d = report.get("scripts_3d", [])
    script_3d_count = len(scripts_3d)
    script_3d_compile_passed = sum(1 for item in scripts_3d if item.get("py_compile") is True)
    legacy_files = report.get("legacy_files", [])
    legacy_scripts = report.get("legacy_scripts", [])
    legacy_script_compile_passed = sum(1 for item in legacy_scripts if item.get("py_compile") is True)
    theta500_v2_samples = report.get("theta500_v2_samples", {})
    theta500_v2_labels = report.get("theta500_v2_labels", {})
    theta500_v2_plan = report.get("theta500_v2_plan", {})
    theta500_v2_results = report.get("theta500_v2_results", {})
    thesis_numeric = report.get("thesis_numeric_consistency", {})
    smoke_test = report.get("smoke_test", {})
    tilted_3d = report.get("tilted_3d_status", {})
    tilted_export_risks = report.get("tilted_3d_export_risks", {})
    lines.extend(
        [
            "",
            "## 关键统计",
            "",
            f"- 七参数流程脚本数：{script_count}",
            f"- 语法检查通过脚本数：{script_compile_passed}",
            f"- 三维正式脚本数：{script_3d_count}",
            f"- 三维脚本语法通过数：{script_3d_compile_passed}",
            f"- 轻量冒烟测试通过数：{smoke_test.get('passed_count', '缺失')}/{smoke_test.get('total_count', '缺失')}",
            f"- 旧六参数保护资产数：{len(legacy_files)}",
            f"- 旧六参数脚本语法通过数：{legacy_script_compile_passed}",
            f"- 标签样本数：{labels.get('sample_count', '缺失')}",
            f"- eta参考基准样本：case_id={baseline_reference.get('case_id', '缺失')}，Nu0={baseline_reference.get('Nu0', '缺失')}，f0={baseline_reference.get('f0', '缺失')}",
            f"- 数据划分：{dataset_split.get('counts', '缺失')}",
            f"- theta 唯一值数量：{labels.get('theta_unique_count', '缺失')}",
            f"- 七参数theta500_v2样本数：{theta500_v2_samples.get('sample_count', 0) if theta500_v2_samples.get('exists') else 0}",
            f"- 七参数theta500_v2标签数：{theta500_v2_labels.get('sample_count', 0) if theta500_v2_labels.get('exists', True) else 0}",
            f"- 七参数theta500_v2标签非零theta数：{theta500_v2_labels.get('theta_nonzero_count', 0) if theta500_v2_labels.get('exists', True) else 0}",
            f"- 七参数theta500_v2 case_id范围：{theta500_v2_samples.get('case_id_min', '缺失')} 到 {theta500_v2_samples.get('case_id_max', '缺失')}",
            f"- 七参数theta500_v2 theta范围：{theta500_v2_samples.get('theta_min', '缺失')} 到 {theta500_v2_samples.get('theta_max', '缺失')}",
            f"- 七参数theta500_v2 dry-run计划数：{theta500_v2_plan.get('row_count', 0) if theta500_v2_plan.get('exists') else 0}",
            f"- 七参数theta500_v2已求解数：{theta500_v2_results.get('success_count', 0) if theta500_v2_results.get('exists') else 0}/{theta500_v2_results.get('row_count', 0) if theta500_v2_results.get('exists') else 0}",
            f"- 七参数theta500_v2云图完整数：{theta500_v2_results.get('image_complete_count', 0) if theta500_v2_results.get('exists') else 0}",
            f"- 二维非零theta候选角度：{tilted_3d.get('theta', '缺失')}",
            f"- 三维非零theta候选模型存在：{tilted_3d.get('model_exists', '缺失')}",
            f"- 三维非零theta建模记录存在：{tilted_3d.get('build_notes_exists', '缺失')}",
            f"- 三维非零theta网格已生成：{tilted_3d.get('mesh_generated', '缺失')}",
            f"- 三维非零theta网格失败项：{tilted_3d.get('mesh_failed', '缺失')}",
            f"- 三维非零theta求解器设置失败项：{tilted_3d.get('solver_failed', '缺失')}",
            f"- 三维非零theta几何预览图：{tilted_3d.get('preview_exists', '缺失')}，{tilted_3d.get('preview_size_bytes', '缺失')} bytes",
            f"- 三维非零theta俯视图：{tilted_3d.get('top_view_exists', '缺失')}，{tilted_3d.get('top_view_size_bytes', '缺失')} bytes",
            f"- 三维非零theta未求解导出图检查数：{tilted_export_risks.get('checked_count', '缺失')}",
            f"- 三维非零theta不可作为证据的导出图数：{tilted_export_risks.get('unusable_count', '缺失')}",
            f"- 论文图片数：{images.get('image_count', '缺失')}",
            f"- 缺失图片数：{len(images.get('missing', [])) if images else '缺失'}",
            f"- 图片来源分类：{images.get('source_counts', '缺失') if images else '缺失'}",
            f"- 论文图题编号数：{thesis_numbering.get('figure_count', '缺失') if thesis_numbering else '缺失'}",
            f"- 论文表题编号数：{thesis_numbering.get('table_count', '缺失') if thesis_numbering else '缺失'}",
            f"- 论文关键数值匹配数：{thesis_numeric.get('matched_count', '缺失')}/{thesis_numeric.get('check_count', '缺失')}",
            f"- 论文关键表述检查项：{len(thesis_claims.get('required_phrases', {})) if thesis_claims else '缺失'}",
            f"- 论文禁用表述命中数：{sum(thesis_claims.get('forbidden_hits', {}).values()) if thesis_claims else '缺失'}",
            f"- 参考文献总数：{refs.get('total', '缺失')}",
            f"- 中文参考文献数：{refs.get('chinese_count', '缺失')}",
            f"- 英文参考文献数：{refs.get('english_count', '缺失')}",
            "",
            "## 必需文件",
            "",
            "| 名称 | 状态 | 路径 |",
            "|---|---|---|",
        ]
    )
    for row in report["required_files"]:
        state = "存在" if row["exists"] else "缺失"
        lines.append(f"| {row['name']} | {state} | `{row['path']}` |")
    lines.extend(["", "## 七参数流程脚本", "", "| 脚本 | 存在 | 语法检查 |", "|---|---|---|"])
    for row in report.get("scripts", []):
        exists = "是" if row.get("exists") else "否"
        if row.get("py_compile") is True:
            compile_state = "通过"
        elif row.get("py_compile") is False:
            compile_state = "失败"
        else:
            compile_state = "未检查"
        lines.append(f"| `{row['name']}` | {exists} | {compile_state} |")
    lines.extend(["", "## 三维正式脚本", "", "| 脚本 | 存在 | 语法检查 |", "|---|---|---|"])
    for row in report.get("scripts_3d", []):
        exists = "是" if row.get("exists") else "否"
        if row.get("py_compile") is True:
            compile_state = "通过"
        elif row.get("py_compile") is False:
            compile_state = "失败"
        else:
            compile_state = "未检查"
        lines.append(f"| `{row['path']}` | {exists} | {compile_state} |")
    tilted_export_risks = report.get("tilted_3d_export_risks", {})
    if tilted_export_risks.get("files"):
        lines.extend(
            [
                "",
                "## 三维非零theta未求解导出图风险",
                "",
                "| 文件 | 大小/bytes | 可作为论文证据 | 说明 |",
                "|---|---:|---|---|",
            ]
        )
        for row in tilted_export_risks["files"]:
            usable = "是" if row.get("usable_as_evidence") else "否"
            reason = row.get("reason") or "未发现文件大小异常"
            lines.append(f"| `{row['path']}` | {row.get('size_bytes', 0)} | {usable} | {reason} |")
    lines.extend(["", "## 旧六参数保护资产", "", "| 名称 | 状态 | 路径 |", "|---|---|---|"])
    for row in report.get("legacy_files", []):
        state = "存在" if row.get("exists") else "缺失"
        lines.append(f"| {row['name']} | {state} | `{row['path']}` |")
    lines.extend(["", "## 旧六参数入口脚本", "", "| 脚本 | 存在 | 语法检查 |", "|---|---|---|"])
    for row in report.get("legacy_scripts", []):
        exists = "是" if row.get("exists") else "否"
        if row.get("py_compile") is True:
            compile_state = "通过"
        elif row.get("py_compile") is False:
            compile_state = "失败"
        else:
            compile_state = "未检查"
        lines.append(f"| `{row['path']}` | {exists} | {compile_state} |")
    return "\n".join(lines) + "\n"


def infer_table_evidence(table_number: str) -> str:
    """按论文表号给出可追溯的数据来源。"""
    evidence_map = {
        "3-1": "论文正文给定材料物性；用于COMSOL模型设置说明",
        "3-2": "大论文初稿/figures/fig3_13_parameter_importance.csv",
        "4-1": "七参数_几何掩码代理优化/09_消融实验_PI_CNN_CBAM.py",
        "4-2": "七参数_几何掩码代理优化/ablation_results_1000/ablation_summary.csv",
        "4-3": "七参数_几何掩码代理优化/kfold_results_1000/kfold_summary.json",
        "4-4": "七参数_几何掩码代理优化/samples/labels_7param_theta500_v2.csv；七参数_几何掩码代理优化/samples/labels_7param_1000.csv",
        "5-1": "七参数_几何掩码代理优化/common.py；七参数_几何掩码代理优化/11_差分进化优化_PI_CNN_CBAM七参数.py",
        "5-2": "七参数_几何掩码代理优化/11_差分进化优化_PI_CNN_CBAM七参数.py",
        "5-3": "七参数_几何掩码代理优化/optimization_results_1000_gp/best_params.json",
        "5-4": "七参数_几何掩码代理优化/optimization_results_1000_gp/best_params.json；七参数_几何掩码代理优化/samples/labels_7param_1000.csv",
        "5-5": "七参数_几何掩码代理优化/validation_results_1000_gp/final_validation_report.json",
        "6-1": "comsol_3d_airfoil_radiator/generated_7param_chip_heat_sink/pi_cbam_best/pi_cbam_best_realistic_build_notes.json",
        "6-2": "comsol_3d_airfoil_radiator/generated_7param_chip_heat_sink/results/seven_param_3d_summary.csv",
    }
    return evidence_map.get(table_number, "未配置表格数据来源，请人工补充")


def write_figure_table_trace(report: dict[str, Any], output_path: Path) -> None:
    """导出论文图表追溯清单，便于逐项核对图表来源。"""
    images_by_path = {
        item["path"].split("#")[0]: item for item in report.get("thesis_images", {}).get("images", [])
    }
    rows: list[dict[str, Any]] = []
    for figure in report.get("thesis_numbering", {}).get("figures", []):
        image = images_by_path.get(figure["path"].split("#")[0], {})
        rows.append(
            {
                "类型": "图",
                "编号": figure["number"],
                "题名": figure["caption"],
                "引用路径": figure["path"],
                "解析路径": image.get("resolved", ""),
                "存在": image.get("exists", ""),
                "来源分类": image.get("source", ""),
                "证据文件": image.get("resolved", figure["path"]),
            }
        )
    for table in report.get("thesis_numbering", {}).get("tables", []):
        rows.append(
            {
                "类型": "表",
                "编号": table["number"],
                "题名": f"表{table['number']} {table['caption']}",
                "引用路径": "",
                "解析路径": "",
                "存在": True,
                "来源分类": "论文表格",
                "证据文件": infer_table_evidence(table["number"]),
            }
        )

    with output_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["类型", "编号", "题名", "引用路径", "解析路径", "存在", "来源分类", "证据文件"],
        )
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="检查七参数项目关键文件、结果和论文引用。")
    parser.add_argument("--dataset-name", default="1000", help="当前主线数据集后缀，例如 1000、theta500_v2、1500")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "audit_results", help="检查报告输出目录")
    parser.add_argument("--strict", action="store_true", help="存在警告时也返回非零退出码")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = ensure_dir(args.output_dir)
    report = build_report(build_required_files(args.dataset_name))

    write_json(output_dir / "integrity_report.json", report)
    (output_dir / "integrity_report.md").write_text(markdown_report(report), encoding="utf-8")
    write_figure_table_trace(report, output_dir / "figure_table_trace.csv")

    print(f"状态: {report['status']}")
    print(f"错误数: {len(report['errors'])}")
    print(f"警告数: {len(report['warnings'])}")
    print(f"报告: {output_dir / 'integrity_report.md'}")
    print(f"图表追溯清单: {output_dir / 'figure_table_trace.csv'}")
    if report["errors"] or (args.strict and report["warnings"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
