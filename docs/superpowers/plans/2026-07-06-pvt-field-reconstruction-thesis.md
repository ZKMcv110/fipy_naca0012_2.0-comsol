# PVT Field Reconstruction Thesis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将论文云图主线统一为 PVT 三场：压力场 p、速度大小 U、温度场 T，并完成可复查的数据集、训练、导图和论文证据链。

**Architecture:** 保留旧 `u/v/p/T` 四通道 MLP-CNN 作为 Nu/f/eta 性能代理与历史对照；新增 `p/U/T` 三通道数据集和 U-Net 链路作为论文云图主线。这里 PVT 中的 V 表示 velocity magnitude，代码中用 `U=sqrt(u^2+v^2)` 表示，与 COMSOL 云图表达式 `spf.U` 一致。

**Tech Stack:** Python、NumPy、PyTorch、Matplotlib、COMSOL 规则采样 npz、Markdown。

---

### Task 1: 正确 PVT 数据集构建

**Files:**
- Modify: `七参数_MLP_CNN流场重建/01_构建流场数据集.py`
- Output: `七参数_MLP_CNN流场重建/data/field_reconstruction_dataset_320x96_full_pUt.npz`

- [x] **Step 1: 增加派生通道 `U`**

`U=sqrt(u^2+v^2)`，用于对应 COMSOL 速度大小 `spf.U`。

- [x] **Step 2: 构建 1000 组高分辨率 PVT 数据集**

```powershell
python "七参数_MLP_CNN流场重建\01_构建流场数据集.py" --field-dir "七参数_PDE_PINN尝试\field_data_320x96" --output "七参数_MLP_CNN流场重建\data\field_reconstruction_dataset_320x96_full_pUt.npz" --field-names p,U,T --case-output-dir "七参数_MLP_CNN流场重建\data\standard_case_npz_320x96_full_pUt"
```

Observed: `field_shape = [1000, 3, 96, 320]`，`field_names = ["p", "U", "T"]`。

### Task 2: PVT U-Net 全量训练

**Files:**
- Modify: `七参数_MLP_CNN流场重建/08_UNet高精度流场重建训练.py`
- Modify: `七参数_MLP_CNN流场重建/09_导出UNet物理比例对比图.py`
- Modify: `七参数_MLP_CNN流场重建/10_UNet单工况过拟合测试.py`
- Modify: `七参数_MLP_CNN流场重建/11_导出COMSOL风格单变量图.py`

- [x] **Step 1: U-Net 输出通道由数据集决定**

使用 `ConditionalUNet(output_hw, output_channels=len(field_names))`。

- [x] **Step 2: 跑 PVT 全量泛化训练**

```powershell
python "七参数_MLP_CNN流场重建\08_UNet高精度流场重建训练.py" --dataset "七参数_MLP_CNN流场重建\data\field_reconstruction_dataset_320x96_full_pUt.npz" --field-dir "七参数_PDE_PINN尝试\field_data_320x96" --output-dir "七参数_MLP_CNN流场重建\results\unet_pUt_320x96_full_e50" --epochs 50 --batch-size 2 --field-weights 4,6,3 --grad-weight 0.5
```

Observed: `Nu_R2=0.969309`，`f_R2=0.978038`，`eta_R2=0.971888`，`p_MAE=0.908374`，`U_MAE=0.108227`，`T_MAE=0.439960 K`。

### Task 3: PVT COMSOL 风格导图

**Files:**
- Add: `七参数_MLP_CNN流场重建/12_批量导出PVT云图.py`
- Output: `七参数_MLP_CNN流场重建/results/pvt_comsol_style_exports_pUt_full_e50_case20040`

- [x] **Step 1: 批量导出 p、U、T**

```powershell
python "七参数_MLP_CNN流场重建\12_批量导出PVT云图.py" --case-id 20040 --variables p,U,T --dataset "七参数_MLP_CNN流场重建\data\field_reconstruction_dataset_320x96_full_pUt.npz" --model-dir "七参数_MLP_CNN流场重建\results\unet_pUt_320x96_full_e50" --field-dir "七参数_PDE_PINN尝试\field_data_320x96" --output-dir "七参数_MLP_CNN流场重建\results\pvt_comsol_style_exports_pUt_full_e50_case20040"
```

Expected: 每个变量输出 `comsol_sample_style.png`、`pred_style.png`、`error_style.png`。

### Task 4: 文档修正

**Files:**
- Modify: `七参数_MLP_CNN流场重建/README.md`
- Modify: `大论文初稿/基于MLP-CNN流热场重建代理模型的翼型柱阵列散热器优化研究.md`

- [x] **Step 1: README 写清 PVT 定义**

PVT 中 V 是速度大小 `U`，不是速度分量 `v`。

- [x] **Step 2: 论文摘要和证据链加入正确 PVT 结果**

加入 `field_reconstruction_dataset_320x96_full_pUt.npz`、`unet_pUt_320x96_full_e50` 和 `pvt_comsol_style_exports_pUt_full_e50_case20040`。

### Task 5: 后续正式全量结果

**Files:**
- Output: `七参数_PDE_PINN尝试/field_data_320x96`
- Output: `七参数_MLP_CNN流场重建/data/field_reconstruction_dataset_320x96_full_pUt.npz`
- Output: `七参数_MLP_CNN流场重建/results/unet_pUt_320x96_full_e50`

- [x] **Step 1: 继续导出剩余 320×96 COMSOL 规则采样场**

已导出 1000/1000。

```powershell
& ".\myenvs_fipynaca2.0\Scripts\python.exe" ".\七参数_PDE_PINN尝试\01_导出全场数据.py" --start 195 --end 1000 --nx 320 --ny 96 --output-dir ".\七参数_PDE_PINN尝试\field_data_320x96"
```

- [x] **Step 2: 构建全量 PVT 数据集**

```powershell
python "七参数_MLP_CNN流场重建\01_构建流场数据集.py" --field-dir "七参数_PDE_PINN尝试\field_data_320x96" --output "七参数_MLP_CNN流场重建\data\field_reconstruction_dataset_320x96_full_pUt.npz" --field-names p,U,T
```

- [x] **Step 3: 训练全量 PVT U-Net**

```powershell
python "七参数_MLP_CNN流场重建\08_UNet高精度流场重建训练.py" --dataset "七参数_MLP_CNN流场重建\data\field_reconstruction_dataset_320x96_full_pUt.npz" --field-dir "七参数_PDE_PINN尝试\field_data_320x96" --output-dir "七参数_MLP_CNN流场重建\results\unet_pUt_320x96_full_e50" --epochs 50 --batch-size 2 --field-weights 4,6,3 --grad-weight 0.5
```

- [x] **Step 4: 用全量模型替换论文中的单工况验证图**

只有全量测试集指标稳定后，才把单工况验证改写为正式泛化结果。
