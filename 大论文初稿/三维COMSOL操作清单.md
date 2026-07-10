# 三维COMSOL操作清单

## 1. 建模入口

使用当前三维翼型柱散热器脚本：

```powershell
python .\comsol_3d_airfoil_radiator\build_airfoil_pillar_heat_sink.py --all --mesh-hauto 4
```

当前有效输出：

```text
comsol_3d_airfoil_radiator\generated_pillar_heat_sink\baseline\baseline_airfoil_pillar_heat_sink_current.mph
comsol_3d_airfoil_radiator\generated_pillar_heat_sink\optimal\optimal_airfoil_pillar_heat_sink.mph
```

## 2. 打开模型后先检查

- 空气通道是否为70 mm × 30 mm × 15 mm。
- 铝基座是否为22 mm × 18 mm × 2 mm。
- 底部芯片热源是否为15 mm × 15 mm × 2 mm。
- 翼型柱阵列是否为3×8。
- 热源是否选中底部芯片域，不应选到翼型柱。
- `fluid1`是否为空气域。
- `nitf1`是否为空气域。
- `sol1`求解器序列是否存在。

## 3. 当前边界和物理场设置

| 项目 | 设置 |
|---|---|
| 流动物理场 | Laminar Flow |
| 传热物理场 | Heat Transfer in Solids and Fluids |
| 多物理场耦合 | Nonisothermal Flow |
| 入口 | Fully developed flow，U0 = 5 cm/s |
| 出口 | Pressure outlet，p = 0 Pa |
| 热源 | 芯片域总热功率P0 = 1 W |
| 求解类型 | Stationary |

## 4. 求解前检查

在COMSOL中确认以下节点：

```text
ht/fluid1 = 空气域
ht/solid1 = 铝基座、翼型柱和芯片域
ht/hs1 = 芯片域，HeatRate，P0
spf/inl1 = 入口，FullyDevelopedFlow，U0
spf/out1 = 出口，Pressure
nitf1 = 空气域
sol1 = st1, v1, s1
```

## 5. 求解步骤

1. 先求解基准模型。
2. 基准模型收敛后，导出温度场、速度场和压力场。
3. 对基准模型做粗、中、细三组网格无关性。
4. 用选定网格求解优化模型。
5. 使用相同视角、相同色标和相同箭头过滤条件导出优化模型结果。

## 6. 推荐结果图

优先使用模型中已经建立的结果图：

```text
温度和流体流动
```

该图包含：

```text
壁温
固体温度
流体流动箭头
速度过滤：spf.U > 0.25*nitf1.Uave
```

不要使用过密的全域箭头图作为论文主图，否则会掩盖翼型柱附近的真实流动路径。

## 7. 后处理指标

建立或使用平均/最大值算子：

- 入口面平均压力：`p_in`
- 出口面平均压力：`p_out`
- 芯片平均温度：`T_chip,avg`
- 芯片最高温度：`T_chip,max`

计算：

```text
Δp = p_in - p_out
R_th = (T_chip,avg - T_in)/P0
η_3D = (R_th,0/R_th)/(Δp/Δp_0)^(1/3)
```

## 8. 论文最低补齐内容

- 图5-2：三维模型示意图或COMSOL模型截图。
- 图5-3：三维网格图和局部加密图。
- 图5-4：基准/优化温度指标对比。
- 图5-6至图5-8：速度场、温度场、压力场对比。
- 表5-4：网格无关性。
- 表5-5：基准/优化三维验证结果。
