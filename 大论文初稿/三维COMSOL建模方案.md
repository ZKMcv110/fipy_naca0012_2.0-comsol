# 三维COMSOL建模方案

## 1. 建模定位

第5章三维模型采用强制风冷散热器代表性模型，不再采用旧的“二维翼型阵列直接拉伸成长通道”路线。当前模型用于验证翼型柱阵列在三维空气通道、铝基座和底部芯片热源条件下的相对流热性能。

该三维模型不代表完整工程车辆动力舱，也不包含风扇、水室、集流管和冷却液回路。其目的在于建立可求解、可展示、传热路径清晰的三维共轭换热模型，为第5章工程适用性分析提供模型基础。

## 2. 当前有效模型

建模脚本：

```text
comsol_3d_airfoil_radiator/build_airfoil_pillar_heat_sink.py
```

当前有效模型文件：

```text
comsol_3d_airfoil_radiator/generated_pillar_heat_sink/baseline/baseline_airfoil_pillar_heat_sink_current.mph
comsol_3d_airfoil_radiator/generated_pillar_heat_sink/optimal/optimal_airfoil_pillar_heat_sink.mph
```

旧目录`generated`和`generated_parametric`属于早期建模路线，论文第5章不再采用。

## 3. 几何尺寸

| 项目 | 当前设置 | 说明 |
|---|---:|---|
| 空气通道 | 70 mm × 30 mm × 15 mm | 长度×宽度×高度 |
| 芯片热源 | 15 mm × 15 mm × 2 mm | 位于铝基座下方 |
| 铝基座 | 22 mm × 18 mm × 2 mm | 略大于芯片热源 |
| 翼型柱阵列 | 3×8 | 位于铝基座上表面 |
| 翼型弦长 | 1.2 mm | 用于适配小型基座 |
| 翼型柱高度 | 8 mm | 竖直拉伸 |

## 4. 参数设置

基准结构：

```text
Ta = 0.000, Twa = 0.40, Tb = 0.12, Ts = 1.10, Tt = 0.85, Tad = 0.00
```

优化结构：

```text
Ta = 0.000, Twa = 0.40, Tb = 0.12, Ts = 1.10, Tt = 0.85, Tad = 0.50
```

三维验证阶段暂不引入弯度变化，主要考察交错位移对三维风冷散热模型的影响。第4章二维最优结构中的弯度变化可作为后续三维扩展内容。

## 5. 物理场和材料

- 物理场：
  - Laminar Flow
  - Heat Transfer in Solids and Fluids
  - Nonisothermal Flow
- 求解类型：Stationary
- 空气域：非固体材料，参与层流流动和流体传热。
- 铝基座和翼型柱：铝材料，参与固体导热。
- 芯片域：固体材料，施加总热功率。

当前模型已验证：

```text
fluid1 = [空气域]
hs1 = [芯片热源域]
nitf1 = [空气域]
solver = sol1
```

## 6. 边界条件

| 位置 | 流动条件 | 热边界条件 |
|---|---|---|
| 入口面 | 充分发展入口，U0 = 5 cm/s | 入口温度293.15 K |
| 出口面 | 压力出口，p = 0 Pa | Convective outflow |
| 固体-空气界面 | 无滑移 | 温度连续、热流连续 |
| 芯片域 | 不参与流动 | 总热功率P0 = 1 W |

## 7. 网格建议

- 当前脚本可生成自由四面体网格。
- 正式求解前建议检查翼型柱前缘、尾缘、基座上表面和芯片接触区域网格。
- 三维网格无关性至少采用粗、中、细三组模型。
- 判据建议采用芯片最高温度、等效热阻和压降。

## 8. 后处理指标

建议优先报告：

```text
T_chip,max
T_chip,avg
R_th = (T_chip,avg - T_in)/P0
Δp = p_in - p_out
η_3D = (R_th,0/R_th)/(Δp/Δp_0)^(1/3)
```

若继续使用Nu形式，应明确其为等效Nu，并给出有效换热面积和平均温差的定义。

## 9. 最小计算任务

1. 求解基准结构。
2. 对基准结构做粗、中、细三组网格无关性验证。
3. 求解优化结构。
4. 导出基准/优化结构速度场、温度场、压力场。
5. 填写表5-4和表5-5。
