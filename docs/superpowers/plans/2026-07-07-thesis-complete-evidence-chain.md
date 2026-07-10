# 七参数 MLP-CNN 流热场重建论文完整证据链 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 完成七参数翼型柱阵列散热器论文的完整实验、证据链、论文正文和答辩材料，使论文能清楚说明建模、数据、代理模型、K 折、敏感性、网格无关、消融、优化、二维 CFD 复算和三维迁移验证。

**Architecture:** 以当前 `p/U/T` 三通道 PVT 高分辨率流热场重建作为论文主线，旧 `u/v/p/T` 四通道 MLP-CNN 只作为历史对照和已完成 DE 复算证据。所有结论必须能追溯到真实脚本、JSON、CSV、图片或 COMSOL 导出结果；不能把未训练的注意力、PINN、完整 PDE 残差写成已完成实验。

**Tech Stack:** Python、NumPy、Pandas、PyTorch、Matplotlib、scikit-learn、COMSOL Java/MPh 结果导出、Markdown 论文、PowerPoint/PPTX。

---

## 文件责任边界

- `七参数_MLP_CNN流场重建/01_构建流场数据集.py`：从 COMSOL 规则采样 `.npz` 构建 PVT 数据集。
- `七参数_MLP_CNN流场重建/08_UNet高精度流场重建训练.py`：训练 PVT Conditional U-Net 主模型。
- `七参数_MLP_CNN流场重建/12_批量导出PVT云图.py`：导出论文用 `p/U/T` COMSOL 风格云图。
- `七参数_MLP_CNN流场重建/13_PVT_K折验证.py`：新增，执行 PVT 主模型 K 折验证。
- `七参数_MLP_CNN流场重建/14_PVT消融实验.py`：新增，统一运行场监督、梯度损失、坐标通道、区域指示等消融。
- `七参数_MLP_CNN流场重建/15_网格无关性汇总.py`：新增，汇总二维 CFD 和三维模型的网格无关性证据。
- `七参数_MLP_CNN流场重建/16_论文证据链汇总.py`：新增，生成论文证据链总表。
- `七参数_MLP_CNN流场重建/analysis_results/sensitivity/`：保存参数敏感性图表和 JSON。
- `七参数_MLP_CNN流场重建/results/`：保存模型训练、K 折、消融、导图结果。
- `七参数_MLP_CNN流场重建/reports/论文证据链总表.md`：新增，所有实验路径、指标、图表编号的总索引。
- `大论文初稿/基于MLP-CNN流热场重建代理模型的翼型柱阵列散热器优化研究.md`：最终论文正文。
- `七参数_几何掩码代理优化/ppt模版/毕业答辩PPT_final.pptx`：答辩 PPT 参考模板。

---

### Task 1: 建立论文总证据链索引

**Files:**
- Create: `七参数_MLP_CNN流场重建/16_论文证据链汇总.py`
- Create: `七参数_MLP_CNN流场重建/reports/论文证据链总表.md`
- Modify: `大论文初稿/基于MLP-CNN流热场重建代理模型的翼型柱阵列散热器优化研究.md`

- [ ] **Step 1: 写证据链脚本**

创建 `16_论文证据链汇总.py`，读取以下固定路径并检查文件存在：

