# 七参数参数-几何掩码代理优化流程

本目录是新增流程，不修改旧的六参数脚本、旧数据、旧模型权重和旧结果。旧流程可继续作为历史结果和对照结果使用。

## 核心思路

新流程仍然是多模态模型，但输入不再使用 CFD 云图。模型输入为：

- 参数模态：`Ta, Twa, Tb, Ts, Tt, Tad, theta`
- 几何图像模态：由七参数直接生成的翼型阵列二值几何掩码图

因此差分进化优化阶段不需要调用 COMSOL，也不需要速度、压力、温度云图。COMSOL 只用于生成训练标签和最终复核。

## 文件说明

- `common.py`：七参数范围、NACA 几何、掩码生成、归一化和性能指标工具。
- `01_七参数LHS采样.py`：生成七参数 LHS 样本。
- `02_七参数COMSOL批量求解.py`：批量调用七参数 COMSOL 单工况脚本，支持断点续算和失败记录。
- `02a_七参数COMSOL单工况求解.py`：从旧单工况脚本复制改造的七参数二维 COMSOL 求解脚本，新增 `theta` 翼型整体倾斜角。
- `03_从COMSOL结果重建标签.py`：从 COMSOL 结果或旧 `labels.csv` 重建 `labels_7param.csv`。
- `04_生成几何掩码图.py`：由参数直接生成 `case_x_mask.png`。
- `05_训练参数_几何掩码代理模型.py`：训练 CNN/MLP 融合代理模型，默认使用本目录 `samples/dataset_split_7param.csv`，不读取旧六参数结果目录的划分文件。
- `06_预测单组七参数性能.py`：输入七参数，输出 `Nu_pred, f_pred, eta_pred`；默认从本目录 `samples/labels_7param.csv` 中寻找最接近预设基准构型的参考样本，并读取其 `Nu0/f0` 计算 `eta`。
- `07_差分进化优化七参数.py`：用代理模型作为目标函数进行七参数差分进化优化。
- `08_COMSOL复核最优结构.py`：将代理模型找到的最优结构回到 COMSOL 复核。
- `09_消融实验_PI_CNN_CBAM.py`：训练 MLP、几何 CNN、普通融合模型、PI-CNN-CBAM 融合模型，并输出消融实验表格和图；默认使用本目录 `samples/dataset_split_7param.csv`。
- `10_预测_PI_CNN_CBAM性能.py`：调用消融实验中训练出的 PI-CNN-CBAM 几何掩码模型进行单点预测；默认从本目录 `samples/labels_7param.csv` 中寻找最接近预设基准构型的参考样本，并读取其 `Nu0/f0` 计算 `eta`。
- `11_差分进化优化_PI_CNN_CBAM七参数.py`：调用 PI-CNN-CBAM 几何掩码模型进行差分进化优化。
- `12_七参数PI_CNN_CBAM_K折验证.py`：对七参数 PI-CNN-CBAM 几何掩码模型进行 K 折交叉验证，输出每折指标、均值和标准差。
- `13_七参数项目完整性检查.py`：不调用 COMSOL、不训练模型，只读检查标签、消融、K折、优化、复核、三维结果、七参数脚本、三维正式脚本、旧六参数保护资产、论文图片、图表编号、关键表述、参考文献统计和剩余工作清单。
- `14_生成非零theta补充样本.py`：生成非零 `theta` 的补充样本清单，用于后续 COMSOL 补跑真实七参数标签；不修改现有 `labels_7param.csv`。
- `15_合并theta补充标签.py`：将基础 `labels_7param.csv` 与非零 `theta` 补跑结果安全合并到新标签文件，默认不覆盖旧标签。
- `16_非零theta补充统计.py`：统计非零 `theta` 补跑结果的参数范围、性能范围和相关性，只用于补样质量检查。
- `17_合并theta轻量重训评估.py`：使用合并标签做轻量重训评估，判断少量非零 `theta` 样本是否改善倾斜角构型预测；不替代正式消融实验和K折验证。
- `18_七参数轻量冒烟测试.py`：验证预测、采样、标签重建、掩码生成、优化和复核脚本入口；不训练模型、不运行COMSOL。

