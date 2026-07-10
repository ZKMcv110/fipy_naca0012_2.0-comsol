# 参数敏感性分析结果

## 方法

- Pearson/Spearman 相关性：基于 1000 组 CFD 标签。
- 随机森林重要性：基于七参数对 Nu、f、eta 的统计解释。
- 局部扰动：在 DE 最优点附近单参数扰动，使用当前 MLP-CNN 代理模型预测 eta。

## eta 的随机森林重要性前三

- Ts: permutation importance = 1.361628
- theta: permutation importance = 0.231464
- Tb: permutation importance = 0.147826

## eta 的局部扰动敏感性前三

- Ts: eta_range = 0.044242
- Tb: eta_range = 0.017418
- theta: eta_range = 0.014892

## 结论边界

该结果可用于解释当前样本分布和代理模型最优点附近的参数影响趋势；不能替代严格的 CFD 单因素扫描。
