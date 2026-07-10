# 七参数 MLP-CNN 流热场重建代理模型

本目录是独立新方案，不修改既有 `七参数_几何掩码代理优化`、`七参数_PDE_PINN尝试` 或三维验证目录。

## 技术路线

七参数参数化建模 -> 二维 CFD 流热耦合仿真 -> 导出 `Nu/f/eta` 与 PVT 云图主线数值场 -> 统一网格化数据集 -> MLP-CNN / U-Net 多任务代理模型 -> DE 优化 `eta` -> CFD 复算验证 -> 三维迁移验证。

## 当前最小链路

- `01_构建流场数据集.py`：只读读取七参数标签和已有 `case_x_full.npz`，构建统一训练数据；支持 `--field-names p,v,T` 构建论文三场云图数据集。
- `02_MLP_CNN流场重建训练.py`：训练“七参数 -> u/v/p/T + Nu/f”的最小多任务模型，并输出指标和对比图。
- `08_UNet高精度流场重建训练.py`：训练“七参数 + air/solid domain mask + x/y 坐标 -> 多通道场 + Nu/f”的条件 U-Net 模型，输出通道由数据集 `field_names` 决定，可用于 PVT 三场主线。
- `11_导出COMSOL风格单变量图.py`：按 COMSOL 风格导出单变量规则采样场、预测场和误差场。
- `12_批量导出PVT云图.py`：一键导出论文主线 PVT 三场的 COMSOL 风格图，其中 V 表示速度大小 `U=sqrt(u^2+v^2)`。

## 数据口径

当前优先读取：

- 标签：`七参数_几何掩码代理优化/samples/labels_7param_1000.csv`
- 全场数据：`七参数_PDE_PINN尝试/field_data/case_{case_id}_full.npz`

`case_x_full.npz` 应包含：

- `x, y, u, v, p, T, domain`
- 默认旧数据集保留 `u/v/p/T` 四通道；论文云图主线使用 `p/U/T` 三通道，其中 `U` 对应 COMSOL 的 `spf.U` 速度大小，脚本会自动按 `unique(y) x unique(x)` 恢复为二维场。

## 运行

```powershell
python .\七参数_MLP_CNN流场重建\01_构建流场数据集.py --limit 200
python .\七参数_MLP_CNN流场重建\02_MLP_CNN流场重建训练.py --epochs 20
```

高精度场重建版本：

```powershell
python .\七参数_MLP_CNN流场重建\08_UNet高精度流场重建训练.py --epochs 30 --batch-size 16 --output-dir ".\七参数_MLP_CNN流场重建\results\unet_mask_field_e30"
```

构建论文 PVT 三场全量数据集：

```powershell
python .\七参数_MLP_CNN流场重建\01_构建流场数据集.py --field-dir ".\七参数_PDE_PINN尝试\field_data_320x96" --output ".\七参数_MLP_CNN流场重建\data\field_reconstruction_dataset_320x96_full_pUt.npz" --field-names p,U,T --case-output-dir ".\七参数_MLP_CNN流场重建\data\standard_case_npz_320x96_full_pUt"
```

导出 PVT 三场 COMSOL 风格图：

```powershell
python .\七参数_MLP_CNN流场重建\12_批量导出PVT云图.py --case-id 20040 --variables p,U,T --dataset ".\七参数_MLP_CNN流场重建\data\field_reconstruction_dataset_320x96_full_pUt.npz" --model-dir ".\七参数_MLP_CNN流场重建\results\unet_pUt_320x96_full_e50" --field-dir ".\七参数_PDE_PINN尝试\field_data_320x96" --output-dir ".\七参数_MLP_CNN流场重建\results\pvt_comsol_style_exports_pUt_full_e50_case20040"
```

高分辨率 COMSOL 规则采样版本：

```powershell
.\七参数_PDE_PINN尝试\run_extract_320x96_full.bat
.\七参数_MLP_CNN流场重建\run_train_unet_320x96_after_export.bat
```

说明：

- `run_extract_320x96_full.bat` 会从已有 COMSOL `.mph` 中导出 `320×96` 规则采样场，输出到 `七参数_PDE_PINN尝试/field_data_320x96`。
- `run_train_unet_320x96_after_export.bat` 会在全量高分辨率场导出完成后构建数据集并训练 U-Net。
- 已完成前 20 组高分辨率导出和小样本链路验证：
  - 高分辨率场目录：`七参数_PDE_PINN尝试/field_data_320x96`
  - 小样本数据集：`data/field_reconstruction_dataset_320x96_first20.npz`
  - 小样本训练结果：`results/unet_mask_320x96_first20_e3`
- 20 组训练只用于验证流程和出图比例，不作为正式模型性能结论。
- 已完成单工况过拟合测试：
  - 脚本：`10_UNet单工况过拟合测试.py`
  - 结果：`results/unet_overfit_case_20009_e300`
  - 指标：`field_MAE=0.114535`，`u_MAE=0.056958`，`v_MAE=0.003218`，`p_MAE=0.197056`，`T_MAE=0.200906 K`
  - 结论：条件 U-Net 结构具备复现 COMSOL 规则采样场的能力；前 20 组小样本泛化差是样本量不足，不是网络结构不能学。
- 已完成 PVT 三通道全量泛化训练：
  - 数据集：`data/field_reconstruction_dataset_320x96_full_pUt.npz`
  - 结果：`results/unet_pUt_320x96_full_e50`
  - 划分：训练/验证/测试 = `700/150/150`
  - 标量指标：`Nu_R2=0.969309`，`f_R2=0.978038`，`eta_R2=0.971888`
  - 场指标：`p_MAE=0.908374`，`U_MAE=0.108227`，`T_MAE=0.439960 K`
  - 导图：`results/pvt_comsol_style_exports_pUt_full_e50_case20040`
  - 说明：导图背景为规则采样场，翼型边界为七参数解析轮廓，不再使用低分辨率 `domain` 栅格轮廓。

## 模型口径

- 原 `02_MLP_CNN流场重建训练.py` 更适合作为 Nu/f/eta 快速预测与 DE 优化筛选模型。
- 新 `08_UNet高精度流场重建训练.py` 更适合作为高精度流热场重建模型，因为它显式使用 domain mask 和坐标条件。
- 当前 5 epoch 短训验证结果位于 `results/unet_mask_field_e5`，相比原 10 epoch MLP-CNN，场重建指标已有明显改善：
  - `field_MAE`: 0.966458 -> 0.679607
  - `u_MAE`: 0.321742 -> 0.229635
  - `v_MAE`: 0.108398 -> 0.042386
  - `p_MAE`: 2.160603 -> 1.598204
  - `T_MAE`: 1.275088 K -> 0.848202 K
- 5 epoch U-Net 的 Nu/f/eta 标量预测尚未追上原 10 epoch MLP-CNN，因此正式优化仍建议先使用原 MLP-CNN，场图展示和论文解释使用 U-Net 长训结果。
