#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""检查论文主线关键模型、结果和图片路径是否存在。

本脚本只读文件系统，不求解 COMSOL、不导图、不修改论文。用途是快速确认
二维/三维基准、最优模型和论文图目录是否还在原位置。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Artifact:
    category: str
    name: str
    path: Path
    note: str = ""


def project_path(relative_path: str) -> Path:
    return ROOT / relative_path


def build_artifacts() -> list[Artifact]:
    return [
        Artifact(
            "二维当前主线",
            "eta 归一化基准数据",
            project_path("七参数_MLP_CNN流场重建/data/dataset_summary.json"),
            "包含 Nu0=30.366123 和 f0=0.092996",
        ),
        Artifact(
            "二维当前主线",
            "DE 最优参数",
            project_path("七参数_MLP_CNN流场重建/optimization_results/mlp_cnn_de_multiloss_e10/best_params.json"),
        ),
        Artifact(
            "二维当前主线",
            "最优结构 COMSOL 复算模型",
            project_path("七参数_MLP_CNN流场重建/validation_results/mlp_cnn_de_multiloss_e10/comsol/case_1/cfd_solution/model.mph"),
        ),
        Artifact(
            "二维当前主线",
            "最优结构复算报告",
            project_path("七参数_MLP_CNN流场重建/validation_results/mlp_cnn_de_multiloss_e10/final_validation_report.json"),
        ),
        Artifact(
            "二维基准",
            "网格无关性 baseline G5 模型",
            project_path("七参数_MLP_CNN流场重建/analysis_results/grid_independence/two_d_runs/baseline/G5/cfd_solution/model.mph"),
            "这是可打开的二维 baseline mph",
        ),
        Artifact(
            "二维基准",
            "网格无关性汇总表",
            project_path("七参数_MLP_CNN流场重建/analysis_results/grid_independence/grid_independence_summary.csv"),
        ),
        Artifact(
            "三维当前主线",
            "芯片级三维基准模型",
            project_path("comsol_3d_airfoil_radiator/generated_chip_airfoil_heat_sink/chip_baseline_reference/chip_baseline_reference_realistic_heat_sink.mph"),
        ),
        Artifact(
            "三维当前主线",
            "芯片级三维最优模型",
            project_path("comsol_3d_airfoil_radiator/generated_chip_airfoil_heat_sink/chip_mlp_cnn_de_multiloss_e10/chip_mlp_cnn_de_multiloss_e10_realistic_heat_sink.mph"),
        ),
        Artifact(
            "三维当前主线",
            "三维基准/最优指标汇总",
            project_path("comsol_3d_airfoil_radiator/generated_chip_airfoil_heat_sink/results/seven_param_3d_summary.csv"),
        ),
        Artifact(
            "三维当前主线",
            "三维最优原生色标导图目录",
            project_path("comsol_3d_airfoil_radiator/generated_chip_airfoil_heat_sink/chip_mlp_cnn_de_multiloss_e10/exports_native_legend_white_20260710"),
        ),
        Artifact(
            "三维当前主线",
            "三维基准/最优统一色标对比图目录",
            project_path("comsol_3d_airfoil_radiator/generated_chip_airfoil_heat_sink/chip_mlp_cnn_de_multiloss_e10/exports_comparison"),
        ),
        Artifact(
            "旧几何掩码线",
            "旧 1000 组 baseline 最优复算模型",
            project_path("七参数_几何掩码代理优化/validation_results_1000_baseline/comsol/case_1/cfd_solution/model.mph"),
        ),
        Artifact(
            "密集散热器",
            "60 鳍片修正版已求解模型",
            project_path("comsol_3d_airfoil_radiator/generated_dense_chip_heat_sink/dense_on_plate_fixed_geom_p21/dense_solution_runs/run_20260711_165020/dense_6x10_dense_on_plate_fixed_geom_p21_solved.mph"),
            "修复旧版阵列越出基板/不居中问题",
        ),
        Artifact(
            "密集散热器",
            "60 鳍片修正版完成说明",
            project_path("comsol_3d_airfoil_radiator/generated_dense_chip_heat_sink/dense_on_plate_fixed_geom_p21/dense_solution_runs/run_20260711_165020/完成说明.md"),
        ),
        Artifact(
            "论文图片",
            "论文图片汇总目录",
            project_path("大论文初稿/完整论文初稿_图片汇总"),
        ),
        Artifact(
            "论文图片",
            "PNG 转 SVG 清单",
            project_path("大论文初稿/完整论文初稿_图片汇总_svg/conversion_manifest.json"),
        ),
        Artifact(
            "项目说明",
            "项目说明书",
            project_path("docs/10-项目说明书.md"),
        ),
    ]


def format_relative(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def main() -> int:
    artifacts = build_artifacts()
    missing: list[Artifact] = []

    print("关键产物检查：")
    current_category = ""
    for artifact in artifacts:
        if artifact.category != current_category:
            current_category = artifact.category
            print(f"\n[{current_category}]")
        exists = artifact.path.exists()
        status = "OK" if exists else "缺失"
        suffix = f"；{artifact.note}" if artifact.note else ""
        print(f"- {status} {artifact.name}: {format_relative(artifact.path)}{suffix}")
        if not exists:
            missing.append(artifact)

    if missing:
        print("\n缺失项汇总：")
        for artifact in missing:
            print(f"- {artifact.category} / {artifact.name}: {format_relative(artifact.path)}")
        return 1

    print("\n检查通过：当前论文主线的关键模型、结果和图片目录都存在。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
