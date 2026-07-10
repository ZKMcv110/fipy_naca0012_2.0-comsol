# COMSOL 论文图脚本

本文件夹集中存放基于 COMSOL/CNN 结果生成论文图的脚本。

## 推荐入口

在项目根目录运行：

```powershell
.\myenvs_fipynaca2.0\Scripts\python.exe .\旧六参数流程\论文图脚本\generate_comsol_svgs.py
```

只生成某一类图：

```powershell
.\myenvs_fipynaca2.0\Scripts\python.exe .\旧六参数流程\论文图脚本\generate_comsol_svgs.py --only base
.\myenvs_fipynaca2.0\Scripts\python.exe .\旧六参数流程\论文图脚本\generate_comsol_svgs.py --only cbam
.\myenvs_fipynaca2.0\Scripts\python.exe .\旧六参数流程\论文图脚本\generate_comsol_svgs.py --only fig8
.\myenvs_fipynaca2.0\Scripts\python.exe .\旧六参数流程\论文图脚本\generate_comsol_svgs.py --only heat
```

指定基准工况和最优工况：

```powershell
.\myenvs_fipynaca2.0\Scripts\python.exe .\旧六参数流程\论文图脚本\generate_comsol_svgs.py --baseline-case 1 --optimal-case 195
```

## 脚本分工

- `generate_comsol_svgs.py`：统一入口，调度下面四个图生成脚本。
- `generate_paper_svgs.py`：生成基础论文 SVG，包括几何、边界、网格、流程、预测散点、模型对比和 loss 曲线。
- `generate_cbam_architecture_svg.py`：生成 CBAM 双流 CNN 架构图。
- `make_fig8_cfd_comparison.py`：生成基准/最优 COMSOL 云图对比。
- `make_heat_dissipation_evidence.py`：生成散热证据链图和 `heat_dissipation_summary.csv`。

## 注意

请从项目根目录运行脚本，不要先 `cd 旧六参数流程/论文图脚本`。这些脚本会读取根目录下的：

- `consol_cfddata/`
- `csv_data/`
- `ai_cnn_model_results/`

并把结果写入：

- `paper_figures_svg/`
