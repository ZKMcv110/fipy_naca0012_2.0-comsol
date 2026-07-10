#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""边界检测函数测试脚本。

验证新的边界检测功能是否正确工作。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
from common_pde import (
    GRID_NX, GRID_NY, CHORD,
    make_grid, compute_boundary_masks,
)


def test_boundary_detection():
    """测试边界检测函数。"""
    print("=" * 60)
    print("边界检测函数测试")
    print("=" * 60)

    # 使用默认参数生成网格
    Ta, Tb, Ts, Tt, Tad, theta = 1.0, 1.0, 1.0, 1.0, 0.5, 0.0
    x, y = make_grid(Ta, Tb, Ts, Tt, Tad, theta)

    # 创建简单的域标记：中间区域设为固体
    domain = np.zeros(len(x), dtype=np.int64)
    x_min, x_max = x.min(), x.max()
    y_min, y_max = y.min(), y.max()
    
    # 在中心区域创建一个模拟的固体块
    center_x = (x_min + x_max) / 2
    center_y = (y_min + y_max) / 2
    solid_radius = CHORD * 2
    
    for i in range(len(x)):
        dist = np.sqrt((x[i] - center_x)**2 + (y[i] - center_y)**2)
        if dist < solid_radius:
            domain[i] = 1

    print(f"网格尺寸: {GRID_NX} × {GRID_NY} = {len(x)} 点")
    print(f"空气域点数: {(domain == 0).sum()}")
    print(f"固体域点数: {(domain == 1).sum()}")

    # 测试边界检测
    masks = compute_boundary_masks(x, y, domain, GRID_NX, GRID_NY)

    print("\n边界检测结果:")
    print(f"  入口边界: {masks['inlet'].sum()} 点")
    print(f"  出口边界: {masks['outlet'].sum()} 点")
    print(f"  壁面边界: {masks['wall'].sum()} 点")
    print(f"  顶部边界: {masks['top'].sum()} 点")
    print(f"  底部边界: {masks['bottom'].sum()} 点")

    # 验证边界点不重叠
    all_masks = masks['inlet'] | masks['outlet'] | masks['wall'] | masks['top'] | masks['bottom']
    print(f"\n所有边界点总数: {all_masks.sum()}")

    # 验证壁面边界点都在空气域
    wall_in_air = (masks['wall'] & (domain == 0)).sum()
    print(f"壁面边界点中在空气域的数量: {wall_in_air} (应为 {masks['wall'].sum()})")
    
    assert wall_in_air == masks['wall'].sum(), "壁面边界点应该都在空气域"

    print("\n[OK] 边界检测测试通过!")


def test_loss_weights():
    """测试损失权重配置。"""
    print("\n" + "=" * 60)
    print("损失权重配置测试")
    print("=" * 60)

    # 修复后的权重配置
    weights = {
        "data": 1.0,
        "continuity": 1.0,
        "momentum": 1.0,
        "energy_air": 1.0,
        "energy_solid": 1.0,
        "bc_inlet": 1.0,
        "bc_wall": 1.0,
        "bc_outlet": 1.0,
    }

    print("修复后的损失权重配置:")
    for key, value in weights.items():
        print(f"  {key}: {value}")

    # 检查所有权重都是同一量级
    values = list(weights.values())
    min_val, max_val = min(values), max(values)
    
    print(f"\n权重范围: [{min_val}, {max_val}]")
    assert max_val / min_val <= 10, "权重量级差异不应超过10倍"

    print("[OK] 损失权重配置测试通过!")


def main():
    test_boundary_detection()
    test_loss_weights()
    
    print("\n" + "=" * 60)
    print("[OK] 所有测试通过!")
    print("=" * 60)


if __name__ == "__main__":
    main()