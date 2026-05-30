# 章节架构

## Required chapter files

- `chapters/00_Abstract.md` | min_chars=1800 | owner=controller | placeholders=no
- `chapters/01_Introduction.md` | min_chars=8000 | owner=chapter-agent-or-confirmed-single-agent | placeholders=no
- `chapters/02_Physical_Model_and_Numerical_Method.md` | min_chars=9000 | owner=chapter-agent-or-confirmed-single-agent | placeholders=no
- `chapters/03_Dataset_Construction.md` | min_chars=8000 | owner=chapter-agent-or-confirmed-single-agent | placeholders=no
- `chapters/04_Multimodal_CNN_Model.md` | min_chars=9000 | owner=chapter-agent-or-confirmed-single-agent | placeholders=no
- `chapters/05_Optimization_and_CFD_Verification.md` | min_chars=9000 | owner=chapter-agent-or-confirmed-single-agent | placeholders=no
- `chapters/06_Conclusion_and_Outlook.md` | min_chars=3500 | owner=controller | placeholders=no

## 章节角色

- 第1章负责把工程背景、文献现状、研究空白和本文任务链条讲清楚。
- 第2章负责定义物理对象、几何参数、控制方程、边界条件、网格和指标。
- 第3章负责说明样本设计、批量仿真、数据集组织和典型流热特征。
- 第4章负责说明多模态 CNN/CBAM 代理模型、训练方案、结果与消融。
- 第5章负责说明差分进化优化、最优构型、CFD 复核和物理机理。
- 第6章负责收束贡献、局限和后续工作。

## 写作硬约束

- 不编造文献、数据、图表和实验结果。
- 未核对的数据只能标记为“待核对”，不得写成确定结论。
- 每章正文以段落论证为主，避免把任务说明写进论文正文。
- 所有图表必须在 `figures/data-manifest.md` 或图表清单中登记来源。
- 全文术语保持一致：参数化拓扑优化、代理模型、CFD 复核、流热耦合、翼型管阵列。

## 当前限制

本环境支持子代理工具，但系统规则要求只有用户明确要求“多代理/并行代理”时才可启用。若用户确认使用多代理，我会按本 skill 的 full-paper gate 为主要章节分派独立章节代理；否则采用单代理降级流程，并在 `plan/progress.md` 中记录。