## 推荐运行顺序

### 1. 生成七参数样本

```powershell
python "七参数_几何掩码代理优化\01_七参数LHS采样.py" --num-samples 100
```

输出：

```text
七参数_几何掩码代理优化/samples/samples_7param.csv
```

### 2. 批量 COMSOL 求解

```powershell
python "七参数_几何掩码代理优化\02_七参数COMSOL批量求解.py" --samples "七参数_几何掩码代理优化\samples\samples_7param.csv"
```

输出：

```text
七参数_几何掩码代理优化/comsol_results/case_x/result.json
七参数_几何掩码代理优化/comsol_results/case_x/cfd_solution/*.png
七参数_几何掩码代理优化/comsol_results/summary.csv
```

### 3. 重建标签

```powershell
python "七参数_几何掩码代理优化\03_从COMSOL结果重建标签.py" --mode results
```

调试阶段也可以把旧六参数标签临时扩展为 `theta=0`：

```powershell
python "七参数_几何掩码代理优化\03_从COMSOL结果重建标签.py" --mode existing
```

注意：`--mode existing` 只能用于验证程序链路，不能证明 theta 参数的真实物理影响。

### 4. 生成几何掩码图

```powershell
python "七参数_几何掩码代理优化\04_生成几何掩码图.py"
```

输出：

```text
七参数_几何掩码代理优化/masks/case_x_mask.png
```

当前消融实验与基础训练脚本默认使用本目录内的固定划分文件：

```text
七参数_几何掩码代理优化/samples/dataset_split_7param.csv
```

该文件用于保证不同模型采用一致的训练集、验证集和测试集划分，不依赖旧六参数目录。

### 5. 训练代理模型

```powershell
python "七参数_几何掩码代理优化\05_训练参数_几何掩码代理模型.py" --epochs 100 --batch-size 32
```

输出：

```text
七参数_几何掩码代理优化/models/best_model.pth
七参数_几何掩码代理优化/models/stats.json
七参数_几何掩码代理优化/models/metrics.json
七参数_几何掩码代理优化/models/train_history.csv
七参数_几何掩码代理优化/models/test_predictions.csv
```

### 6. 单组参数预测

```powershell
python "七参数_几何掩码代理优化\06_预测单组七参数性能.py" --Ta 0.03 --Twa 0.4 --Tb 0.12 --Ts 1.1 --Tt 0.85 --Tad 0.3 --theta 5
```

该脚本默认使用 `samples/labels_7param.csv` 中最接近预设基准构型的参考样本计算 `eta` 的基准 `Nu0/f0`；如需复现实验中的特定基准值，可手动传入 `--Nu0` 和 `--f0`。

### 7. 差分进化优化

```powershell
python "七参数_几何掩码代理优化\07_差分进化优化七参数.py" --pop-size 32 --generations 30
```

输出：

```text
七参数_几何掩码代理优化/optimization_results/best_params.json
七参数_几何掩码代理优化/optimization_results/de_history.csv
七参数_几何掩码代理优化/optimization_results/de_convergence.png
```

### 8. PI-CNN-CBAM 消融实验与优化

```powershell
python "七参数_几何掩码代理优化\09_消融实验_PI_CNN_CBAM.py" --epochs 30 --batch-size 64 --image-size 64
python "七参数_几何掩码代理优化\10_预测_PI_CNN_CBAM性能.py"
python "七参数_几何掩码代理优化\11_差分进化优化_PI_CNN_CBAM七参数.py" --pop-size 32 --generations 30
```

输出：

```text
七参数_几何掩码代理优化/ablation_results/ablation_summary.csv
七参数_几何掩码代理优化/ablation_results/ablation_bar.png
七参数_几何掩码代理优化/optimization_results_pi_cbam/best_params.json
七参数_几何掩码代理优化/optimization_results_pi_cbam/de_convergence.png
```

