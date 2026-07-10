#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""PDE-PINN 探索项目共用工具。

包含：路径常量、物理参数、采样网格、归一化、数据加载。
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

# ──────────────────── 路径常量 ────────────────────

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
PARAM_DIR = PROJECT_ROOT / "七参数_几何掩码代理优化"

COMSOL_DIRS = [
    PARAM_DIR / "comsol_results_theta500_v2",
    PARAM_DIR / "comsol_results_1000_extra",
]

LABELS_1000 = PARAM_DIR / "samples" / "labels_7param_1000.csv"
SPLIT_1000 = PARAM_DIR / "samples" / "dataset_split_1000.csv"

FIELD_DATA_DIR = ROOT / "field_data"
RESULTS_DIR = ROOT / "results"

# ──────────────────── 参数定义 ────────────────────

PARAM_COLS = ["Ta", "Twa", "Tb", "Ts", "Tt", "Tad", "theta"]

# ──────────────────── 物理参数（与 COMSOL 模型一致）────────────────────

CHORD = 0.01          # 弦长 [m]
RHO_AIR = 1.2         # 空气密度 [kg/m³]
MU_AIR = 1.8e-5       # 空气动力粘度 [Pa·s]
CP_AIR = 1005.0       # 空气比热容 [J/(kg·K)]
K_AIR = 0.026         # 空气导热系数 [W/(m·K)]
K_ALUM = 238.0        # 铝导热系数 [W/(m·K)]
Q_HEAT = 1e7          # 热源体积功率 [W/m³]
U_IN = 5.0            # 入口速度 [m/s]
T_AMB = 293.15        # 入口/环境温度 [K]

# 运动粘度
NU_AIR = MU_AIR / RHO_AIR   # [m²/s]
ALPHA_AIR = K_AIR / (RHO_AIR * CP_AIR)  # 热扩散率 [m²/s]

# ──────────────────── 采样网格 ────────────────────

GRID_NX = 80
GRID_NY = 50


def channel_bounds(Ta: float, Tb: float, Ts: float, Tt: float,
                   Tad: float, theta: float) -> tuple[float, float, float, float]:
    """计算流道矩形区域的 (x_min, x_max, y_min, y_max)。"""
    c = CHORD
    x_min = -5 * c
    x_max = (8 * (1 + Ts) + Tad + 15) * c + x_min
    half_h = (Tt + Ta + Tb + 0.35 + 0.6 * abs(np.sin(np.radians(theta)))) * c
    y_min = -half_h
    y_max = half_h
    return x_min, x_max, y_min, y_max


def make_grid(Ta: float, Tb: float, Ts: float, Tt: float,
              Tad: float, theta: float,
              nx: int = GRID_NX, ny: int = GRID_NY) -> tuple[np.ndarray, np.ndarray]:
    """在流道区域内生成规则采样网格。"""
    x_min, x_max, y_min, y_max = channel_bounds(Ta, Tb, Ts, Tt, Tad, theta)
    xs = np.linspace(x_min, x_max, nx, dtype=np.float32)
    ys = np.linspace(y_min, y_max, ny, dtype=np.float32)
    xx, yy = np.meshgrid(xs, ys)
    return xx.ravel(), yy.ravel()


# ──────────────────── 归一化 ────────────────────

def compute_param_stats(df: pd.DataFrame, train_idx: list[int]) -> dict:
    """从训练集计算参数 Z-score 统计。"""
    train_df = df.iloc[train_idx]
    return {
        "param_mean": train_df[PARAM_COLS].mean().to_numpy(dtype=np.float32).tolist(),
        "param_std": (train_df[PARAM_COLS].std().to_numpy(dtype=np.float32) + 1e-8).tolist(),
    }


def compute_xy_bounds(df: pd.DataFrame) -> dict:
    """从全部 case 的参数范围计算 x/y 坐标的全局归一化边界。"""
    x_mins, x_maxs, y_mins, y_maxs = [], [], [], []
    for _, row in df.iterrows():
        x_min, x_max, y_min, y_max = channel_bounds(
            row["Ta"], row["Tb"], row["Ts"], row["Tt"], row["Tad"], row["theta"],
        )
        x_mins.append(x_min)
        x_maxs.append(x_max)
        y_mins.append(y_min)
        y_maxs.append(y_max)
    return {
        "x_min": float(min(x_mins)),
        "x_max": float(max(x_maxs)),
        "y_min": float(min(y_mins)),
        "y_max": float(max(y_maxs)),
    }


def normalize_xy(x: np.ndarray, y: np.ndarray, bounds: dict) -> tuple[np.ndarray, np.ndarray]:
    """将 x, y 归一化到 [-1, 1]。"""
    x_norm = 2.0 * (x - bounds["x_min"]) / (bounds["x_max"] - bounds["x_min"] + 1e-8) - 1.0
    y_norm = 2.0 * (y - bounds["y_min"]) / (bounds["y_max"] - bounds["y_min"] + 1e-8) - 1.0
    return x_norm.astype(np.float32), y_norm.astype(np.float32)


# ──────────────────── 数据分割 ────────────────────

