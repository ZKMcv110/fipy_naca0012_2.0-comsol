# 二维壁面边界层网格尝试记录

本文档记录二维翼型柱阵列网格无关性整改中的壁面边界层网格尝试。该记录只说明代码和 COMSOL 运行现状，不把失败尝试写成已完成的网格无关性证据。

## 1. 已实现的代码入口

已在二维单工况 COMSOL 脚本中新增可选参数：

```text
--wall_bl_layers
--wall_bl_hminfact
--wall_bl_required
```

对应脚本：

```text
七参数_几何掩码代理优化/02a_七参数COMSOL单工况求解.py
```

实现方式：

- 使用 `sel_airfoil_walls` Box selection 在翼型阵列附近选择边界。
- 使用 `BndLayer` 在空气域上创建边界层网格。
- 使用 `BndLayerProp` 将边界层属性施加到 `sel_airfoil_walls`。
- 当传入 `--wall_bl_required` 时，如果边界层创建或网格划分失败，脚本直接报错，不继续生成不可信结果。

二维网格运行器已支持 8 段 `--levels` 格式：

```text
name:hauto:air_hmax:air_hmin:solid_hmax:solid_hmin:wall_bl_layers:wall_bl_hminfact
```

对应脚本：

```text
七参数_MLP_CNN流场重建/17_二维网格无关性运行器.py
```

## 2. 已执行尝试

### BL1

命令：

```powershell
& "myenvs_fipynaca2.0\Scripts\python.exe" "七参数_MLP_CNN流场重建\17_二维网格无关性运行器.py" --levels "BL1:4:1.2[mm]:0.12[mm]:0.28[mm]:0.028[mm]:5:3.0" --cases baseline --run --timeout 1800
```

结果：

- 状态：失败。
- 失败阶段：`mesh1.run()`。
- 日志：`七参数_MLP_CNN流场重建/analysis_results/grid_independence/two_d_runs/baseline/BL1/stdout.log`

### BL_light

命令：

```powershell
& "myenvs_fipynaca2.0\Scripts\python.exe" "七参数_MLP_CNN流场重建\17_二维网格无关性运行器.py" --levels "BL_light:4:1.2[mm]:0.12[mm]:0.28[mm]:0.028[mm]:3:1.5" --cases baseline --run --timeout 1800
```

结果：

- 状态：失败。
- 失败阶段：`mesh1.run()`。
- 日志：`七参数_MLP_CNN流场重建/analysis_results/grid_independence/two_d_runs/baseline/BL_light/stdout.log`

### BL_diag

命令：

```powershell
& "myenvs_fipynaca2.0\Scripts\python.exe" "七参数_MLP_CNN流场重建\17_二维网格无关性运行器.py" --levels "BL_diag:4:1.2[mm]:0.12[mm]:0.28[mm]:0.028[mm]:3:1.5" --cases baseline --run --timeout 1800
```

结果：

- 状态：失败。
- 壁面 Box selection 选中边界数量：`50`。
- 失败阶段：`mesh1.run()`。
- 日志：`七参数_MLP_CNN流场重建/analysis_results/grid_independence/two_d_runs/baseline/BL_diag/stdout.log`

### BL_only

命令：

```powershell
& "myenvs_fipynaca2.0\Scripts\python.exe" "七参数_MLP_CNN流场重建\17_二维网格无关性运行器.py" --levels "BL_only:4:3[mm]:0.3[mm]:0.8[mm]:0.08[mm]:3:1.5" --cases baseline --run --timeout 1800
```

结果：

- 状态：失败。
- 失败阶段：`mesh1.run()`。
- 日志：`七参数_MLP_CNN流场重建/analysis_results/grid_independence/two_d_runs/baseline/BL_only/stdout.log`

## 3. 当前判断

当前失败不再是“壁面边界选择为空”的问题，因为 `BL_diag` 中已经确认翼型阵列附近 Box selection 选中了 `50` 条边界。失败更可能来自：

- 选中的边界中包含不适合生成边界层的外边界或几何小边。
- `BndLayer` 对当前空气域和固体翼型柱共边界的网格拓扑要求更严格。
- 当前翼型柱之间间距较小，边界层膨胀后与相邻翼型或尾迹区域网格发生冲突。
- 仅靠 Box selection 选择壁面仍不够精确，需要构建稳定的显式翼型壁面边界集合。

## 4. 下一步

