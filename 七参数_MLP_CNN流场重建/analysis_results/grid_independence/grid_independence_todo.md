# 网格无关性补算任务书

本任务书用于补齐论文中尚未完成的粗/中/细三档网格无关性验证。所有数值必须来自真实 COMSOL 求解，不得手工编造。

## 二维 CFD 补算

目标工况：baseline 与 DE_optimum。每个工况至少计算 coarse、medium、fine 三档网格。

| 工况 | 网格档位 | 建议网格设置 | 必须导出指标 |
|---|---|---|---|
| baseline | coarse | 当前正式网格更粗一档 | Nu、f、eta、delta_p、单元数 |
| baseline | medium | 当前正式网格或论文采用网格 | Nu、f、eta、delta_p、单元数 |
| baseline | fine | 当前正式网格更细一档 | Nu、f、eta、delta_p、单元数 |
| DE_optimum | coarse | 当前正式网格更粗一档 | Nu、f、eta、delta_p、单元数 |
| DE_optimum | medium | 当前正式网格或论文采用网格 | Nu、f、eta、delta_p、单元数 |
| DE_optimum | fine | 当前正式网格更细一档 | Nu、f、eta、delta_p、单元数 |

推荐使用已封装的二维网格无关性运行器。默认 dry-run，只检查命令链；显式传入 `--run` 才会启动 COMSOL 求解：

```powershell
python "七参数_MLP_CNN流场重建\17_二维网格无关性运行器.py"
python "七参数_MLP_CNN流场重建\17_二维网格无关性运行器.py" --run
python "七参数_MLP_CNN流场重建\15_网格无关性汇总.py" --input-csv "七参数_MLP_CNN流场重建\analysis_results\grid_independence\grid_independence_2d_real_results.csv"
```

二维验收阈值：

```text
abs(Nu_fine - Nu_medium) / abs(Nu_fine) <= 2%
abs(f_fine - f_medium) / abs(f_fine) <= 3%
```

## 三维迁移模型补算

目标工况：baseline 与 chip_mlp_cnn_de_multiloss_e10。每个工况至少计算 coarse、medium、fine 三档网格。

| 工况 | 网格档位 | 可参考脚本参数 | 必须导出指标 |
|---|---|---|---|
| baseline | coarse | `--mesh-hauto` 较粗设置 | Tmax、Tavg、delta_p、r_th、eta3D、单元数 |
| baseline | medium | 当前正式设置 | Tmax、Tavg、delta_p、r_th、eta3D、单元数 |
| baseline | fine | 更细设置 | Tmax、Tavg、delta_p、r_th、eta3D、单元数 |
| optimized | coarse | `--mesh-hauto` 较粗设置 | Tmax、Tavg、delta_p、r_th、eta3D、单元数 |
| optimized | medium | 当前正式设置 | Tmax、Tavg、delta_p、r_th、eta3D、单元数 |
| optimized | fine | 更细设置 | Tmax、Tavg、delta_p、r_th、eta3D、单元数 |

推荐使用已封装的三维网格无关性运行器。默认 dry-run，只检查命令链；显式传入 `--run` 才会启动 COMSOL 求解：

```text
python "comsol_3d_airfoil_radiator\20_三维网格无关性运行器.py"
python "comsol_3d_airfoil_radiator\20_三维网格无关性运行器.py" --run --skip-existing
python "七参数_MLP_CNN流场重建\15_网格无关性汇总.py" --input-csv "七参数_MLP_CNN流场重建\analysis_results\grid_independence\grid_independence_3d_real_results.csv"
```

运行器内部复用以下三维建模和后处理脚本：

```text
comsol_3d_airfoil_radiator/18_芯片级翼型鳍片散热器建模.py
comsol_3d_airfoil_radiator/15_提取七参数三维指标.py
comsol_3d_airfoil_radiator/build_airfoil_pillar_heat_sink.py
comsol_3d_airfoil_radiator/build_realistic_airfoil_heat_sink.py
comsol_3d_airfoil_radiator/05_结果后处理.py
```

三维验收阈值：

```text
abs(Tmax_fine - Tmax_medium) / abs(Tmax_fine) <= 1%
abs(delta_p_fine - delta_p_medium) / abs(delta_p_fine) <= 5%
```

## 补算后写入格式

将真实结果追加到：

```text
七参数_MLP_CNN流场重建/analysis_results/grid_independence/grid_independence_input_template.csv
```

字段至少包括：

```text
dimension,case,mesh_level,element_count,Nu,f,eta,Tmax,Tavg,pressure_drop,thermal_resistance,relative_to_fine_percent,status
```

补算完成后重新运行：

```powershell
python "七参数_MLP_CNN流场重建\15_网格无关性汇总.py" --input-csv "七参数_MLP_CNN流场重建\analysis_results\grid_independence\grid_independence_2d_real_results.csv" --input-csv "七参数_MLP_CNN流场重建\analysis_results\grid_independence\grid_independence_3d_real_results.csv"
python "七参数_MLP_CNN流场重建\16_论文证据链汇总.py"
```
