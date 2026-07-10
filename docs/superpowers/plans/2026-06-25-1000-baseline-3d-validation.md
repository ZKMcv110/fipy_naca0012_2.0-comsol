# 1000 Baseline 3D Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 完成 1000 组 baseline 二维最优参数的三维建模、求解、导图和指标提取，形成可追溯三维复核证据链。

**Architecture:** 复用现有 `13_七参数真实芯片散热器建模.py` 读取 `optimization_results_1000_baseline/best_params.json` 并生成 `baseline_1000_best` 三维模型。修改 `15_提取七参数三维指标.py`，让它支持命令行传入任意候选 case，避免继续写死 `pi_cbam_best`。导图脚本 `14_导出七参数三维结果图.py` 已支持传入模型路径和前缀，直接复用。

**Tech Stack:** Python、COMSOL mph、PowerShell、pytest、现有七参数/三维脚本。

---

### Task 1: 让三维指标提取脚本支持任意候选 case

**Files:**
- Modify: `comsol_3d_airfoil_radiator/15_提取七参数三维指标.py`
- Test: `python -m py_compile comsol_3d_airfoil_radiator/15_提取七参数三维指标.py`

- [ ] **Step 1: 修改命令行参数和模型路径构建**

在脚本中新增 `argparse`，保留默认 baseline 路径，并允许传入多个候选模型：

```python
def parse_case_specs(specs: list[str]) -> dict[str, Path]:
    paths = {"baseline": MODEL_PATHS["baseline"]}
    for spec in specs:
        if "=" not in spec:
            raise ValueError(f"--case 必须使用 name=path 格式: {spec}")
        name, path = spec.split("=", 1)
        if not name.strip():
            raise ValueError(f"--case 名称不能为空: {spec}")
        paths[name.strip()] = Path(path)
    return paths
```

- [ ] **Step 2: 修改 `main()` 使用传入 case**

把原来的：

```python
results = [evaluate_case(client, case, path) for case, path in MODEL_PATHS.items()]
```

替换为：

```python
args = parser.parse_args()
model_paths = parse_case_specs(args.case)
results = [evaluate_case(client, case, path) for case, path in model_paths.items()]
write_outputs(add_ratios(results), Path(args.output_dir))
```

- [ ] **Step 3: 让 `write_outputs` 接收输出目录**

把 `write_outputs(results)` 改为 `write_outputs(results, out_dir)`，并把内部 `OUT_DIR` 改为传入目录。

- [ ] **Step 4: 运行语法检查**

Run:

```powershell
python -m py_compile "comsol_3d_airfoil_radiator\15_提取七参数三维指标.py"
```

Expected: 无输出，退出码 0。

### Task 2: 生成并求解 1000 组 baseline 三维模型

**Files:**
- Input: `七参数_几何掩码代理优化/optimization_results_1000_baseline/best_params.json`
- Output: `comsol_3d_airfoil_radiator/generated_7param_chip_heat_sink/baseline_1000_best/baseline_1000_best_realistic_airfoil_heat_sink.mph`

- [ ] **Step 1: 运行三维建模和求解**

Run:

```powershell
python "comsol_3d_airfoil_radiator\13_七参数真实芯片散热器建模.py" --case-name baseline_1000_best --params-json "七参数_几何掩码代理优化\optimization_results_1000_baseline\best_params.json" --mesh-hauto 5 --solve
```

Expected: 生成 `.mph` 和 `baseline_1000_best_realistic_build_notes.json`，其中 `solved=true`。

- [ ] **Step 2: 检查建模记录**

Run:

```powershell
Get-Content "comsol_3d_airfoil_radiator\generated_7param_chip_heat_sink\baseline_1000_best\baseline_1000_best_realistic_build_notes.json" -Raw -Encoding UTF8
```

Expected: `params.theta=-2.4482582302172773`，`mesh_generated=true`，`solved=true`。

### Task 3: 提取三维指标并生成三维复核结果

**Files:**
- Input: `comsol_3d_airfoil_radiator/generated_realistic_heat_sink/baseline/baseline_realistic_airfoil_heat_sink.mph`
- Input: `comsol_3d_airfoil_radiator/generated_7param_chip_heat_sink/baseline_1000_best/baseline_1000_best_realistic_airfoil_heat_sink.mph`
- Output: `comsol_3d_airfoil_radiator/generated_7param_chip_heat_sink/results_baseline_1000/seven_param_3d_summary.csv`

- [ ] **Step 1: 运行指标提取**

Run:

```powershell
python "comsol_3d_airfoil_radiator\15_提取七参数三维指标.py" --output-dir "comsol_3d_airfoil_radiator\generated_7param_chip_heat_sink\results_baseline_1000" --case "baseline_1000_best=comsol_3d_airfoil_radiator\generated_7param_chip_heat_sink\baseline_1000_best\baseline_1000_best_realistic_airfoil_heat_sink.mph"
```

Expected: 输出 CSV/JSON/MD，包含 `baseline` 和 `baseline_1000_best` 两行。

- [ ] **Step 2: 读取结果**

Run:

```powershell
Get-Content "comsol_3d_airfoil_radiator\generated_7param_chip_heat_sink\results_baseline_1000\seven_param_3d_summary.csv" -Encoding UTF8
```

Expected: 可看到 `eta_3d`、`r_th_ratio`、`delta_p_ratio`。

### Task 4: 导出最终三维图

**Files:**
- Input: `comsol_3d_airfoil_radiator/generated_7param_chip_heat_sink/baseline_1000_best/baseline_1000_best_realistic_airfoil_heat_sink.mph`
- Output: `comsol_3d_airfoil_radiator/generated_7param_chip_heat_sink/baseline_1000_best/exports/*.png`

- [ ] **Step 1: 导出图组**

Run:

```powershell
python "comsol_3d_airfoil_radiator\14_导出七参数三维结果图.py" --model "comsol_3d_airfoil_radiator\generated_7param_chip_heat_sink\baseline_1000_best\baseline_1000_best_realistic_airfoil_heat_sink.mph" --out-dir "comsol_3d_airfoil_radiator\generated_7param_chip_heat_sink\baseline_1000_best\exports" --prefix baseline_1000_best
```

Expected: 导出 `baseline_1000_best_appearance.png`、`baseline_1000_best_temperature.png`、`baseline_1000_best_velocity.png`、`baseline_1000_best_mesh.png`。

### Task 5: 验证和更新架构记录

**Files:**
- Modify: `项目架构.md`
- Verify: `tests/test_7param_mainline_contracts.py`

- [ ] **Step 1: 更新 `项目架构.md` 三维状态**

把“三维 baseline 复核还没做”改为真实结果：记录 `eta_3d`、热阻比、压降比和结果目录。

- [ ] **Step 2: 运行验证**

Run:

```powershell
python -m pytest tests/test_7param_mainline_contracts.py -q
python "七参数_几何掩码代理优化\18_七参数轻量冒烟测试.py"
```

Expected: pytest 通过，冒烟测试 `pass 7/7`。

### Self-Review

- Spec coverage: 覆盖了建模、求解、指标提取、导图、架构记录和验证。
- Placeholder scan: 无 TBD/TODO/以后补 等占位步骤。
- Type consistency: case 名称统一使用 `baseline_1000_best`，结果目录统一使用 `results_baseline_1000`。
