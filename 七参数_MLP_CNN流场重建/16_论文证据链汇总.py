#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""生成论文证据链总表。

该脚本只检查当前工作区中已有脚本、数据、指标和图片是否存在，
不推断实验结论，也不把缺失结果写成已完成结果。
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "七参数_MLP_CNN流场重建" / "reports"
REPORT_PATH = REPORT_DIR / "论文证据链总表.md"


EVIDENCE_ITEMS = [
    {
        "section": "第3章 数据集",
        "claim": "1000 组 p/U/T 高分辨率 PVT 数据集",
        "script": "七参数_MLP_CNN流场重建/01_构建流场数据集.py",
        "data": "七参数_MLP_CNN流场重建/data/field_reconstruction_dataset_320x96_full_pUt.npz",
        "figure": "",
        "ppt": "数据集构建页",
    },
    {
        "section": "第4章 主模型",
        "claim": "Conditional U-Net 主模型训练指标",
        "script": "七参数_MLP_CNN流场重建/08_UNet高精度流场重建训练.py",
        "data": "七参数_MLP_CNN流场重建/results/unet_pUt_320x96_full_e50/metrics.json",
        "figure": "七参数_MLP_CNN流场重建/results/unet_pUt_320x96_full_e50/prediction_scatter.png",
        "ppt": "主模型结果页",
    },
    {
        "section": "第4章 PVT 云图",
        "claim": "p/U/T COMSOL 风格规则采样场、预测场和误差场",
        "script": "七参数_MLP_CNN流场重建/12_批量导出PVT云图.py",
        "data": "七参数_MLP_CNN流场重建/results/pvt_comsol_style_exports_pUt_full_e50_case20040",
        "figure": "七参数_MLP_CNN流场重建/results/pvt_comsol_style_exports_pUt_full_e50_case20040/case_20040_T_pred_style.png",
        "ppt": "PVT 云图对比页",
    },
    {
        "section": "第4章 K 折",
        "claim": "PVT 主模型 3 折验证",
        "script": "七参数_MLP_CNN流场重建/13_PVT_K折验证.py",
        "data": "七参数_MLP_CNN流场重建/results/pvt_unet_kfold_3_e20/kfold_summary.json",
        "figure": "",
        "ppt": "K 折验证页",
    },
    {
        "section": "第4章 消融",
        "claim": "A0-A4 五组精简版消融实验",
        "script": "七参数_MLP_CNN流场重建/14_PVT消融实验.py",
        "data": "七参数_MLP_CNN流场重建/results/pvt_ablation/ablation_summary.json",
        "figure": "",
        "ppt": "消融实验页",
    },
    {
        "section": "第4章 敏感性",
        "claim": "Pearson/Spearman、随机森林和局部扰动敏感性分析",
        "script": "七参数_MLP_CNN流场重建/06_参数敏感性分析.py",
        "data": "七参数_MLP_CNN流场重建/analysis_results/sensitivity/sensitivity_summary.json",
        "figure": "七参数_MLP_CNN流场重建/analysis_results/sensitivity/sensitivity_bar_eta.png",
        "ppt": "敏感性分析页",
    },
    {
        "section": "第2章/第6章 网格",
        "claim": "二维和三维网格无关性汇总",
        "script": "七参数_MLP_CNN流场重建/15_网格无关性汇总.py",
        "data": "七参数_MLP_CNN流场重建/analysis_results/grid_independence/grid_independence_summary.md",
        "figure": "",
        "ppt": "网格无关性页",
    },
    {
        "section": "第2章/第6章 网格",
        "claim": "二维粗/中/细网格真实补算运行入口",
        "script": "七参数_MLP_CNN流场重建/17_二维网格无关性运行器.py",
        "data": "七参数_MLP_CNN流场重建/analysis_results/grid_independence/grid_independence_todo.md",
        "figure": "",
        "ppt": "网格无关性页",
    },
    {
        "section": "第2章/第6章 网格",
        "claim": "三维粗/中/细网格真实补算运行入口",
        "script": "comsol_3d_airfoil_radiator/20_三维网格无关性运行器.py",
        "data": "七参数_MLP_CNN流场重建/analysis_results/grid_independence/grid_independence_todo.md",
        "figure": "",
        "ppt": "网格无关性页",
    },
    {
        "section": "第2章/第6章 网格",
        "claim": "网格无关性判定逻辑测试",
        "script": "tests/test_grid_independence_summary.py",
        "data": "七参数_MLP_CNN流场重建/analysis_results/grid_independence/grid_independence_summary.md",
        "figure": "",
        "ppt": "网格无关性页",
    },
    {
        "section": "第2章/第6章 网格",
        "claim": "网格无关性未通过原因诊断",
        "script": "七参数_MLP_CNN流场重建/19_网格无关性失败诊断.py",
        "data": "七参数_MLP_CNN流场重建/analysis_results/grid_independence/grid_independence_failure_diagnosis.md",
        "figure": "",
        "ppt": "网格无关性页",
    },
    {
        "section": "第2章/第6章 网格",
        "claim": "网格无关性整改方案",
        "script": "",
        "data": "七参数_MLP_CNN流场重建/analysis_results/grid_independence/grid_independence_remediation_plan.md",
        "figure": "",
        "ppt": "结论与不足页",
    },
    {
        "section": "第2章/第6章 网格",
        "claim": "网格无关性后续补算执行清单",
        "script": "",
        "data": "七参数_MLP_CNN流场重建/analysis_results/grid_independence/grid_independence_execution_checklist.md",
        "figure": "",
        "ppt": "结论与不足页",
    },
    {
        "section": "第2章/第6章 网格",
        "claim": "网格补算下一步自动决策",
        "script": "七参数_MLP_CNN流场重建/20_网格补算决策.py",
        "data": "七参数_MLP_CNN流场重建/analysis_results/grid_independence/grid_independence_next_action.md",
        "figure": "",
        "ppt": "结论与不足页",
    },
    {
        "section": "第2章/第6章 网格",
        "claim": "二维壁面边界层网格尝试记录",
        "script": "七参数_几何掩码代理优化/02a_七参数COMSOL单工况求解.py",
        "data": "七参数_MLP_CNN流场重建/analysis_results/grid_independence/boundary_layer_attempts.md",
        "figure": "",
        "ppt": "结论与不足页",
    },
    {
        "section": "附录A 证据链",
        "claim": "论文完成度审计与结论边界",
        "script": "七参数_MLP_CNN流场重建/18_论文完成度审计.py",
        "data": "七参数_MLP_CNN流场重建/reports/论文完成度审计.md",
        "figure": "",
        "ppt": "结论与不足页",
    },
    {
        "section": "答辩问答",
        "claim": "老师可能提问与回答准备",
        "script": "",
        "data": "七参数_MLP_CNN流场重建/reports/答辩问答准备.md",
        "figure": "",
        "ppt": "答辩问答页",
    },
    {
        "section": "第5章 DE 优化",
        "claim": "二维 DE 最优参数",
        "script": "七参数_MLP_CNN流场重建/03_DE优化eta.py",
        "data": "七参数_MLP_CNN流场重建/optimization_results/mlp_cnn_de_multiloss_e10/best_params.json",
        "figure": "",
        "ppt": "DE 优化页",
    },
    {
        "section": "第5章 CFD 复算",
        "claim": "二维 CFD 复算验证",
        "script": "七参数_MLP_CNN流场重建/04_准备CFD复算输入.py",
        "data": "七参数_MLP_CNN流场重建/validation_results/mlp_cnn_de_multiloss_e10/final_validation_report.json",
        "figure": "七参数_MLP_CNN流场重建/validation_results/mlp_cnn_de_multiloss_e10/comsol/case_1/cfd_solution",
        "ppt": "二维 CFD 复算页",
    },
    {
        "section": "第6章 三维迁移",
        "claim": "三维散热器迁移验证",
        "script": "comsol_3d_airfoil_radiator/build_realistic_airfoil_heat_sink.py",
        "data": "comsol_3d_airfoil_radiator/generated_chip_airfoil_heat_sink/results/seven_param_3d_summary.csv",
        "figure": "comsol_3d_airfoil_radiator/generated_chip_airfoil_heat_sink/chip_mlp_cnn_de_multiloss_e10/exports",
        "ppt": "三维迁移验证页",
    },
    {
        "section": "最终交付",
        "claim": "论文、PPT、实验结果和未通过边界的总状态说明",
        "script": "",
        "data": "七参数_MLP_CNN流场重建/reports/最终交付状态报告.md",
        "figure": "",
        "ppt": "结论与不足页",
    },
    {
        "section": "答辩 PPT",
        "claim": "完整答辩演示文稿",
        "script": "",
        "data": "大论文初稿/七参数MLP-CNN流热场重建答辩PPT.pptx",
        "figure": "",
        "ppt": "全稿",
    },
]