当前 `labels_7param.csv` 中 `theta` 只有 0，因此 `11_差分进化优化_PI_CNN_CBAM七参数.py` 会自动固定 `theta=0`，避免模型在未训练的倾斜角维度上外推。要做真实七参数全空间优化，必须先用 COMSOL 生成包含非零 `theta` 的样本标签。

`10_预测_PI_CNN_CBAM性能.py` 默认使用 `samples/labels_7param.csv` 中最接近预设基准构型的参考样本计算 `eta` 的基准 `Nu0/f0`；如需复现实验中的特定基准值，可手动传入 `--Nu0` 和 `--f0`。

### 9. COMSOL 复核最优结构

```powershell
python "七参数_几何掩码代理优化\08_COMSOL复核最优结构.py"
```

复核 PI-CNN-CBAM 优化结果：

```powershell
python "七参数_几何掩码代理优化\08_COMSOL复核最优结构.py" --best "七参数_几何掩码代理优化\optimization_results_pi_cbam\best_params.json" --output-dir "七参数_几何掩码代理优化\validation_results_pi_cbam"
```

输出：

```text
七参数_几何掩码代理优化/validation_results/final_validation_report.md
七参数_几何掩码代理优化/validation_results/final_validation_report.json
```

### 10. 七参数 PI-CNN-CBAM K 折交叉验证

```powershell
python "七参数_几何掩码代理优化\12_七参数PI_CNN_CBAM_K折验证.py" --k-folds 5 --epochs 30 --batch-size 64 --image-size 64
```

输出：

```text
七参数_几何掩码代理优化/kfold_results/kfold_metrics.csv
七参数_几何掩码代理优化/kfold_results/kfold_summary.json
七参数_几何掩码代理优化/kfold_results/kfold_summary.md
```

该结果用于补强小样本条件下的泛化稳定性说明。若未运行该脚本，不应在论文中写入七参数 PI-CNN-CBAM 的 K 折交叉验证结论。

### 11. 项目完整性检查

```powershell
python "七参数_几何掩码代理优化\13_七参数项目完整性检查.py"
```

输出：

```text
七参数_几何掩码代理优化/audit_results/integrity_report.json
七参数_几何掩码代理优化/audit_results/integrity_report.md
七参数_几何掩码代理优化/audit_results/figure_table_trace.csv
七参数_几何掩码代理优化/audit_results/smoke_test_results.json
```

该脚本只读取已有文件，不调用 COMSOL、不训练模型，也不会修改旧六参数代码或结果。当前审计范围包括：

- 七参数流程脚本、三维正式脚本和旧六参数入口脚本是否存在并通过语法检查；
- 七参数预测、采样、标签重建、掩码生成、优化和复核脚本入口是否通过轻量冒烟测试；
- 旧六参数 `labels.csv`、模型权重和 `consol_cfddata` 目录是否仍存在；
- 七参数标签、数据划分、消融实验、K折验证、差分进化优化、COMSOL复核和三维汇总结果是否存在；
- 三维非零 `theta` 候选模型是否存在，并检查其建模记录中的网格生成、图组创建、网格失败项、求解器设置失败项和几何预览图有效性；
- `Nu0/f0` 是否来自 `labels_7param.csv` 中最接近预设基准构型的参考样本，并与优化记录一致；
- 论文图片是否缺失、图片来源是否可追溯、图题和表题编号是否重复或断号；
- 论文中二维复核、三维验证和消融实验的关键数值是否能匹配真实 JSON/CSV 结果；
- 论文是否保留“不依赖CFD云图”“theta=0”“分箱均值趋势”“三维不能写成综合最优”等关键限制表述；
- 根据当前警告自动生成剩余工作清单；
- 导出 `figure_table_trace.csv`，记录论文每张图和每个表的题名、引用路径、来源分类和证据文件。

### 12. 生成非零 theta 补充样本

```powershell
python "七参数_几何掩码代理优化\14_生成非零theta补充样本.py" --num-samples 60
```

输出：

```text
七参数_几何掩码代理优化/samples/samples_7param_theta_supplement.csv
```

该文件只表示“待补跑”的非零倾斜角样本输入，不是训练标签。生成后可用批量调度脚本单独求解：

