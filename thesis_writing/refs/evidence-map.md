# Evidence Map

本文件用于登记论文中的文献、数据、图表和关键结论。当前先建立空表，后续写章节时逐条补齐。

## 关键结论核查表

| ID | 结论/数据 | 当前来源 | 状态 | 备注 |
|---|---|---|---|---|
| E-001 | 有效样本数量为 500 组 | `academic_pre_review_committee_loaded.md` | 待核对 | 需对应 CSV 和结果目录 |
| E-002 | Nu 预测 R2 达到 0.987 | `academic_pre_review_committee_loaded.md` | 待核对 | 需对应训练日志或结果表 |
| E-003 | 优化方案综合评价因子提升 24.5% | `academic_pre_review_committee_loaded.md` | 待核对 | 需对应 CFD 复核数据 |
| E-004 | 采用 NACA 参数化翼型管阵列 | 项目代码与草稿 | 待核对 | 需统一 Ta/Twa/Tb/Ts/Tt/Tad 定义 |
| E-005 | Jiang 风格标量 ANN 在测试集上达到 Nu R2=0.9901、f R2=0.9690 | `paper_reference/jiang_style_ann_results/ann_metrics.json` | 已生成，待论文终稿复核 | 作为第5章代理优化基线，不替代多模态模型 |
| E-006 | 标量 ANN 最大综合性能候选点 eta_pred=1.2005 | `paper_reference/jiang_style_ann_results/ann_optimization_candidates.csv` | 代理预测，待 CFD 复核 | 不得写成最终性能提升结论 |
| E-007 | 已建立用户参数驱动的三维冷热双通道 PCHE 参考案例 dry-run 计划 | `paper_reference/jiang_3d_pche_case/dry_run_case/model_plan.json` | 已生成，待 COMSOL 实体建模与求解 | 使用 Ta/Twa/Tb/Ts/Tt/Tad，不直接复现 Jiang 的 Lt/Ls/Wa/delta |
| E-008 | 已生成三维冷热 PCHE 翼形翅片 STL 几何资产 | `paper_reference/jiang_3d_pche_case/dry_run_case/*.stl` | 已生成，待 COMSOL 导入验证 | 冷侧 24000 facets，热侧 24000 facets，总计 48000 facets |
| E-009 | 已生成用户参数驱动三维冷热 PCHE COMSOL skeleton 模型 | `paper_reference/jiang_3d_pche_case/comsol_build_case/user_param_jiang3d_pche_skeleton.mph` | 已生成，待边界/物理场细化求解 | 包含冷热通道 block、SS316 隔板、STL 翅片导入入口、传热物理场和 Stationary study |
| E-010 | 已生成用户参数驱动三维冷热 PCHE COMSOL configured 模型 | `paper_reference/jiang_3d_pche_case/comsol_configured_case_v2/user_param_jiang3d_pche_configured.mph` | 已生成，待人工检查后求解 | 包含冷热独立流体材料、冷热独立 Laminar Flow、传热入口出口、Box selections、网格和 Stationary study |
| E-011 | 三维冷热 PCHE 全尺寸粗网格案例已完成 Stationary solve | `paper_reference/jiang_3d_pche_case/comsol_full_solve_case/solve_status.json` | 已跑通，待高保真复核 | 10 排 x 3 列，mesh_hauto=7，占位流体物性，不能直接作为最终性能结论 |
| E-012 | 三维冷热 PCHE 全尺寸粗网格案例已输出温度、压力和压降摘要 | `paper_reference/jiang_3d_pche_case/comsol_full_solve_case/result_summary.json` | 已生成，待物理口径复核 | 当前为自动边界平均和估算 f，后续需替换为严格 Nu_c/f_c/Nu_h/f_h 后处理 |
| E-013 | 三维冷热 PCHE 全尺寸粗网格案例已导出温度、压力和速度云图 | `paper_reference/jiang_3d_pche_case/comsol_full_solve_case/result_exports/` | 已生成 | 包含 slice 和 surface 两组 PNG，COMSOL 默认视角较远，后续可在 `.mph` 内调整视角 |

## 文献登记表

| Ref ID | 文献信息 | 支撑位置 | 状态 |
|---|---|---|---|
| R-001 | 待补充 | 第1章研究现状 | 待补充 |
| J-2023 | Jiang T, Li M-J, Yang J-Q. Research on optimization of structural parameters for airfoil fin PCHE based on machine learning. Applied Thermal Engineering, 2023, 229: 120498. | 第1章研究现状；第3章样本设计；第5章优化目标与代理优化流程 | 已提取全文并形成文献笔记 |

## 图表登记表

| Figure/Table ID | 名称 | 文件路径 | 支撑章节 | 状态 |
|---|---|---|---|---|
| Fig-001 | 参数化几何示意图 | `paper_figures_svg/` | 第2章 | 待核对 |
| Fig-002 | 数据生成、代理模型训练与 CFD 复核流程 | `paper_figures_svg/Fig2_Workflow.svg` | 第3章/第5章 | 待核对 |
| Fig-003 | Jiang 风格 ANN 测试集预测散点图 | `paper_reference/jiang_style_ann_results/ann_prediction_scatter.png` | 第5章 | 已生成 |
| Fig-004 | 用户参数驱动三维冷热 PCHE 参考案例几何计划 | `paper_reference/jiang_3d_pche_case/dry_run_case/model_plan.json` | 第2章/第5章 | dry-run 已生成，待转几何图 |
| Fig-005 | 用户参数驱动三维冷热 PCHE 参考案例预览图 | `paper_reference/jiang_3d_pche_case/dry_run_case/geometry_preview.png` | 第2章/第5章 | 已生成 |
| Fig-006 | 三维冷热 PCHE 温度切片云图 | `paper_reference/jiang_3d_pche_case/comsol_full_solve_case/result_exports/temperature_slice.png` | 第5章 | 已导出 |
| Fig-007 | 三维冷热 PCHE 冷/热侧压力与速度云图 | `paper_reference/jiang_3d_pche_case/comsol_full_solve_case/result_exports/*pressure*.png`, `*velocity*.png` | 第5章 | 已导出 |