EVIDENCE_ITEMS.append(
    {
        "section": "附录A 证据链",
        "claim": "旧论文可复用写法与旧六参数数据边界",
        "script": "",
        "data": "七参数_MLP_CNN流场重建/reports/旧论文可复用内容清单.md",
        "figure": "",
        "ppt": "结论与不足页",
    }
)

EVIDENCE_ITEMS.append(
    {
        "section": "附录A 证据链",
        "claim": "项目目录整理与迁移边界",
        "script": "",
        "data": "docs/项目目录迁移清单.md",
        "figure": "",
        "ppt": "结论与不足页",
    }
)


def path_status(relative_path: str) -> str:
    if not relative_path:
        return "不适用"
    return "存在" if (ROOT / relative_path).exists() else "缺失"


def summarize_main_metrics() -> list[str]:
    metrics_path = ROOT / "七参数_MLP_CNN流场重建" / "results" / "unet_pUt_320x96_full_e50" / "metrics.json"
    if not metrics_path.exists():
        return ["主模型指标文件缺失。"]
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    keys = ["Nu_R2", "f_R2", "eta_R2", "p_MAE", "U_MAE", "T_MAE"]
    return [f"- `{key}` = {metrics.get(key)}" for key in keys]


def build_report() -> str:
    lines = [
        "# 论文证据链总表",
        "",
        "本表由 `七参数_MLP_CNN流场重建/16_论文证据链汇总.py` 自动生成，只记录当前文件是否存在。",
        "",
        "## 主模型核心指标",
        "",
        *summarize_main_metrics(),
        "",
        "## 证据链索引",
        "",
        "| 论文章节 | 结论 | 脚本 | 数据/指标 | 图片/导出 | PPT位置 | 状态 |",
        "|---|---|---|---|---|---|---|",
    ]
    for item in EVIDENCE_ITEMS:
        statuses = [
            path_status(item["script"]),
            path_status(item["data"]),
            path_status(item["figure"]),
        ]
        required_statuses = [status for status in statuses if status != "不适用"]
        overall = "存在" if required_statuses and all(status == "存在" for status in required_statuses) else "缺失"
        lines.append(
            "| {section} | {claim} | `{script}` | `{data}` | `{figure}` | {ppt} | {status} |".format(
                section=item["section"],
                claim=item["claim"],
                script=item["script"] or "-",
                data=item["data"] or "-",
                figure=item["figure"] or "-",
                ppt=item["ppt"],
                status=overall,
            )
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(build_report(), encoding="utf-8")
    print(REPORT_PATH)


if __name__ == "__main__":
    main()