不能把当前壁面边界层网格写成已完成结果。下一步应先解决“稳定翼型壁面边界集合”问题：

1. 导出当前二维模型的边界编号和边界中心坐标。
2. 用边界中心坐标、相邻域信息或几何标签筛选真实翼型壁面边界。
3. 生成显式边界选择 `sel_airfoil_wall_explicit`。
4. 再将 `BndLayerProp` 绑定到该显式选择，而不是 Box selection。
5. 先只对 baseline 单工况做一档边界层网格求解，成功后再纳入网格无关性补算。

论文和答辩中只能写：本文已经定位到二维 Nu/f 对壁面和尾迹网格高度敏感，初步尝试壁面边界层网格但尚未形成可稳定求解的三档网格证据，因此不宣称网格无关性通过。

## 5. 2026-07-07 补充诊断

已对 baseline 工况导出翼型壁面边界选择目录：

- 目录：`七参数_MLP_CNN流场重建/analysis_results/grid_independence/wall_boundary_diagnostic/baseline/`
- 边界目录：`wall_boundary_selection_catalog.csv`
- 诊断模型：`wall_boundary_diagnostic.mph`

诊断结论：

- 单个翼型局部 Box selection 通常选中 2 条边界。
- 24 个翼型局部 Box selection 合并后，显式翼型壁面边界集合数量为 48。
- broad Box selection 曾选中 50 条边界，说明其中可能混入非翼型壁面边界；显式集合更接近真实翼型壁面。

补充尝试：

- `BL_inside` 已在单工况脚本中使用 `condition="inside"` 限制局部 Box selection。
- 日志：`七参数_MLP_CNN流场重建/analysis_results/grid_independence/two_d_runs/baseline/BL_inside/stdout.log`
- 结果：边界选择数量为 48，但仍在 `mesh1.run()` 阶段失败。

脚本状态：

- `七参数_几何掩码代理优化/02a_七参数COMSOL单工况求解.py` 已支持 `--wall_bl_explicit`。
- `七参数_MLP_CNN流场重建/17_二维网格无关性运行器.py` 已支持 `--wall-bl-explicit` / `--wall_bl_explicit`，可将显式翼型壁面选择参数传递给单工况脚本。

### BL_explicit

命令：

```powershell
& "myenvs_fipynaca2.0\Scripts\python.exe" "七参数_MLP_CNN流场重建\17_二维网格无关性运行器.py" --levels "BL_explicit:4:3[mm]:0.3[mm]:0.8[mm]:0.08[mm]:3:1.5" --cases baseline --wall-bl-explicit --run --timeout 1800
```

结果：

- 状态：失败。
- 壁面 Box selection 选中边界数量：`48`。
- 显式翼型壁面边界集合数量：`48`。
- 失败阶段：`mesh1.run()`。
- 日志：`七参数_MLP_CNN流场重建/analysis_results/grid_independence/two_d_runs/baseline/BL_explicit/stdout.log`
- 判断：显式翼型壁面选择已经生效，失败不再来自“选错或选空边界”，而是当前边界层网格参数与域 1 空气域网格拓扑不兼容。

### BL_ultralight

命令：

```powershell
& "myenvs_fipynaca2.0\Scripts\python.exe" "七参数_MLP_CNN流场重建\17_二维网格无关性运行器.py" --levels "BL_ultralight:4:5[mm]:0.8[mm]:1.2[mm]:0.2[mm]:1:1.05" --cases baseline --wall-bl-explicit --run --timeout 1800
```

结果：

- 状态：失败。
- 壁面 Box selection 选中边界数量：`48`。
- 显式翼型壁面边界集合数量：`48`。
- 失败阶段：`mesh1.run()`。
- 日志：`七参数_MLP_CNN流场重建/analysis_results/grid_independence/two_d_runs/baseline/BL_ultralight/stdout.log`
- 判断：即使将边界层减到 `1` 层、`wall_bl_hminfact=1.05`，仍在空气域网格划分阶段失败。因此当前不再继续追加边界层补算，论文和 PPT 采用既有 G3/G4/G5 与三维粗/中/细网格数据作为网格敏感性说明。

当前仍不能写成“网格无关性通过”。后续若继续做网格问题，应转向重新设计局部尾迹细化区、固定压降后处理截面和检查几何小边，而不是在当前答辩材料中继续追加未收敛网格结果。