```python
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

EVIDENCE = [
    ("PVT 全量数据集", ROOT / "七参数_MLP_CNN流场重建/data/field_reconstruction_dataset_320x96_full_pUt.npz"),
    ("PVT 主模型指标", ROOT / "七参数_MLP_CNN流场重建/results/unet_pUt_320x96_full_e50/metrics.json"),
    ("PVT COMSOL 风格导图", ROOT / "七参数_MLP_CNN流场重建/results/pvt_comsol_style_exports_pUt_full_e50_case20040"),
    ("二维 DE 最优参数", ROOT / "七参数_MLP_CNN流场重建/optimization_results/mlp_cnn_de_multiloss_e10/best_params.json"),
    ("二维 CFD 复算", ROOT / "七参数_MLP_CNN流场重建/validation_results/mlp_cnn_de_multiloss_e10/final_validation_report.json"),
    ("三维迁移验证", ROOT / "comsol_3d_airfoil_radiator/generated_chip_airfoil_heat_sink/results/seven_param_3d_summary.csv"),
    ("参数敏感性", ROOT / "七参数_MLP_CNN流场重建/analysis_results/sensitivity/sensitivity_summary.json"),
]

def main() -> None:
    report_dir = ROOT / "七参数_MLP_CNN流场重建/reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    out = report_dir / "论文证据链总表.md"
    lines = ["# 论文证据链总表", "", "| 内容 | 路径 | 状态 |", "|---|---|---|"]
    for name, path in EVIDENCE:
        status = "存在" if path.exists() else "缺失"
        lines.append(f"| {name} | `{path.relative_to(ROOT)}` | {status} |")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(out)

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 运行证据链脚本**

Run:

```powershell
python "七参数_MLP_CNN流场重建\16_论文证据链汇总.py"
```

Expected:

```text
七参数_MLP_CNN流场重建\reports\论文证据链总表.md
```

- [ ] **Step 3: 检查缺失项**

Run:

```powershell
rg -n "缺失" "七参数_MLP_CNN流场重建\reports\论文证据链总表.md"
```

Expected: 如果有输出，先补对应实验；如果无输出，进入下一任务。

---

### Task 2: 完成 PVT 主模型 K 折验证

**Files:**
- Create: `七参数_MLP_CNN流场重建/13_PVT_K折验证.py`
- Output: `七参数_MLP_CNN流场重建/results/pvt_unet_kfold_3_e20/kfold_summary.json`
- Output: `七参数_MLP_CNN流场重建/results/pvt_unet_kfold_3_e20/kfold_metrics.csv`

- [ ] **Step 1: 新建 K 折脚本**

脚本要求：

```text
输入数据集：data/field_reconstruction_dataset_320x96_full_pUt.npz
模型结构：复用 08_UNet高精度流场重建训练.py 中的 ConditionalUNet
折数：3
每折 epoch：20
batch size：2
指标：Nu_R2、f_R2、eta_R2、p_MAE、U_MAE、T_MAE、field_MAE
输出：每折指标 CSV、均值和标准差 JSON
```

- [ ] **Step 2: 运行 3 折验证**

Run:

```powershell
python "七参数_MLP_CNN流场重建\13_PVT_K折验证.py" --dataset "七参数_MLP_CNN流场重建\data\field_reconstruction_dataset_320x96_full_pUt.npz" --output-dir "七参数_MLP_CNN流场重建\results\pvt_unet_kfold_3_e20" --folds 3 --epochs 20 --batch-size 2
```

Expected:

```text
kfold_summary.json
kfold_metrics.csv
fold_1/best_model.pth
fold_2/best_model.pth
fold_3/best_model.pth
```

- [ ] **Step 3: 写入论文 K 折章节**

在论文第 4 章更新：

```text
PVT 主模型 3 折验证用于检验模型对数据划分的敏感性。报告 Nu_R2、f_R2、eta_R2 和 PVT 场误差的均值与标准差。该结果作为泛化稳定性证据，不替代 50 epoch 全量主模型指标。
```

---

### Task 3: 完成参数敏感性分析

**Files:**
- Existing: `七参数_MLP_CNN流场重建/06_参数敏感性分析.py`
- Output: `七参数_MLP_CNN流场重建/analysis_results/sensitivity/sensitivity_summary.json`
- Output: `七参数_MLP_CNN流场重建/analysis_results/sensitivity/*.png`

- [ ] **Step 1: 检查敏感性脚本输入**

Run:

```powershell
rg -n "labels_7param_1000|eta|RandomForest|permutation|Spearman|Pearson" "七参数_MLP_CNN流场重建\06_参数敏感性分析.py"
```

Expected: 能看到标签文件、eta、随机森林、置换重要性、相关分析。

- [ ] **Step 2: 重新运行敏感性分析**

Run:

```powershell
python "七参数_MLP_CNN流场重建\06_参数敏感性分析.py"
```

Expected:

```text
analysis_results/sensitivity/sensitivity_summary.json
analysis_results/sensitivity/*.png
```

- [ ] **Step 3: 论文写法**

论文只写真实排序：

```text
敏感性分析包括 Pearson/Spearman 相关性、随机森林特征重要性和 DE 最优点附近单参数扰动。若三种方法均显示 Ts 靠前，则说明阵列流向间距是当前样本空间中影响 eta 的关键参数；若不同方法排序不完全一致，则说明参数对性能的影响存在非线性和局部依赖。
```

---

### Task 4: 完成网格无关性证据

**Files:**
- Create: `七参数_MLP_CNN流场重建/15_网格无关性汇总.py`
- Output: `七参数_MLP_CNN流场重建/analysis_results/grid_independence/grid_independence_summary.csv`
- Output: `七参数_MLP_CNN流场重建/analysis_results/grid_independence/grid_independence_summary.md`

- [ ] **Step 1: 汇总已有二维和三维网格结果**

脚本读取或人工录入三类网格：

```text
二维 baseline：粗、中、细网格的 Nu、f、eta、单元数
二维 DE 最优：粗、中、细网格的 Nu、f、eta、单元数
三维迁移模型：粗、中、细网格的 Tmax、Tavg、pressure_drop、thermal_resistance、单元数
```

相对误差计算：

```python
relative_error = abs(value_fine - value_medium) / max(abs(value_fine), 1e-12) * 100
```

- [ ] **Step 2: 判断网格无关**

验收标准：

```text
二维 Nu 中细网格相对差异 <= 2%
二维 f 中细网格相对差异 <= 3%
三维 Tmax 中细网格相对差异 <= 1%
三维压降中细网格相对差异 <= 5%
```

- [ ] **Step 3: 论文写法**

```text
网格无关性不用于追求最小误差，而用于证明后续 CFD 复算结论不依赖某一个过粗网格。若中细网格主要指标差异满足阈值，则后续批量计算采用中等网格以平衡计算成本和精度。
```

---

### Task 5: 完成消融实验

**Files:**
- Create: `七参数_MLP_CNN流场重建/14_PVT消融实验.py`
- Output: `七参数_MLP_CNN流场重建/results/pvt_ablation/ablation_summary.csv`
- Output: `七参数_MLP_CNN流场重建/results/pvt_ablation/ablation_summary.json`

- [ ] **Step 1: 定义消融组**

必须包含：

```text
A0: 仅标量性能分支，输出 Nu/f，不输出 PVT 场
A1: PVT 场监督 + Nu/f/eta，多任务基础模型
A2: A1 + 坐标通道
A3: A2 + 固体/流体区域指示
A4: A3 + 场梯度一致性损失
```

禁止写未训练结果：

```text
Attention、CBAM、完整 PDE residual、PINN 只写成扩展设计，除非真实训练并生成指标。
```

- [ ] **Step 2: 运行消融**

Run:

```powershell
python "七参数_MLP_CNN流场重建\14_PVT消融实验.py" --dataset "七参数_MLP_CNN流场重建\data\field_reconstruction_dataset_320x96_full_pUt.npz" --output-dir "七参数_MLP_CNN流场重建\results\pvt_ablation" --epochs 20 --batch-size 2
```

Expected:

```text
ablation_summary.csv
ablation_summary.json
A0/metrics.json
A1/metrics.json
A2/metrics.json
A3/metrics.json
A4/metrics.json
```

- [ ] **Step 3: 论文写法**

```text
消融实验用于回答每个设计是否必要。若加入 PVT 场监督后 eta_R2 提升或场误差降低，说明空间场监督能约束潜在特征；若加入梯度一致性后边界和尾迹误差降低，说明梯度项对局部高梯度区域有帮助。
```

---

### Task 6: 梳理二维优化与 CFD 复算

**Files:**
- Existing: `七参数_MLP_CNN流场重建/03_DE优化eta.py`
- Existing: `七参数_MLP_CNN流场重建/optimization_results/mlp_cnn_de_multiloss_e10/best_params.json`
- Existing: `七参数_MLP_CNN流场重建/validation_results/mlp_cnn_de_multiloss_e10/final_validation_report.json`

- [ ] **Step 1: 读取最优参数和复算结果**

Run:

```powershell
Get-Content -Encoding UTF8 "七参数_MLP_CNN流场重建\optimization_results\mlp_cnn_de_multiloss_e10\best_params.json"
Get-Content -Encoding UTF8 "七参数_MLP_CNN流场重建\validation_results\mlp_cnn_de_multiloss_e10\final_validation_report.json"
```

- [ ] **Step 2: 论文中明确边界**

写成：

```text
当前二维 DE 最优结果来自已完成并经过 CFD 复算的 MLP-CNN 性能分支；PVT U-Net 主模型用于论文云图重建和性能预测解释。若后续需要完全统一，可再用 PVT U-Net 性能分支重新执行 DE，并进行新的 CFD 复算。
```

- [ ] **Step 3: 生成二维复算对比表**

表格字段：

```text
结构、Nu_pred、f_pred、eta_pred、Nu_CFD、f_CFD、eta_CFD、相对误差
```

---

### Task 7: 梳理三维迁移验证

**Files:**
- Existing: `comsol_3d_airfoil_radiator/generated_chip_airfoil_heat_sink/results/seven_param_3d_summary.csv`
- Existing: `comsol_3d_airfoil_radiator/generated_chip_airfoil_heat_sink/chip_mlp_cnn_de_multiloss_e10/exports/*.png`

- [ ] **Step 1: 汇总三维指标**

Run:

```powershell
Import-Csv "comsol_3d_airfoil_radiator\generated_chip_airfoil_heat_sink\results\seven_param_3d_summary.csv" | Format-List
```

- [ ] **Step 2: 检查三维图**

Run:

```powershell
Get-ChildItem "comsol_3d_airfoil_radiator\generated_chip_airfoil_heat_sink\chip_mlp_cnn_de_multiloss_e10\exports" -Filter "*.png" | Select-Object Name,Length
```

- [ ] **Step 3: 论文写法**

```text
三维结果写为迁移验证，不写成三维全局优化。重点报告 Tavg、Tmax、pressure_drop、thermal_resistance 和 eta3D 的变化，并说明二维最优参数在三维芯片级模型中仍具有正向收益。
```

---

### Task 8: 更新论文正文

**Files:**
- Modify: `大论文初稿/基于MLP-CNN流热场重建代理模型的翼型柱阵列散热器优化研究.md`

- [ ] **Step 1: 固定章节结构**

采用：

```text
第1章 绪论
第2章 七参数几何建模与 CFD 数值方法
第3章 PVT 流热场数据集构建
第4章 MLP-CNN / Conditional U-Net 流热场重建代理模型
第5章 差分进化优化与二维 CFD 复算
第6章 三维散热器迁移验证
第7章 结论与展望
附录A 证据链
```

- [ ] **Step 2: 补齐实验章节**

必须写入：

```text
K 折验证：指标均值和标准差
敏感性分析：全局相关、随机森林、局部扰动
网格无关性：二维和三维的中细网格误差
消融实验：A0-A4 对照
物理约束边界：已完成 L_eta 和 L_grad，未完成完整 PDE residual
注意力边界：作为扩展设计，不写成已完成结果
```

- [ ] **Step 3: 复查不允许出现的表述**

Run:

```powershell
rg -n "完整PINN已完成|已完成CBAM主模型|几何掩码主线|高保真替代CFD|三维全局最优" "大论文初稿\基于MLP-CNN流热场重建代理模型的翼型柱阵列散热器优化研究.md"
```

Expected: 无输出。

---

### Task 9: 制作答辩 PPT

**Files:**
- Read: `七参数_几何掩码代理优化/ppt模版/毕业答辩PPT_final.pptx`
- Create: `大论文初稿/七参数MLP-CNN流热场重建答辩PPT.pptx`

- [ ] **Step 1: PPT 页结构**

页数控制在 22-28 页：

```text
1 标题
2 研究背景：散热器优化为什么需要代理模型
3 问题定义：七参数、Nu/f/eta、PVT 场
4 技术路线总览
5 七参数几何建模
6 二维 CFD 设置与边界条件
7 数据集构建：1000 组、p/U/T、96×320
8 为什么不是几何掩码输入
9 MLP-CNN / U-Net 网络结构
10 损失函数：PVT、梯度、Nu/f、eta
11 主模型结果：Nu/f/eta 指标
12 PVT 云图对比
13 K 折验证
14 消融实验
15 参数敏感性
16 网格无关性
17 DE 优化方法
18 二维 CFD 复算
19 三维迁移验证
20 结果讨论：有效性和不足
21 创新点
22 结论
23 老师可能提问与回答
```

- [ ] **Step 2: PPT 统一风格**

要求：

```text
数字字体统一，不允许同一页数字忽大忽小。
每页只讲一个结论。
每个关键结论旁边放证据路径或图表编号。
图比文字重要，少用大段话。
```

- [ ] **Step 3: 准备答辩问答**

必须覆盖：

```text
为什么不用几何掩码作为最终主线？
CNN 在这里学到了什么？
PVT 的 V 为什么用 U 表示？
为什么不说模型替代 CFD？
二维优化结果为什么可以做三维迁移？
K 折、敏感性、消融、网格无关分别证明什么？
注意力和物理约束为什么没有写成已完成主结果？
```

---

### Task 10: 最终验收

**Files:**
- Verify: `七参数_MLP_CNN流场重建/reports/论文证据链总表.md`
- Verify: `大论文初稿/基于MLP-CNN流热场重建代理模型的翼型柱阵列散热器优化研究.md`
- Verify: `大论文初稿/七参数MLP-CNN流热场重建答辩PPT.pptx`

- [ ] **Step 1: 运行脚本编译检查**

Run:

```powershell
python -m py_compile "七参数_MLP_CNN流场重建\01_构建流场数据集.py" "七参数_MLP_CNN流场重建\08_UNet高精度流场重建训练.py" "七参数_MLP_CNN流场重建\12_批量导出PVT云图.py" "七参数_MLP_CNN流场重建\13_PVT_K折验证.py" "七参数_MLP_CNN流场重建\14_PVT消融实验.py" "七参数_MLP_CNN流场重建\15_网格无关性汇总.py" "七参数_MLP_CNN流场重建\16_论文证据链汇总.py"
```

Expected: 无报错。

- [ ] **Step 2: 检查关键结果存在**

Run:

```powershell
Test-Path "七参数_MLP_CNN流场重建\data\field_reconstruction_dataset_320x96_full_pUt.npz"
Test-Path "七参数_MLP_CNN流场重建\results\unet_pUt_320x96_full_e50\metrics.json"
Test-Path "七参数_MLP_CNN流场重建\results\pvt_unet_kfold_3_e20\kfold_summary.json"
Test-Path "七参数_MLP_CNN流场重建\results\pvt_ablation\ablation_summary.json"
Test-Path "七参数_MLP_CNN流场重建\analysis_results\grid_independence\grid_independence_summary.md"
Test-Path "大论文初稿\七参数MLP-CNN流热场重建答辩PPT.pptx"
```

Expected: 全部输出 `True`。

- [ ] **Step 3: 最终论文禁用词检查**

Run:

```powershell
rg -n "完整PINN已完成|已完成CBAM主模型|高保真替代CFD|三维全局最优|几何掩码主线" "大论文初稿\基于MLP-CNN流热场重建代理模型的翼型柱阵列散热器优化研究.md"
```

Expected: 无输出。

- [ ] **Step 4: 最终交付说明**

交付时必须列出：

```text
1. 论文主线：七参数 -> CFD -> PVT 数据集 -> MLP-CNN/U-Net -> DE -> CFD 复算 -> 三维迁移
2. 已完成实验：PVT 主模型、K 折、敏感性、网格无关、消融、二维复算、三维迁移
3. 未写成主结果的内容：完整 PDE residual、注意力增强主模型、三维全局优化
4. 核心指标：Nu_R2、f_R2、eta_R2、p_MAE、U_MAE、T_MAE、eta_CFD、eta3D
```

---

## Self-Review

Spec coverage:
- K 折：Task 2。
- 敏感性：Task 3。
- 网格无关：Task 4。
- 消融：Task 5。
- 二维 DE 与 CFD 复算：Task 6。
- 三维迁移验证：Task 7。
- 论文正文：Task 8。
- PPT：Task 9。
- 最终验收：Task 10。

Placeholder scan:
- 本计划没有使用 TBD、TODO、implement later。
- 所有新增脚本都有明确输入、输出、命令和验收标准。

Type consistency:
- PVT 主线统一为 `p/U/T`。
- 速度大小统一写作 `U=sqrt(u^2+v^2)`。
- 旧 `u/v/p/T` 只作为历史对照，不作为最终云图主线。
