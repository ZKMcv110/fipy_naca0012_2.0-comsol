# NACA 翼型管阵列流热仿真与代理建模项目

> 当前目录状态：七参数论文主线保留在 `七参数_MLP_CNN流场重建/`；旧六参数模型结果已移至 `归档/旧六参数模型结果/`；旧论文材料已移至 `归档/旧论文材料/`；旧图件已移至 `归档/旧论文图件/`；历史答辩输出已移至 `归档/历史答辩材料/`；外部 skill 包集中在 `skills/`。

本项目用于翼型柱阵列散热器流动换热数值模拟、二维 CFD 数据集构建、七参数 MLP-CNN / Conditional U-Net 流热场重建代理模型训练，以及二维优化结果向三维芯片级散热器模型的迁移验证。

当前论文主线已经从旧六参数 CNN/几何掩码流程转为七参数 PVT 流热场重建流程。旧 FiPy、旧六参数 CNN 和旧答辩材料保留作追溯，不作为当前论文默认运行入口。

## 当前主流程

1. 七参数参数化建模。
2. 二维 COMSOL 流热耦合仿真。
3. 导出 p/U/T 高分辨率 PVT 数值场数据集。
4. 建立 MLP-CNN / Conditional U-Net 流热场重建代理模型。
5. 输出 p/U/T 场、Nu、f，并计算 eta。
6. 采用差分进化 DE 搜索 eta 最大的结构。
7. 对最优结构进行二维 CFD 复算验证。
8. 将二维优化结构迁移到三维芯片级散热器中验证。
9. 将可信数据、图件、证据链、论文正文和答辩 PPT 整理到 `大论文初稿/`。

## 关键入口

- [运行入口说明.md](docs/运行入口说明.md)：主命令和运行顺序。
- [项目目录说明.md](docs/项目目录说明.md)：当前主线、旧流程边界和哪些目录不能删。
- [docs/项目目录当前审查.md](docs/项目目录当前审查.md)：当前目录是否合理、哪些目录冻结、剩余小问题和验证结果。
- [docs/项目目录整理方案.md](docs/项目目录整理方案.md)：项目整理原则、保留目录、归档目录和清理建议。
- [docs/项目目录迁移清单.md](docs/项目目录迁移清单.md)：后续真实移动旧材料时使用的迁移清单和验证命令。
- [数据说明.md](docs/数据说明.md)：二维标签、结果文件、图像和训练结果说明。
- [论文证据链.md](docs/论文证据链.md)：论文图表与数据来源对应关系。
- 旧六参数实验流程文档已归档到 `归档/旧论文材料/`，旧论文图件生成脚本已归档到 `归档/旧论文图件/`。

## 核心目录

```text
fipy_naca0012_2.0/
├─ 七参数_MLP_CNN流场重建/
├─ 七参数_几何掩码代理优化/
├─ 七参数_PDE_PINN尝试/
├─ comsol_3d_airfoil_radiator/
├─ 大论文初稿/
├─ docs/
├─ tests/
├─ 工具脚本/
├─ 旧六参数流程/
├─ consol_cfddata/
├─ paper_reference/
├─ 第三方工具/
└─ 归档/
```

当前不要移动或删除：

- `七参数_MLP_CNN流场重建/`
- `七参数_几何掩码代理优化/`
- `七参数_PDE_PINN尝试/`
- `comsol_3d_airfoil_radiator/`
- `大论文初稿/`
- `consol_cfddata/`

旧六参数模型结果、旧论文材料和历史答辩输出可以按 `docs/项目目录迁移清单.md` 逐项归档。

## 二维 COMSOL 数据

以下为旧六参数二维流程入口，保留作历史追溯；当前七参数论文主线以 `七参数_MLP_CNN流场重建/` 和 `七参数_几何掩码代理优化/` 下的结果为准。

单工况：

```powershell
python 工具脚本/comsol单次执行脚本.py --Ta 0 --Twa 0.4 --Tb 0.12 --Ts 1.1 --Tt 0.85 --Tad 0 --outdir consol_cfddata/case_test_cfd_solution
```

批量工况：

```powershell
python 工具脚本/consol500组参数.py --num-samples 500
```

当前二维数据集状态：

- 样本数：500
- 标签文件：`consol_cfddata/labels.csv`
- 工况目录：`consol_cfddata/case_{编号}_cfd_solution/`
- 每个正式工况包含：`model.mph`、`result.json`、`velocity_magnitude.png`、`pressure.png`、`temperature.png`

## 神经网络模型

当前神经网络脚本集中在 `旧六参数流程/模型脚本/`。

```powershell
python 旧六参数流程/模型脚本/MLP基线_训练.py
python 旧六参数流程/模型脚本/多模态特征融合_训练.py
python 旧六参数流程/模型脚本/CNN_CBAM_训练.py
python 旧六参数流程/模型脚本/物理信息CNN_训练.py
```

预测示例：

```powershell
python 旧六参数流程/模型脚本/CNN_CBAM_预测.py --case-id 1
python 旧六参数流程/模型脚本/物理信息CNN_预测.py --case-id 1
```

当前主要结果文件：

- `归档/旧六参数模型结果/ai_cnn_model_results/mlp_baseline_metrics.json`
- `归档/旧六参数模型结果/ai_cnn_model_results/multimodal_feature_metrics.json`
- `归档/旧六参数模型结果/cnn_big_results/cnn_big_metrics.json`
- `归档/旧六参数模型结果/cnn_cbam_gap_results/cnn_cbam_gap_metrics.json`
- `归档/旧六参数模型结果/pi_cnn_nuf_results/pi_cnn_nuf_metrics.json`
- `归档/旧六参数模型结果/ai_cnn_model_results/feature_fusion_kfold_5/feature_fusion_kfold_summary.json`

## 三维 COMSOL 模型

三维脚本集中在 `comsol_3d_airfoil_radiator/`。

主建模脚本：

```powershell
python comsol_3d_airfoil_radiator/build_airfoil_pillar_heat_sink.py --all --mesh-hauto 4 --solve
```

后处理：

```powershell
python comsol_3d_airfoil_radiator/05_结果后处理.py
python comsol_3d_airfoil_radiator/10_绘制结果汇总.py
```

当前三维结果：

- `comsol_3d_airfoil_radiator/generated_pillar_heat_sink/results/pillar_heat_sink_summary.csv`
- `comsol_3d_airfoil_radiator/generated_pillar_heat_sink/results/pillar_heat_sink_summary.json`

注意：当前三维结果显示优化结构优势不明显，论文中不能写成“已验证三维显著最优”。

## 不能随意删除的内容

- `consol_cfddata/`
- `归档/旧六参数模型结果/ai_cnn_model_results/`
- `归档/旧六参数模型结果/cnn_big_results/`
- `归档/旧六参数模型结果/cnn_cbam_gap_results/`
- `归档/旧六参数模型结果/pi_cnn_nuf_results/`
- `comsol_3d_airfoil_radiator/generated_pillar_heat_sink/`
- `大论文初稿/`
- 任何仍需要复现的 `.mph`、`.json`、`.csv`、`.pth`

## Git 管理原则

- 大型 CFD 数据、`.mph`、训练权重、论文中间文件默认不提交。
- 可提交脚本、轻量说明文档、指标 JSON/CSV、必要的图表脚本。
- 当前 Git 状态中旧根目录神经网络脚本显示删除，新脚本集中在 `旧六参数流程/模型脚本/`。提交前需要确认这是正式迁移。

## 许可证

本项目沿用仓库中的 `LICENSE`。