正式求解前建议先做 dry-run，只生成调度计划，不调用 COMSOL：

```powershell
python "七参数_几何掩码代理优化\02_七参数COMSOL批量求解.py" `
  --samples "七参数_几何掩码代理优化\samples\samples_7param_theta_supplement.csv" `
  --output-dir "七参数_几何掩码代理优化\comsol_results_theta_supplement" `
  --dry-run
```

dry-run 输出：

```text
七参数_几何掩码代理优化/comsol_results_theta_supplement/dry_run_plan.csv
```

确认计划无误后再正式求解：

```powershell
python "七参数_几何掩码代理优化\02_七参数COMSOL批量求解.py" `
  --samples "七参数_几何掩码代理优化\samples\samples_7param_theta_supplement.csv" `
  --output-dir "七参数_几何掩码代理优化\comsol_results_theta_supplement"
```

建议先小批量试跑，确认COMSOL几何、网格、求解和导图都正常后再跑全部样本：

```powershell
python "七参数_几何掩码代理优化\02_七参数COMSOL批量求解.py" `
  --samples "七参数_几何掩码代理优化\samples\samples_7param_theta_supplement.csv" `
  --output-dir "七参数_几何掩码代理优化\comsol_results_theta_supplement" `
  --start-index 0 `
  --limit 3
```

`--start-index` 表示从样本表第几行开始，`--limit` 表示本次最多调度多少行。二者配合使用可以分批补跑，例如第二批可使用 `--start-index 3 --limit 3`。

完成COMSOL补跑并检查结果无误后，再使用 `03_从COMSOL结果重建标签.py --mode results` 指定新的结果目录和输出文件，避免覆盖当前正式 `labels_7param.csv`。

也可以使用安全合并脚本将当前500组基础标签与补跑成功结果合并到新文件：

```powershell
python "七参数_几何掩码代理优化\15_合并theta补充标签.py" `
  --results-dir "七参数_几何掩码代理优化\comsol_results_theta_supplement" `
  --output "七参数_几何掩码代理优化\samples\labels_7param_with_theta_supplement.csv"
```

如果补跑结果目录为空，脚本会报错退出，不会生成合并标签。

### 13. 非零 theta 补充统计与轻量评估

补跑完成并合并标签后，可以先统计非零 `theta` 样本覆盖范围：

```powershell
python "七参数_几何掩码代理优化\16_非零theta补充统计.py"
```

输出：

```text
七参数_几何掩码代理优化/comsol_results_theta_supplement/theta_supplement_stats.json
七参数_几何掩码代理优化/comsol_results_theta_supplement/theta_supplement_stats.md
```

然后进行轻量重训评估：

```powershell
python "七参数_几何掩码代理优化\17_合并theta轻量重训评估.py"
```

输出：

```text
七参数_几何掩码代理优化/theta_retrain_eval/theta_retrain_eval_summary.json
七参数_几何掩码代理优化/theta_retrain_eval/theta_retrain_eval_summary.md
```

注意：该评估只用于判断非零 `theta` 补样是否有价值。当前非零 `theta` 成功样本只有35组，不能替代正式全七参数训练、K折验证和差分进化优化。

## 论文中建议表述

本文构建参数-几何图像双模态代理模型，其中参数分支用于表征翼型外形与阵列排布的数值设计变量，图像分支用于提取参数化几何掩码中的空间排布特征。该模型输入不依赖 CFD 计算得到的流场云图，因此可在优化过程中快速预测 Nu 和 f，并作为差分进化算法的适应度评价模型。CFD 云图主要用于对比分析和机理解释，COMSOL 计算用于样本标签生成及最终优化结构复核。

当前 PI-CNN-CBAM 几何掩码模型已加入 CBAM 注意力和物理约束项，可表述为：本文进一步在参数-几何掩码融合代理模型中引入 CBAM 注意力机制和基于 Nu、f、eta 关系的物理一致性约束，形成适用于优化阶段的 PI-CNN-CBAM 几何掩码代理模型。
