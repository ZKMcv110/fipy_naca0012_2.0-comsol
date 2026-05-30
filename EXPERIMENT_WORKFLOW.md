# 实验运行手册

本文档用于记录本项目从 COMSOL 数据生成、标签重建、模型训练到论文图生成的推荐流程。

目标是避免后续重新跑数据、改模型或补论文结果时出现数据覆盖、标签错配、训练集不一致、论文指标来源不清等问题。

## 1. 总体流程

```text
参数设计空间
-> LHS 采样
-> COMSOL 批量仿真
-> case_*_cfd_solution/result.json 与三类场图
-> 重建 consol_cfddata/labels.csv
-> 检查数据完整性
-> CNN / MLP / 多模态模型训练
-> ai_cnn_model_results/
-> 论文表格与论文图生成
```

核心证据链：

```text
consol_cfddata/case_*/result.json
-> consol_cfddata/labels.csv
-> ai_cnn_model_results/*.json / *.csv / *.pth / *.joblib
-> paper_figures_svg/
```

## 2. 重跑前必须确认

重跑数据或模型前，先确认是否需要备份下面这些目录：

```text
consol_cfddata/
csv_data/
ai_cnn_model_results/
paper_figures_svg/
```

其中：

- `consol_cfddata/` 是 COMSOL case 原始结果，重建成本最高。
- `csv_data/` 保存批量仿真的结果表。
- `ai_cnn_model_results/` 保存模型权重、预测结果和论文表格。
- `paper_figures_svg/` 保存当前论文图输出。

如果当前结果已经写进论文，建议先复制归档，再重新实验。

## 3. 小样本试跑

不要一上来直接跑 500 组。推荐先跑 3 组确认流程正常：

```powershell
.\myenvs_fipynaca2.0\Scripts\python.exe consol500组参数.py --num-samples 3
```

成功标志：

```text
consol_cfddata/case_1_cfd_solution/
consol_cfddata/case_2_cfd_solution/
consol_cfddata/case_3_cfd_solution/
csv_data/final_results.csv
```

每个 case 里应至少有：

```text
velocity_magnitude.png
pressure.png
temperature.png
result.json
```

如果小样本失败，不要继续跑 500 组。

## 4. 正式批量 COMSOL 仿真

确认小样本正常后，再跑正式数据：

```powershell
.\myenvs_fipynaca2.0\Scripts\python.exe consol500组参数.py --num-samples 500
```

默认输出：

```text
consol_cfddata/case_*_cfd_solution/
csv_data/final_results.csv
```

注意：该脚本会重新写入 `csv_data/final_results.csv`，重跑前请确认旧结果是否已经备份。

## 5. 重建标签文件

正式训练前，推荐从每个 case 的 `result.json` 重建统一标签：

```powershell
.\myenvs_fipynaca2.0\Scripts\python.exe .\data_processing\rebuild_labels_from_results.py
```

生成：

```text
consol_cfddata/labels.csv
```

如果只是检查，不想覆盖标签，可以先 dry-run：

```powershell
.\myenvs_fipynaca2.0\Scripts\python.exe .\data_processing\rebuild_labels_from_results.py --dry-run
```

成功标志：

```text
Valid cases: 500
Wrote labels: consol_cfddata/labels.csv
```

## 6. 检查数据完整性

重建标签后必须检查图像是否完整：

```powershell
.\myenvs_fipynaca2.0\Scripts\python.exe .\data_processing\check_dataset_integrity.py
```

理想结果：

```text
有效行数 = 500
图像完整的案例数 = 500
缺失图像的案例数 = 0
```

如果有缺图，先处理缺失 case，不要直接训练。

## 7. 训练 CNN

CNN 使用：

```text
consol_cfddata/labels.csv
consol_cfddata/case_*/velocity_magnitude.png
consol_cfddata/case_*/pressure.png
consol_cfddata/case_*/temperature.png
```

训练命令：

```powershell
.\myenvs_fipynaca2.0\Scripts\python.exe cnnstep2.py
```

主要输出：

```text
ai_cnn_model_results/best_model.pth
ai_cnn_model_results/cfd_cnn_model.pth
ai_cnn_model_results/dataset_stats.json
ai_cnn_model_results/dataset_split.csv
ai_cnn_model_results/metrics.json
ai_cnn_model_results/test_predictions.csv
ai_cnn_model_results/paper_table7_metrics.csv
ai_cnn_model_results/paper_table7_metrics.md
ai_cnn_model_results/final_prediction.png
```

只想重新评估已有 CNN 模型，不重新训练：

```powershell
.\myenvs_fipynaca2.0\Scripts\python.exe cnnstep2.py --eval-only
```