def load_split(split_file: Path, df: pd.DataFrame) -> tuple[list[int], list[int], list[int]]:
    """读取已有的数据集划分。"""
    split_df = pd.read_csv(split_file)
    id_to_idx = {int(row.case_id): idx for idx, row in df.iterrows()}
    splits = []
    for name in ["train", "val", "test"]:
        ids = split_df.loc[split_df["split"] == name, "case_id"].astype(int).tolist()
        splits.append([id_to_idx[cid] for cid in ids if cid in id_to_idx])
    return tuple(splits)


# ──────────────────── 物理量特征尺度 ────────────────────

def compute_field_scales(df: pd.DataFrame) -> dict:
    """计算场变量的特征尺度，用于 PDE 残差归一化。

    基于入口条件和特征长度（弦长）估算各物理量的典型量级。
    """
    L = CHORD
    U = U_IN
    P_scale = RHO_AIR * U**2          # 动压 [Pa]
    T_scale = Q_HEAT * L**2 / K_ALUM  # 特征温升 [K]
    return {
        "u_scale": U,
        "v_scale": U * 0.1,           # v 通常比 u 小一个量级
        "p_scale": P_scale,
        "T_scale": max(T_scale, 10.0),
        "L_scale": L,
        "continuity_scale": U / L,
        "momentum_scale": RHO_AIR * U**2 / L,
        "energy_air_scale": RHO_AIR * CP_AIR * U * T_scale / L,
        "energy_solid_scale": K_ALUM * T_scale / L**2,
    }


# ──────────────────── 边界检测 ────────────────────

def detect_boundary_points(
    x: np.ndarray, y: np.ndarray, domain: np.ndarray,
    x_min: float, x_max: float, y_min: float, y_max: float,
    nx: int = GRID_NX, ny: int = GRID_NY
) -> dict[str, np.ndarray]:
    """精确检测边界点。
    
    返回：
    - inlet_mask: 入口边界（x最左列的空气域点）
    - outlet_mask: 出口边界（x最右列的空气域点）
    - wall_mask: 壁面边界（固体域表面的空气域相邻点）
    - top_mask: 顶部边界
    - bottom_mask: 底部边界
    """
    # 计算网格步长
    dx = (x_max - x_min) / (nx - 1)
    dy = (y_max - y_min) / (ny - 1)
    
    # 入口：x <= x_min + 1.5*dx（最左列及其右侧紧邻列）
    inlet_mask = (x <= x_min + 1.5 * dx) & (domain == 0)
    
    # 出口：x >= x_max - 1.5*dx（最右列及其左侧紧邻列）
    outlet_mask = (x >= x_max - 1.5 * dx) & (domain == 0)
    
    # 顶部边界：y >= y_max - 1.5*dy
    top_mask = (y >= y_max - 1.5 * dy) & (domain == 0)
    
    # 底部边界：y <= y_min + 1.5*dy
    bottom_mask = (y <= y_min + 1.5 * dy) & (domain == 0)
    
    # 壁面：空气域中与固体域相邻的点（使用4邻域检测）
    wall_mask = detect_solid_interface(x, y, domain, nx, ny)
    
    return {
        "inlet": inlet_mask,
        "outlet": outlet_mask,
        "wall": wall_mask,
        "top": top_mask,
        "bottom": bottom_mask,
    }


def detect_solid_interface(
    x: np.ndarray, y: np.ndarray, domain: np.ndarray,
    nx: int, ny: int
) -> np.ndarray:
    """检测空气域中与固体域直接相邻的点（壁面边界）。
    
    使用4邻域检测：如果一个空气域点的上下左右任一邻居是固体域点，
    则该点为壁面边界点。
    """
    # 恢复网格结构
    domain_grid = domain.reshape(ny, nx)
    
    # 创建边界标记
    wall_grid = np.zeros_like(domain_grid, dtype=bool)
    
    # 4邻域偏移
    offsets = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    
    for i in range(ny):
        for j in range(nx):
            if domain_grid[i, j] == 0:  # 空气域点
                for di, dj in offsets:
                    ni, nj = i + di, j + dj
                    if 0 <= ni < ny and 0 <= nj < nx:
                        if domain_grid[ni, nj] == 1:  # 邻居是固体
                            wall_grid[i, j] = True
                            break
    
    return wall_grid.ravel()


def compute_boundary_masks(
    x: np.ndarray, y: np.ndarray, domain: np.ndarray,
    nx: int = GRID_NX, ny: int = GRID_NY
) -> dict[str, np.ndarray]:
    """简化接口：自动计算边界框后调用detect_boundary_points。"""
    x_min, x_max = x.min(), x.max()
    y_min, y_max = y.min(), y.max()
    return detect_boundary_points(x, y, domain, x_min, x_max, y_min, y_max, nx, ny)


# ──────────────────── JSON 工具 ────────────────────

def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # 转换 numpy 类型为 Python 原生类型
    def convert_numpy(obj):
        if isinstance(obj, dict):
            return {k: convert_numpy(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [convert_numpy(v) for v in obj]
        elif isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return convert_numpy(obj.tolist())
        else:
            return obj
    
    converted_data = convert_numpy(data)
    path.write_text(json.dumps(converted_data, indent=2, ensure_ascii=False), encoding="utf-8")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
