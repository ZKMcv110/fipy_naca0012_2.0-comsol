# NACA0012 翼型管阵列流热耦合仿真、代理建模与论文写作项目

本项目当前包含 COMSOL 批量仿真、多模态 CNN/MLP 代理建模、论文图生成、大论文写作，以及早期 FiPy/Gmsh 旧流程归档。根目录主要保留当前 COMSOL/CNN 主流程；旧流程和论文材料已分别整理到专门文件夹。

更完整的项目地图见：

```text
项目总说明.md
```

重新跑数据、训练模型和生成论文图的推荐顺序见：

```text
EXPERIMENT_WORKFLOW.md
```

## 当前目录结构

```text
fipy_naca0012_2.0/
├── consol_cfddata/             # COMSOL 批量仿真结果，正式 case 数据
├── csv_data/                   # 当前 COMSOL/CNN 使用的数据表
├── data_processing/            # 标签重建、数据整理和完整性检查脚本
├── ai_cnn_model_results/       # CNN、MLP、多模态模型训练结果
├── paper_figures_svg/          # 论文图输出
├── comsol论文图脚本/           # 论文 SVG/PNG 图生成脚本
├── comsol单工况测试/           # 单个 COMSOL case 调试入口
├── thesis_writing/             # 大论文写作工作区
├── fipy_pipeline/              # 早期 FiPy/Gmsh 旧流程归档
├── mcp_comsol_demo/            # COMSOL skill/MCP 自动建模演示
├── research-writing-skill-main/# 研究写作 skill 源文件
└── myenvs_fipynaca2.0/         # Python 虚拟环境
```

## 当前主流程

当前建议以 COMSOL 批量仿真和多模态代理模型为主线。

### 1. 批量 COMSOL 仿真

```powershell
.\myenvs_fipynaca2.0\Scripts\python.exe consol500组参数.py
```

主要输出：

```text
consol_cfddata/
csv_data/final_results.csv
```

### 2. 重建/检查标签

```powershell
.\myenvs_fipynaca2.0\Scripts\python.exe .\data_processing\rebuild_labels_from_results.py
```

主要输出：

```text
consol_cfddata/labels.csv
```

### 3. 训练 CNN 模型

```powershell
.\myenvs_fipynaca2.0\Scripts\python.exe cnnstep2.py
```

主要输出：

```text
ai_cnn_model_results/
```

### 4. 单 case 预测

```powershell
.\myenvs_fipynaca2.0\Scripts\python.exe cnnstep3.py
```

## 对比模型与表格

训练标量 MLP 基线：

```powershell
.\myenvs_fipynaca2.0\Scripts\python.exe train_mlp_baseline.py
```

训练多模态特征融合模型：

```powershell
.\myenvs_fipynaca2.0\Scripts\python.exe train_multimodal_feature_model.py
```

这些脚本会更新 `ai_cnn_model_results/` 中的模型指标和论文表格数据。

## 论文图生成

论文图脚本集中在：

```text
comsol论文图脚本/
```

一键生成当前论文图：

```powershell
.\myenvs_fipynaca2.0\Scripts\python.exe .\comsol论文图脚本\generate_comsol_svgs.py
```

只生成某一类图：

```powershell
.\myenvs_fipynaca2.0\Scripts\python.exe .\comsol论文图脚本\generate_comsol_svgs.py --only base
.\myenvs_fipynaca2.0\Scripts\python.exe .\comsol论文图脚本\generate_comsol_svgs.py --only cbam
.\myenvs_fipynaca2.0\Scripts\python.exe .\comsol论文图脚本\generate_comsol_svgs.py --only fig8
.\myenvs_fipynaca2.0\Scripts\python.exe .\comsol论文图脚本\generate_comsol_svgs.py --only heat
```

输出目录：

```text
paper_figures_svg/
```

注意：请从项目根目录运行图脚本，不要先 `cd comsol论文图脚本`。

## 单工况调试

如果只想测试一个固定参数的 COMSOL case：

```powershell
.\myenvs_fipynaca2.0\Scripts\python.exe .\comsol单工况测试\test_single_case.py
```

输出默认进入：

```text
comsol单工况测试/test_case_debug/
```

这只是调试产物，不是正式 500 组数据集。

## 大论文写作

大论文工作区：

```text
thesis_writing/
```

主要入口：

```text
thesis_writing/README.md
thesis_writing/plan/outline.md
thesis_writing/plan/progress.md
thesis_writing/chapters/
```

建议把论文原始草稿、图表说明和证据记录继续整理进 `thesis_writing/source_drafts/` 和 `thesis_writing/notes/`。

## FiPy 旧流程

早期 FiPy/Gmsh 流程已迁入：

```text
fipy_pipeline/
```

如果需要运行旧流程，请先进入该目录：

```powershell
cd fipy_pipeline
python run_all_cases_refactored.py
```

不要从根目录直接运行 `python fipy_pipeline/run_all_cases_refactored.py`，因为旧脚本大量依赖相对路径。详细说明见：

```text
fipy_pipeline/README.md
```

## 重要数据目录

暂时不要随意删除：

```text
consol_cfddata/
csv_data/
ai_cnn_model_results/
paper_figures_svg/
thesis_writing/
fipy_pipeline/
myenvs_fipynaca2.0/
```

其中 `consol_cfddata/` 和 `fipy_pipeline/results/` 体积较大，但重建成本高。

## 清理建议

可清理缓存：

```text
__pycache__/
```

旧副本脚本建议归档到 `archive/old_scripts/`，不要混在根目录。详细清单见：

```text
项目总说明.md
```

## 许可证

本项目沿用仓库中的 `LICENSE`。