## 8. 单 case CNN 预测

按已有 case 预测：

```powershell
.\myenvs_fipynaca2.0\Scripts\python.exe cnnstep3.py --case_id 1
```

输出：

```text
ai_cnn_model_results/current_prediction_visual.png
```

如果手动输入参数：

```powershell
.\myenvs_fipynaca2.0\Scripts\python.exe cnnstep3.py --manual --Ta 0.02 --Twa 0.4 --Tb 0.12 --Ts 1.0 --Tt 0.8 --Tad 0.5
```

手动参数应尽量落在训练数据范围内。

## 9. 训练 MLP 基线

MLP 只使用 6 个几何/排布参数：

```text
Ta, Twa, Tb, Ts, Tt, Tad
```

训练命令：

```powershell
.\myenvs_fipynaca2.0\Scripts\python.exe train_mlp_baseline.py
```

主要输出：

```text
ai_cnn_model_results/mlp_baseline_model.pth
ai_cnn_model_results/mlp_baseline_metrics.json
ai_cnn_model_results/mlp_baseline_predictions.csv
ai_cnn_model_results/mlp_baseline_history.csv
ai_cnn_model_results/mlp_baseline_table8_rows.csv
```

注意：MLP 默认复用 `ai_cnn_model_results/dataset_split.csv`，这样可以保证和 CNN 使用同一测试集。

## 10. 训练多模态模型

多模态模型使用：

```text
几何参数 + CFD 场图特征
```

训练命令：

```powershell
.\myenvs_fipynaca2.0\Scripts\python.exe train_multimodal_feature_model.py
```

主要输出：

```text
ai_cnn_model_results/multimodal_feature_model.joblib
ai_cnn_model_results/multimodal_feature_metrics.json
ai_cnn_model_results/multimodal_feature_predictions.csv
ai_cnn_model_results/paper_table8_model_comparison.csv
ai_cnn_model_results/paper_table8_model_comparison.md
```

注意：多模态模型也默认复用 `dataset_split.csv`，保证对比公平。

## 11. 生成论文图

统一入口：

```powershell
.\myenvs_fipynaca2.0\Scripts\python.exe .\comsol论文图脚本\generate_comsol_svgs.py
```

只生成某一类：

```powershell
.\myenvs_fipynaca2.0\Scripts\python.exe .\comsol论文图脚本\generate_comsol_svgs.py --only base
.\myenvs_fipynaca2.0\Scripts\python.exe .\comsol论文图脚本\generate_comsol_svgs.py --only cbam
.\myenvs_fipynaca2.0\Scripts\python.exe .\comsol论文图脚本\generate_comsol_svgs.py --only fig8
.\myenvs_fipynaca2.0\Scripts\python.exe .\comsol论文图脚本\generate_comsol_svgs.py --only heat
```

输出：

```text
paper_figures_svg/
```

## 12. 重新实验时的推荐顺序

如果只是改模型，不改 COMSOL 数据：

```text
1. 检查 labels.csv 和图像完整性
2. 保留 dataset_split.csv
3. 重新训练/评估新模型
4. 更新 ai_cnn_model_results/
5. 重新生成论文表格和论文图
```

如果重新跑 COMSOL 数据：

```text
1. 备份旧 consol_cfddata/、csv_data/、ai_cnn_model_results/
2. 小样本试跑 3 个 case
3. 正式跑 500 个 case
4. 重建 labels.csv
5. 检查完整性
6. 重新训练 CNN
7. 重新训练 MLP
8. 重新训练多模态模型
9. 重新生成论文图
10. 记录本次实验版本
```

## 13. 常见风险

### 数据和模型不匹配

不要用新 `labels.csv` 搭配旧 `dataset_stats.json` 或旧 `cfd_cnn_model.pth` 直接报告论文结果。

### 测试集不一致

CNN、MLP、多模态模型比较时，应使用同一个 `dataset_split.csv`。

### 覆盖论文结果

如果某组结果已经写进论文，重跑前先归档旧的：

```text
ai_cnn_model_results/
paper_figures_svg/
```

### 缺图训练

如果有 case 缺少 `velocity_magnitude.png`、`pressure.png` 或 `temperature.png`，不要直接训练。

### COMSOL 重跑成本

COMSOL 批量仿真耗时高，也可能占许可证。正式大批量运行前，必须先小样本试跑。

## 14. 建议记录实验版本

每次正式实验建议记录：

```text
实验日期
样本数
数据目录
labels.csv 生成方式
dataset_split.csv 是否复用
CNN 指标
MLP 指标
多模态模型指标
论文是否采用
备注
```

可以后续新建：

```text
experiments/
```

把每次正式实验的结果和说明单独存档。
