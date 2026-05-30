# 第 5 章蓝图：基于代理模型的参数化拓扑优化与 CFD 复核

## Chapter Role

第 5 章负责把前面章节建立的参数化样本、CFD 数据集和多模态代理模型转化为可执行的结构优化流程。该章不只报告最优参数，还要说明优化目标如何定义、代理模型如何参与搜索、候选构型如何经过 CFD 复核，以及优化前后流热场变化如何解释。

## Paragraph Blueprint

### Paragraph 1

- Role: chapter opening
- Main claim: 仅依赖 CFD 逐点搜索会带来较高计算成本，因此需要代理模型承担快速筛选功能。
- Evidence IDs: J-2023-001, project-code-optimization
- Contrast or transition: 从文献中的 ANN + SQP/NSGA-II 过渡到本文的 CNN/MLP + 差分进化/候选复核。
- Forbidden content: 不得声称本文已经完全复现 Jiang 等的全部工况。

### Paragraph 2

- Role: objective definition
- Main claim: 优化目标应同时考虑强化换热和流动阻力，不能只最大化 Nu。
- Evidence IDs: J-2023-002
- Contrast or transition: 引出本文的 `Nu`、`f` 和综合性能因子。
- Forbidden content: 不得把综合性能因子写成唯一评价标准。

### Paragraph 3

- Role: surrogate workflow
- Main claim: 本文将训练后的代理模型作为目标函数近似器，在参数空间中快速预测候选构型性能。
- Evidence IDs: project-model-results, J-2023-003
- Contrast or transition: 从代理预测转向优化算法。
- Forbidden content: 不得忽略代理模型误差和外推风险。

### Paragraph 4

- Role: optimization search
- Main claim: 优化算法负责在约束范围内搜索候选点，代理模型负责快速评估，二者构成计算成本可控的筛选环节。
- Evidence IDs: J-2023-004, paper-reference-code
- Contrast or transition: 引出 CFD 复核的必要性。
- Forbidden content: 不得把代理模型最优点直接等同于最终物理最优点。

### Paragraph 5

- Role: CFD verification
- Main claim: 代理模型筛选出的优选构型必须重新进行独立 CFD 计算，以验证 Nu、f 和流场结构是否与预测一致。
- Evidence IDs: project-cfd-verification
- Contrast or transition: 从数值误差转向物理机理解释。
- Forbidden content: 不得伪造尚未核对的复核数值。

### Paragraph 6

- Role: mechanism discussion
- Main claim: 优化构型的合理性需要回到速度场、压力场和温度场中解释，而不仅由指标提升证明。
- Evidence IDs: project-field-figures, J-2023-005
- Contrast or transition: 收束到本章贡献。
- Forbidden content: 不得只用定性词汇替代图像或数据证据。
