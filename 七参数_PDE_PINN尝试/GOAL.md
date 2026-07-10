# Goal: 二维 PDE 残差 PINN 探索（共轭传热）

在不影响现有 PI-CNN-CBAM 主流程的前提下，尝试用 PINN 直接求解二维稳态不可压层流控制方程，学习翼型管阵列的 u(x,y)、v(x,y)、p(x,y)、T(x,y) 场，评估其作为代理模型的可行性。

**重要声明：本目录是探索性方法验证，不替代现有 PI-CNN-CBAM 主结论。**

## Context

- 现有 PI-CNN-CBAM 只预测标量 Nu/f，不输出场变量
- COMSOL 模型求解完整共轭传热：Non-Isothermal Laminar Flow（Navier-Stokes + 能量方程）
- 1000 个 .mph 文件包含完整 u, v, p, T 数值场（已验证）
- u, v, p 仅在流体域有定义（固体域返回 NaN），T 全域有定义
- 本项目独立于 `七参数_几何掩码代理优化/` 和 `PINN温度场/`

## 控制方程（二维稳态不可压层流）

连续性方程：
  ∂u/∂x + ∂v/∂y = 0

x-动量方程：
  ρ(u·∂u/∂x + v·∂u/∂y) = -∂p/∂x + μ(∂²u/∂x² + ∂²u/∂y²)

y-动量方程：
  ρ(u·∂v/∂x + v·∂v/∂y) = -∂p/∂y + μ(∂²v/∂x² + ∂²v/∂y²)

能量方程（流体域）：
  ρ·cp(u·∂T/∂x + v·∂T/∂y) = k_air(∂²T/∂x² + ∂²T/∂y²)

能量方程（固体域）：
  k_alum(∂²T/∂x² + ∂²T/∂y²) + Q_heat = 0

## Tasks

### Task 1: 全场数据导出（venv Python）

- [ ] 创建 `01_导出全场数据.py`
  - 遍历 1000 个 case 的 .mph 文件
  - 在流道区域生成 80×50=4000 点规则网格
  - 用 CutPoint2D + EvalPoint 同时提取 u, v, p, T
  - 流体域点：u, v, p, T 均有值
  - 固体域点：T 有值，u/v/p 为 NaN
  - 用 domain 标记区分（0=空气, 1=固体）
  - 保存 `field_data/case_{id}_full.npz`（x, y, u, v, p, T, domain）
- [ ] 运行导出
- [ ] 验证：抽查 case_20001，u 在入口 ≈ 5m/s，p 沿流向递减，T 在翼型附近升高

### Task 2: 单工况 PDE-PINN（Anaconda GPU）

- [ ] 创建 `02_单工况PDE_PINN.py`
  - 输入：(x, y) → 输出：(u, v, p, T)
  - 网络：Linear(2→256) + Tanh × 6 + Linear(256→4)
  - PDE 残差损失：
    - L_continuity = MSE(∂u/∂x + ∂v/∂y, 0)
    - L_momentum_x = MSE(ρ(u·∂u/∂x + v·∂u/∂y) + ∂p/∂x - μ·∇²u, 0)
    - L_momentum_y = MSE(ρ(u·∂v/∂x + v·∂v/∂y) + ∂p/∂y - μ·∇²v, 0)
    - L_energy_air = MSE(ρ·cp·(u·∂T/∂x + v·∂T/∂y) - k_air·∇²T, 0)
    - L_energy_solid = MSE(k_alum·∇²T + Q_heat, 0)
  - 边界条件损失：
    - L_bc_inlet = MSE(u - U_in, 0) + MSE(v, 0) + MSE(T - T_amb, 0)
    - L_bc_wall = MSE(u, 0) + MSE(v, 0)  （无滑移）
  - 数据监督损失：L_data = MSE(pred, comsol) for u, v, p, T
  - 自适应损失权重（Uncertainty Weighting 或 GradNorm）
  - 训练：AdamW + CosineAnnealing，500 epoch
  - 评估：场变量 R²/MAE/RMSE + PDE 残差分布
- [ ] 运行单工况训练
- [ ] 验证：loss 收敛，T R² > 0.95，u R² > 0.90

### Task 3: 多参数 PDE-PINN

- [ ] 创建 `03_多参数PDE_PINN.py`
  - 输入：7 参数(Z-score) + (x, y)(归一化) → 输出：(u, v, p, T)
  - 网络：Linear(9→256) + Tanh × 6 + Linear(256→4)
  - 损失函数同 Task 2
  - 训练：全 1000 case，batch=16 cases
- [ ] 运行训练
- [ ] 验证：测试集 T R² > 0.95，u R² > 0.90

### Task 4: 评估与对比

- [ ] 从预测场计算 Nu（T_wing → h → Nu）和 f（Δp → f）
- [ ] 与 PI-CNN-CBAM 消融实验对比（baseline Nu R²=0.972, f R²=0.981）
- [ ] 生成可视化：u/v/p/T 预测场图 vs COMSOL 真值，PDE 残差分布图
- [ ] 明确总结 PDE-PINN 的优势、成本和局限

## Files

| 文件 | 作用 | 环境 |
|---|---|---|
| `GOAL.md` | 本文件 | — |
| `common_pde.py` | 路径常量、物理参数、网格生成、归一化 | 通用 |
| `01_导出全场数据.py` | COMSOL 全场数据导出 | venv |
| `02_单工况PDE_PINN.py` | 单工况 PINN 训练 | Anaconda GPU |
| `03_多参数PDE_PINN.py` | 多参数 PINN 训练 | Anaconda GPU |
| `field_data/*.npz` | 导出的全场数据 | — |
| `results/` | 训练产物和可视化 | — |

## 只读依赖（不修改）

- `七参数_几何掩码代理优化/common.py` — 翼型几何函数
- `七参数_几何掩码代理优化/samples/labels_7param_1000.csv` — 参数+标量标签
- `七参数_几何掩码代理优化/comsol_results_*/cfd_solution/model.mph` — COMSOL 求解结果

## 物理参数

| 参数 | 值 | 含义 |
|---|---|---|
| ρ | 1.2 kg/m³ | 空气密度 |
| μ | 1.8e-5 Pa·s | 空气动力粘度 |
| cp | 1005 J/(kg·K) | 空气比热容 |
| k_air | 0.026 W/(m·K) | 空气导热系数 |
| k_alum | 238 W/(m·K) | 铝导热系数 |
| Q_heat | 1e7 W/m³ | 热源体积功率 |
| U_in | 5.0 m/s | 入口速度 |
| T_amb | 293.15 K | 入口/环境温度 |
