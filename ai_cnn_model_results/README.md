# AI/CNN 模型结果说明

这个文件夹保存当前 COMSOL/CNN 代理建模流程的训练结果、预测结果、模型对比指标和论文表格数据。

目前不建议随意删除或移动这里的文件，因为 `cnnstep2.py`、`cnnstep3.py`、`train_mlp_baseline.py`、`train_multimodal_feature_model.py` 和 `comsol论文图脚本/generate_paper_svgs.py` 都会直接读取这里的结果。

## 数据来源链条

本文件夹中的模型权重、指标、预测表和论文表格不是手工填写的，而是由下面的数据处理链条生成：

```text
consol500组参数.py
-> comsol单次执行脚本.py
-> consol_cfddata/case_*_cfd_solution/
-> data_processing/rebuild_labels_from_results.py
-> consol_cfddata/labels.csv
-> cnnstep2.py / train_mlp_baseline.py / train_multimodal_feature_model.py
-> ai_cnn_model_results/
```

具体来源如下：

1. `consol500组参数.py` 使用拉丁超立方采样生成 6 个参数的样本组合：

```text
Ta, Twa, Tb, Ts, Tt, Tad
```

2. 每一组参数会调用 `comsol单次执行脚本.py` 自动建立并求解一个 COMSOL case。

3. 每个 case 的原始仿真结果保存在：

```text
consol_cfddata/case_*_cfd_solution/
```

每个 case 通常包含：

```text
velocity_magnitude.png
pressure.png
temperature.png
result.json
result.csv
model.mph
```

4. `data_processing/rebuild_labels_from_results.py` 会扫描每个 case 的 `result.json`，并重建统一标签文件：

```text
consol_cfddata/labels.csv
```

5. `cnnstep2.py` 读取 `labels.csv` 和三类 CFD 场图，训练 CNN，并生成本文件夹中的 CNN 权重、预测结果和 Table 7 指标。

6. `train_mlp_baseline.py` 读取同一个 `labels.csv` 和 `dataset_split.csv`，训练只使用 6 个几何参数的 MLP 基线模型。

7. `train_multimodal_feature_model.py` 读取同一个数据划分，并结合几何参数与 CFD 图像特征，生成多模态融合模型结果和 Table 8 对比表。

因此，本文件夹的可信数据源顺序是：

```text
consol_cfddata/case_*/result.json
-> consol_cfddata/labels.csv
-> ai_cnn_model_results/*.json / *.csv / *.pth / *.joblib
```

## CNN 模型结果

| 文件 | 用途 | 建议 |
|---|---|---|
| `best_model.pth` | 训练过程中验证集最优的 CNN 权重 | 保留 |
| `cfd_cnn_model.pth` | 最终保存的 CNN 权重，预测脚本默认读取 | 保留 |
| `dataset_stats.json` | 参数和目标值的归一化统计量，预测反归一化需要 | 保留 |
| `dataset_split.csv` | 训练/验证/测试集划分，后续 MLP 和多模态对比复用 | 保留 |
| `metrics.json` | CNN 在测试集上的评价指标 | 保留 |
| `test_predictions.csv` | CNN 测试集逐样本预测结果 | 保留 |
| `loss_curve.png` | CNN 训练损失曲线图，也可作为论文图脚本的备用数据源 | 保留 |
| `current_prediction_visual.png` | 单次预测可视化图 | 可保留 |
| `final_prediction.png` | 测试/预测可视化输出 | 可保留 |
| `cnn_training_history_digitized.csv` | 从旧版 `loss_curve.png` 数字化得到的训练曲线数据 | 可保留 |

当前 CNN 指标来自 `metrics.json`：

| Target | R2 | RMSE | MAE | MAPE/% |
|---|---:|---:|---:|---:|
| Nu | 0.9364 | 0.6075 | 0.4856 | 2.788 |
| f | 0.9269 | 0.00119065 | 0.000859 | 2.797 |

## MLP 基线模型

| 文件 | 用途 | 建议 |
|---|---|---|
| `mlp_baseline_model.pth` | 只使用 6 个几何参数训练的 MLP 基线模型 | 保留 |
| `mlp_baseline_metrics.json` | MLP 测试集指标 | 保留 |
| `mlp_baseline_predictions.csv` | MLP 逐样本预测结果 | 保留 |
| `mlp_baseline_history.csv` | MLP 训练历史 | 保留 |
| `mlp_baseline_stats.json` | MLP 输入/输出归一化统计量 | 保留 |
| `mlp_baseline_table8_rows.csv` | 论文 Table 8 中 MLP 部分的行数据 | 保留 |

当前 MLP 指标来自 `mlp_baseline_metrics.json`：

| Target | R2 | RMSE | MAE | MAPE/% |
|---|---:|---:|---:|---:|
| Nu | 0.9701 | 0.4166 | 0.3301 | 1.882 |
| f | 0.9459 | 0.00102392 | 0.000843 | 2.570 |

## 多模态特征融合模型

| 文件 | 用途 | 建议 |
|---|---|---|
| `multimodal_feature_model.joblib` | 几何参数 + CFD场图像统计/空间特征融合模型 | 保留 |
| `multimodal_feature_metrics.json` | 多模态模型测试集指标 | 保留 |
| `multimodal_feature_predictions.csv` | 多模态模型逐样本预测结果，论文散点图优先读取 | 保留 |

当前多模态指标来自 `multimodal_feature_metrics.json`：

| Target | R2 | RMSE | MAE | MAPE/% |
|---|---:|---:|---:|---:|
| Nu | 0.9756 | 0.3765 | 0.2841 | 1.667 |
| f | 0.9633 | 0.00084311 | 0.000549 | 1.753 |

## 论文表格

| 文件 | 用途 | 建议 |
|---|---|---|
| `paper_table7_metrics.csv` | CNN 测试指标表格数据 | 保留 |
| `paper_table7_metrics.md` | CNN 测试指标 Markdown 表格 | 保留 |
| `paper_table8_model_comparison.csv` | MLP 与多模态模型对比表格数据 | 保留 |
| `paper_table8_model_comparison.md` | MLP 与多模态模型对比 Markdown 表格 | 保留 |

`comsol论文图脚本/generate_paper_svgs.py` 会读取 `paper_table8_model_comparison.csv` 生成模型对比图。

## 清理建议

暂时不要删除：

```text
*.pth
*.joblib
dataset_stats.json
dataset_split.csv
metrics.json
*_metrics.json
*_predictions.csv
paper_table*.csv
paper_table*.md
loss_curve.png
```

如果后面要整理内部结构，建议先同步修改相关脚本中的路径，再把文件移动到类似下面的子目录：

```text
ai_cnn_model_results/
├── cnn/
├── mlp_baseline/
├── multimodal_feature/
├── paper_tables/
└── figures/
```

在路径改造之前，保持当前扁平结构最稳。
