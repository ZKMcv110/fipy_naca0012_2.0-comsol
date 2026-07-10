# Realistic Chip Airfoil Heat Sink Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增一套独立的芯片级强制风冷翼型鳍片散热器三维复核模型，使用 1000 组 baseline 最优参数，统一物理口径、Nu3D/f3D/eta3D 后处理和论文图输出。

**Architecture:** 新脚本不覆盖旧模型，输出到 `generated_chip_airfoil_heat_sink/`。建模复用现有 COMSOL mph + Java API 风格，选择集命名保持 `sel_chip/sel_inlet/sel_outlet/sel_air`，因此可直接复用 `15_提取七参数三维指标.py` 和 `14_导出七参数三维结果图.py`。几何上加入芯片、铜热扩散片、铝底座、翼型鳍片阵列和封闭风道。

**Tech Stack:** Python、COMSOL mph、jpype、现有七参数三维后处理脚本。

---

### Task 1: 新增独立真实感建模入口

**Files:**
- Create: `comsol_3d_airfoil_radiator/18_芯片级翼型鳍片散热器建模.py`

- [ ] **Step 1: 创建脚本**

脚本读取 `optimization_results_1000_baseline/best_params.json`，构建 `chip_baseline_1000` 工况，几何包括空气风道、芯片、铜热扩散片、铝底座和翼型鳍片阵列。

- [ ] **Step 2: 设置统一物理口径**

采用旧三维成功口径作为基准：`U0=5[cm/s]`、`T_in=293.15[K]`、`P0=1[W]`、FullyDevelopedFlow 入口、压力出口、共轭传热、弱可压缩层流。

- [ ] **Step 3: 创建图组**

创建 `pg_geometry_preview`、`pg_clean_temp`、`pg_clean_vel`、`pg_clean_pressure`、`pg_mesh_check`，保证既能导出外观，也能看流动是否穿过散热器。

### Task 2: 求解和后处理

**Files:**
- Output: `comsol_3d_airfoil_radiator/generated_chip_airfoil_heat_sink/chip_baseline_1000/chip_baseline_1000_realistic_heat_sink.mph`
- Output: `comsol_3d_airfoil_radiator/generated_chip_airfoil_heat_sink/results/chip_heat_sink_3d_summary.csv`

- [ ] **Step 1: 运行建模求解**

Run:

```powershell
python "comsol_3d_airfoil_radiator\18_芯片级翼型鳍片散热器建模.py" --solve
```

- [ ] **Step 2: 运行后处理**

Run:

```powershell
python "comsol_3d_airfoil_radiator\15_提取七参数三维指标.py" --output-dir "comsol_3d_airfoil_radiator\generated_chip_airfoil_heat_sink\results" --case "chip_baseline_1000=comsol_3d_airfoil_radiator\generated_chip_airfoil_heat_sink\chip_baseline_1000\chip_baseline_1000_realistic_heat_sink.mph"
```

### Task 3: 导图和验证

**Files:**
- Output: `comsol_3d_airfoil_radiator/generated_chip_airfoil_heat_sink/chip_baseline_1000/exports/*.png`
- Modify: `项目架构.md`

- [ ] **Step 1: 导出图**

Run:

```powershell
python "comsol_3d_airfoil_radiator\14_导出七参数三维结果图.py" --model "comsol_3d_airfoil_radiator\generated_chip_airfoil_heat_sink\chip_baseline_1000\chip_baseline_1000_realistic_heat_sink.mph" --out-dir "comsol_3d_airfoil_radiator\generated_chip_airfoil_heat_sink\chip_baseline_1000\exports" --prefix chip_baseline_1000
```

- [ ] **Step 2: 更新架构文件**

记录新模型定位、物理口径、输出目录和 Nu3D/f3D/eta3D 结果。

- [ ] **Step 3: 验证**

Run:

```powershell
python -m py_compile "comsol_3d_airfoil_radiator\18_芯片级翼型鳍片散热器建模.py"
python -m pytest tests/test_7param_mainline_contracts.py -q
python "七参数_几何掩码代理优化\18_七参数轻量冒烟测试.py"
```

Expected: 编译通过，pytest 通过，冒烟测试通过。
