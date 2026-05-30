# Task Packet 002：将 Jiang 等 2023 文献转化为本文方法依据

## Scope

将用户提供的 PCHE 翼形翅片机器学习优化论文纳入本文大论文写作体系，形成可追踪的文献笔记、证据映射、章节蓝图和第 5 章方法草稿。当前任务不改动任何原始仿真、训练或优化脚本。

## Files to Read

- `paper_reference/extracted/pche_airfoil_nn_optimization_text.txt`
- `paper_reference/README.md`
- `paper_reference/src/pche_reference/*.py`
- `thesis_writing/plan/outline.md`
- `thesis_writing/plan/chapter-architecture.md`
- `thesis_writing/refs/evidence-map.md`
- `thesis_writing/chapters/05_Optimization_and_CFD_Verification.md`

## Files Allowed to Edit

- `thesis_writing/refs/jiang2023_pche_airfoil_ml_note.md`
- `thesis_writing/plan/chapter-blueprints/05_Optimization_and_CFD_Verification_blueprint.md`
- `thesis_writing/plan/review/evidence-coverage-jiang2023.md`
- `thesis_writing/chapters/05_Optimization_and_CFD_Verification.md`
- `thesis_writing/plan/progress.md`

## Required Skills

- paper-orchestration
- evidence-driven-writing
- writing-chapters
- writing-core

## Required Artifacts

- 文献笔记：`refs/jiang2023_pche_airfoil_ml_note.md`
- 第 5 章蓝图：`plan/chapter-blueprints/05_Optimization_and_CFD_Verification_blueprint.md`
- 证据覆盖检查：`plan/review/evidence-coverage-jiang2023.md`
- 第 5 章方法草稿：`chapters/05_Optimization_and_CFD_Verification.md`
- 进度记录：`plan/progress.md`

## Rejection Checks

- 不得把文献中的最优参数或提升百分比写成本研究结果。
- 不得伪造本文尚未完成的 CFD 复核结果。
- 正文必须说明文献方法与本文方法的迁移关系，而不是简单复述文献摘要。
- 第 5 章草稿必须按照“输入参数、代理预测、目标函数、优化搜索、CFD 复核、机理解释”的技术流组织。

## Validation Commands

```powershell
python .\paper_reference\run_reference_optimization.py --side cold --samples 1500 --out paper_reference\reference_optimization_cold.json
python .\paper_reference\run_reference_optimization.py --side hot --samples 1500 --out paper_reference\reference_optimization_hot.json
```
