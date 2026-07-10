#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""单工况 PDE-PINN：输入 (x, y) → 输出 (u, v, p, T)。

用完整二维稳态不可压层流控制方程做 PDE 约束：
  - 连续性方程：∂u/∂x + ∂v/∂y = 0
  - x-动量方程：ρ(u·∂u/∂x + v·∂u/∂y) = -∂p/∂x + μ·∇²u
  - y-动量方程：ρ(u·∂v/∂x + v·∂v/∂y) = -∂p/∂y + μ·∇²v
  - 能量方程（流体）：ρ·cp·(u·∂T/∂x + v·∂T/∂y) = k_air·∇²T
  - 能量方程（固体）：k_alum·∇²T + Q = 0

训练：AdamW + CosineAnnealingLR，500 epoch。
支持 GradNorm 自适应损失权重。

运行环境：Anaconda Python（GPU）
用法：
    python 02_单工况PDE_PINN.py --case-id 20001
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common_pde import (
    CHORD, RHO_AIR, MU_AIR, CP_AIR, K_AIR, K_ALUM, Q_HEAT, U_IN, T_AMB,
    GRID_NX, GRID_NY, FIELD_DATA_DIR, RESULTS_DIR, write_json,
    compute_boundary_masks,
)


# ──────────────────── 网络 ────────────────────


class NavierStokesPINN(nn.Module):
    """全连接 PINN：(x, y) → (u, v, p, T)。

    6 层隐藏层 × 256 神经元 + Tanh 激活。
    Tanh 保证二阶导数存在（动量方程和能量方程需要 Laplacian）。
    
    使用输出缩放层来平衡不同变量的尺度：
    - u: ~0-8.6 m/s
    - v: ~-3-2 m/s  
    - p: ~-15-40
    - T: ~293-329 K
    """

    # 输出缩放参数（根据数据统计）
    # 网络内部学习归一化值，输出时缩放回原始范围
    OUT_MEAN = torch.tensor([4.0, 0.0, 12.0, 311.0])  # 近似均值
    OUT_SCALE = torch.tensor([4.0, 2.0, 25.0, 18.0])  # 近似标准差/范围

    def __init__(self, hidden: int = 256, n_layers: int = 6):
        super().__init__()
        layers: list[nn.Module] = [nn.Linear(2, hidden), nn.Tanh()]
        for _ in range(n_layers - 1):
            layers.extend([nn.Linear(hidden, hidden), nn.Tanh()])
        layers.append(nn.Linear(hidden, 4))
        self.net = nn.Sequential(*layers)
        
        # Xavier 初始化，保证 Tanh 激活后导数不会太小
        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_normal_(m.weight, gain=1.0)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)

    def forward(self, xy: torch.Tensor) -> torch.Tensor:
        """xy: (N, 2) → output: (N, 4) = [u, v, p, T]。
        
        网络内部学习归一化值，输出时缩放回原始物理范围。
        """
        out_normalized = self.net(xy)
        
        # 将归一化输出缩放回物理范围
        # 假设网络输出范围是 [-1, 1]，缩放后映射到实际范围
        mean = self.OUT_MEAN.to(xy.device)
        scale = self.OUT_SCALE.to(xy.device)
        out = out_normalized * scale + mean
        
        return out


# ──────────────────── PDE 残差 ────────────────────


def compute_pde_residuals(
    model: NavierStokesPINN,
    xy: torch.Tensor,
    domain: torch.Tensor,
) -> dict[str, torch.Tensor]:
    """计算归一化 PDE 残差。

    每个残差除以其物理特征尺度，使残差量级 ≈ O(1)。
    这样损失权重可以用 1.0 级别的值，避免 1e-12 等极端权重。
    """
    L = CHORD
    # 特征尺度（使用物理尺度，确保残差量级合理）
    cont_scale = U_IN / L                              # ≈ 500
    mom_scale = RHO_AIR * U_IN**2 / L                  # ≈ 3000
    T_rise = Q_HEAT * L**2 / K_ALUM                    # ≈ 42 K
    energy_air_scale = RHO_AIR * CP_AIR * U_IN * T_rise / L  # ≈ 2.5e7
    energy_solid_scale = Q_HEAT                         # 1e7

    xy.requires_grad_(True)
    out = model(xy)
    u = out[:, 0]
    v = out[:, 1]
    p = out[:, 2]
    T = out[:, 3]

    # 一阶偏导
    grads_u = torch.autograd.grad(u.sum(), xy, create_graph=True)[0]
    grads_v = torch.autograd.grad(v.sum(), xy, create_graph=True)[0]
    grads_p = torch.autograd.grad(p.sum(), xy, create_graph=True)[0]
    grads_T = torch.autograd.grad(T.sum(), xy, create_graph=True)[0]

    du_dx, du_dy = grads_u[:, 0], grads_u[:, 1]
    dv_dx, dv_dy = grads_v[:, 0], grads_v[:, 1]
    dp_dx, dp_dy = grads_p[:, 0], grads_p[:, 1]
    dT_dx, dT_dy = grads_T[:, 0], grads_T[:, 1]

    # 二阶偏导
    d2u_dx2 = torch.autograd.grad(du_dx.sum(), xy, create_graph=True, retain_graph=True)[0][:, 0]
    d2u_dy2 = torch.autograd.grad(du_dy.sum(), xy, create_graph=True, retain_graph=True)[0][:, 1]
    d2v_dx2 = torch.autograd.grad(dv_dx.sum(), xy, create_graph=True, retain_graph=True)[0][:, 0]
    d2v_dy2 = torch.autograd.grad(dv_dy.sum(), xy, create_graph=True, retain_graph=True)[0][:, 1]
    d2T_dx2 = torch.autograd.grad(dT_dx.sum(), xy, create_graph=True, retain_graph=True)[0][:, 0]
    d2T_dy2 = torch.autograd.grad(dT_dy.sum(), xy, create_graph=True, retain_graph=True)[0][:, 1]

    lap_u = d2u_dx2 + d2u_dy2
    lap_v = d2v_dx2 + d2v_dy2
    lap_T = d2T_dx2 + d2T_dy2

    air = domain == 0
    solid = domain == 1

    residuals = {}

    # 归一化残差 = 物理残差 / 特征尺度
    residuals["continuity"] = (du_dx + dv_dy)[air] / cont_scale

    mom_x_raw = RHO_AIR * (u[air] * du_dx[air] + v[air] * du_dy[air]) + dp_dx[air] - MU_AIR * lap_u[air]
    residuals["momentum_x"] = mom_x_raw / mom_scale

    mom_y_raw = RHO_AIR * (u[air] * dv_dx[air] + v[air] * dv_dy[air]) + dp_dy[air] - MU_AIR * lap_v[air]
    residuals["momentum_y"] = mom_y_raw / mom_scale

    energy_air_raw = (
        RHO_AIR * CP_AIR * (u[air] * dT_dx[air] + v[air] * dT_dy[air])
        - K_AIR * lap_T[air]
    )
    residuals["energy_air"] = energy_air_raw / energy_air_scale

    energy_solid_raw = K_ALUM * lap_T[solid] + Q_HEAT
    residuals["energy_solid"] = energy_solid_raw / energy_solid_scale

    # 同时返回原始值用于可视化
    residuals["raw"] = {
        "du_dx": du_dx, "du_dy": du_dy,
        "dv_dx": dv_dx, "dv_dy": dv_dy,
        "dp_dx": dp_dx, "dp_dy": dp_dy,
        "dT_dx": dT_dx, "dT_dy": dT_dy,
        "lap_u": lap_u, "lap_v": lap_v, "lap_T": lap_T,
        "u": u, "v": v, "p": p, "T": T,
    }

    return residuals


# ──────────────────── GradNorm 自适应权重 ────────────────────


class GradNormLossWeights:
    """GradNorm 自适应损失权重机制。
    
    参考：https://arxiv.org/abs/1711.02257
    自动平衡多个损失项的梯度范数，使它们大致相等。
    """

    def __init__(self, losses: list[str], alpha: float = 0.1):
        self.weights = torch.tensor([1.0] * len(losses), requires_grad=True)
        self.loss_names = losses
        self.alpha = alpha
        self.device = torch.device("cpu")

    def to(self, device):
        self.device = device
        self.weights = self.weights.to(device)
        return self

    def get_weights_dict(self) -> dict[str, float]:
        return {name: float(self.weights[i].item()) for i, name in enumerate(self.loss_names)}

    def compute(self, loss_components: dict[str, torch.Tensor], total_loss: torch.Tensor):
        """根据 GradNorm 更新权重。"""
        if not self.weights.requires_grad:
            return

        # 计算每个损失项的梯度范数
        grad_norms = []
        for name in self.loss_names:
            if name in loss_components:
                loss = loss_components[name]
                if isinstance(loss, torch.Tensor) and loss.requires_grad:
                    grad = torch.autograd.grad(loss, self.weights, retain_graph=True)[0]
                    grad_norms.append(torch.norm(grad))
                else:
                    grad_norms.append(torch.tensor(0.0, device=self.device))
            else:
                grad_norms.append(torch.tensor(0.0, device=self.device))

        grad_norms = torch.stack(grad_norms)
        avg_grad_norm = grad_norms.mean()

        # 更新权重
        for i in range(len(self.loss_names)):
            if grad_norms[i] > 0:
                self.weights.data[i] *= (avg_grad_norm / grad_norms[i]) ** self.alpha


# ──────────────────── 损失函数 ────────────────────


def pinn_loss_single(
    model: NavierStokesPINN,
    xy: torch.Tensor,
    target: torch.Tensor,
    domain: torch.Tensor,
    boundary_mask: dict[str, torch.Tensor],
    weights: dict[str, float],
) -> tuple[torch.Tensor, dict[str, float], dict[str, torch.Tensor]]:
    """单工况 PDE-PINN 综合损失。

    L = Σ λ_i · L_i

    损失项：
    - L_data: 数据监督 MSE（u, v, p, T）
    - L_continuity: 连续性方程残差
    - L_momentum: x/y 动量方程残差
    - L_energy: 能量方程残差（流体 + 固体）
    - L_bc_inlet: 入口边界条件
    - L_bc_wall: 壁面无滑移
    - L_bc_outlet: 出口边界条件（压力为0）
    """
    out = model(xy)
    u_pred, v_pred, p_pred, T_pred = out[:, 0], out[:, 1], out[:, 2], out[:, 3]
    u_true, v_true, p_true, T_true = target[:, 0], target[:, 1], target[:, 2], target[:, 3]

    air = domain == 0

    # 数据监督（仅在有定义的区域）
    # 使用加权损失：u场权重更高，因为u场变化范围大、拟合难度高
    L_data_u = F.mse_loss(u_pred[air], u_true[air])
    L_data_v = F.mse_loss(v_pred[air], v_true[air])
    L_data_p = F.mse_loss(p_pred[air], p_true[air])
    L_data_T = F.mse_loss(T_pred, T_true)  # T 全域
    
    # 数据损失权重配置：增加u场权重以改善u方向速度拟合
    w_data_u = weights.get("data_u", 50.0)  # u场权重更高（u变化范围0-8.6）
    w_data_v = weights.get("data_v", 1.0)
    w_data_p = weights.get("data_p", 1.0)
    w_data_T = weights.get("data_T", 1.0)
    
    L_data = w_data_u * L_data_u + w_data_v * L_data_v + w_data_p * L_data_p + w_data_T * L_data_T

    # PDE 残差
    residuals = compute_pde_residuals(model, xy, domain)
    L_cont = (residuals["continuity"] ** 2).mean()
    L_mom_x = (residuals["momentum_x"] ** 2).mean()
    L_mom_y = (residuals["momentum_y"] ** 2).mean()
    L_energy_air = (residuals["energy_air"] ** 2).mean()
    L_energy_solid = (residuals["energy_solid"] ** 2).mean()

    # 边界条件
    inlet = boundary_mask.get("inlet")
    wall = boundary_mask.get("wall")
    outlet = boundary_mask.get("outlet")

    L_bc_inlet = torch.tensor(0.0, device=xy.device)
    L_bc_wall = torch.tensor(0.0, device=xy.device)
    L_bc_outlet = torch.tensor(0.0, device=xy.device)

    # 入口 BC：u=U_IN, v=0, T=T_AMB
    if inlet is not None and inlet.any():
        L_bc_inlet = (
            F.mse_loss(u_pred[inlet], torch.full_like(u_pred[inlet], U_IN))
            + F.mse_loss(v_pred[inlet], torch.zeros_like(v_pred[inlet]))
            + F.mse_loss(T_pred[inlet], torch.full_like(T_pred[inlet], T_AMB))
        )

    # 壁面 BC：无滑移 u=0, v=0（仅在空气域与固体域交界）
    if wall is not None and wall.any():
        L_bc_wall = (
            F.mse_loss(u_pred[wall], torch.zeros_like(u_pred[wall]))
            + F.mse_loss(v_pred[wall], torch.zeros_like(v_pred[wall]))
        )

    # 出口 BC：压力为 0（环境压力）
    if outlet is not None and outlet.any():
        L_bc_outlet = F.mse_loss(p_pred[outlet], torch.zeros_like(p_pred[outlet]))

    L_bc = L_bc_inlet + L_bc_wall + L_bc_outlet

    # 加权求和
    total = (
        weights["data"] * L_data
        + weights["continuity"] * L_cont
        + weights["momentum"] * (L_mom_x + L_mom_y)
        + weights["energy_air"] * L_energy_air
        + weights["energy_solid"] * L_energy_solid
        + weights["bc_inlet"] * L_bc_inlet
        + weights["bc_wall"] * L_bc_wall
        + weights["bc_outlet"] * L_bc_outlet
    )

    components = {
        "total": float(total.item()),
        "data": float(L_data.item()),
        "continuity": float(L_cont.item()),
        "momentum_x": float(L_mom_x.item()),
        "momentum_y": float(L_mom_y.item()),
        "energy_air": float(L_energy_air.item()),
        "energy_solid": float(L_energy_solid.item()),
        "bc_inlet": float(L_bc_inlet.item()),
        "bc_wall": float(L_bc_wall.item()),
        "bc_outlet": float(L_bc_outlet.item()),
    }

    return total, components, residuals


# ──────────────────── 数据加载 ────────────────────


def load_single_case(case_id: int, device: torch.device) -> tuple:
    """加载单个 case 的全场数据。"""
    npz_path = FIELD_DATA_DIR / f"case_{case_id}_full.npz"
    if not npz_path.exists():
        raise FileNotFoundError(f"场数据不存在: {npz_path}")

    data = np.load(npz_path)
    x = data["x"].astype(np.float32)
    y = data["y"].astype(np.float32)
    u = data["u"].astype(np.float32)
    v = data["v"].astype(np.float32)
    p = data["p"].astype(np.float32)
    T = data["T"].astype(np.float32)
    domain = data["domain"].astype(np.int64)

    # 坐标归一化到 [-1, 1]
    x_min, x_max = x.min(), x.max()
    y_min, y_max = y.min(), y.max()
    x_norm = 2 * (x - x_min) / (x_max - x_min + 1e-8) - 1
    y_norm = 2 * (y - y_min) / (y_max - y_min + 1e-8) - 1

    xy = np.column_stack([x_norm, y_norm])
    target = np.column_stack([u, v, p, T])

    xy_t = torch.from_numpy(xy).to(device)
    target_t = torch.from_numpy(target).to(device)
    domain_t = torch.from_numpy(domain).to(device)

    # 使用改进的边界检测函数
    boundary_masks = compute_boundary_masks(x, y, domain, GRID_NX, GRID_NY)
    boundary_mask = {
        "inlet": torch.from_numpy(boundary_masks["inlet"]).to(device),
        "wall": torch.from_numpy(boundary_masks["wall"]).to(device),
        "outlet": torch.from_numpy(boundary_masks["outlet"]).to(device),
        "top": torch.from_numpy(boundary_masks["top"]).to(device),
        "bottom": torch.from_numpy(boundary_masks["bottom"]).to(device),
    }

    # 统计边界点数
    print(f"[DEBUG] 边界统计: inlet={boundary_mask['inlet'].sum().item()}, "
          f"wall={boundary_mask['wall'].sum().item()}, "
          f"outlet={boundary_mask['outlet'].sum().item()}")

    # 归一化信息（用于反归一化可视化）
    norm_info = {"x_min": x_min, "x_max": x_max, "y_min": y_min, "y_max": y_max}

    return xy_t, target_t, domain_t, boundary_mask, norm_info, x, y


# ──────────────────── 可视化残差分布 ────────────────────


def plot_residual_distribution(
    x_phys: np.ndarray, y_phys: np.ndarray,
    residuals: dict[str, torch.Tensor], domain: np.ndarray,
    out_dir: Path
) -> None:
    """绘制 PDE 残差空间分布图。"""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        # 将残差转换为 numpy（需要 detach）
        res_cont = residuals["continuity"].detach().cpu().numpy()
        res_mom_x = residuals["momentum_x"].detach().cpu().numpy()
        res_mom_y = residuals["momentum_y"].detach().cpu().numpy()
        res_energy_air = residuals["energy_air"].detach().cpu().numpy()
        res_energy_solid = residuals["energy_solid"].detach().cpu().numpy()

        # 创建掩码
        air = domain == 0
        solid = domain == 1

        # 为每个残差创建完整数组（空气域/固体域外为 NaN）
        n_points = len(domain)
        cont_full = np.full(n_points, np.nan)
        mom_x_full = np.full(n_points, np.nan)
        mom_y_full = np.full(n_points, np.nan)
        energy_air_full = np.full(n_points, np.nan)
        energy_solid_full = np.full(n_points, np.nan)

        cont_full[air] = res_cont
        mom_x_full[air] = res_mom_x
        mom_y_full[air] = res_mom_y
        energy_air_full[air] = res_energy_air
        energy_solid_full[solid] = res_energy_solid

        # 绘图
        fig, axes = plt.subplots(2, 3, figsize=(18, 10))
        residual_names = ["连续性", "x-动量", "y-动量", "流体能量", "固体能量"]
        residual_arrays = [cont_full, mom_x_full, mom_y_full, energy_air_full, energy_solid_full]

        for i, (name, arr) in enumerate(zip(residual_names, residual_arrays)):
            ax = axes[i // 3, i % 3]
            sc = ax.scatter(x_phys, y_phys, c=arr, s=2, cmap="coolwarm", vmin=-1, vmax=1)
            ax.set_title(f"{name}残差")
            plt.colorbar(sc, ax=ax)

        # 域分布图
        ax = axes[1, 2]
        sc = ax.scatter(x_phys, y_phys, c=domain, s=2, cmap="Set1")
        ax.set_title("域分布 (0=空气, 1=固体)")
        plt.colorbar(sc, ax=ax)

        fig.suptitle("PDE 残差空间分布", fontsize=14)
        fig.tight_layout()
        fig.savefig(out_dir / "residual_distribution.png", dpi=150)
        plt.close(fig)

    except ImportError:
        print("[WARN] matplotlib 不可用，跳过残差分布图")


# ──────────────────── 训练 ────────────────────


def main():
    parser = argparse.ArgumentParser(description="单工况 PDE-PINN 训练")
    parser.add_argument("--case-id", type=int, default=20001)
    parser.add_argument("--epochs", type=int, default=500)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--gradnorm", action="store_true", help="启用 GradNorm 自适应权重")
    args = parser.parse_args()

    torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[INFO] 设备: {device}")
    print(f"[INFO] 工况: case_{args.case_id}")
    print(f"[INFO] GradNorm: {'启用' if args.gradnorm else '禁用'}")

    out_dir = RESULTS_DIR / f"single_case_{args.case_id}"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 加载数据
    xy, target, domain, boundary_mask, norm_info, x_phys, y_phys = load_single_case(
        args.case_id, device,
    )
    n_points = xy.shape[0]
    n_air = (domain == 0).sum().item()
    n_solid = (domain == 1).sum().item()
    print(f"[INFO] 网格点: {n_points} (空气={n_air}, 固体={n_solid})")

    # 模型
    model = NavierStokesPINN().to(device)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"[INFO] 模型参数量: {n_params:,}")

    # 损失权重配置：先数据拟合，再逐步增加PDE约束
    # 策略：初始时优先拟合数据，训练过程中逐步增加PDE权重
    weights = {
        "data": 1.0,
        "continuity": 1.0,       # 连续性方程权重（初始较小）
        "momentum": 1.0,         # 动量方程权重
        "energy_air": 1.0,       # 空气域能量方程权重
        "energy_solid": 1.0,     # 固体域能量方程权重
        "bc_inlet": 1.0,         # 边界条件权重
        "bc_wall": 1.0,          # 壁面边界权重
        "bc_outlet": 1.0,        # 出口边界权重
    }

    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)

    # GradNorm 自适应权重
    gradnorm_weights = None
    if args.gradnorm:
        gradnorm_weights = GradNormLossWeights(
            losses=["data", "continuity", "momentum", "energy_air", "energy_solid", "bc_inlet", "bc_wall", "bc_outlet"],
            alpha=0.1
        ).to(device)

    history = []
    best_loss = float("inf")
    best_residuals = None
    t0 = time.time()

    # 两阶段训练策略：
    # 阶段1（前200轮）：只拟合数据和边界条件，不施加PDE约束
    # 阶段2（200-600轮）：逐步增加PDE约束权重
    # 阶段3（600轮后）：保持最大PDE权重训练
    pde_weight_factor = 0.0  # 初始PDE权重为0
    phase1_end = 200         # 纯数据拟合阶段结束
    phase2_end = 600         # PDE权重增加阶段结束
    pde_max_factor = 1e8     # PDE权重最大增加倍数

    for epoch in range(1, args.epochs + 1):
        model.train()
        loss, components, residuals = pinn_loss_single(
            model, xy, target, domain, boundary_mask, weights,
        )
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        scheduler.step()

        # 两阶段训练策略
        if epoch <= phase1_end:
            # 阶段1：纯数据拟合，PDE权重为0
            pde_weight_factor = 0.0
            weights["continuity"] = 0.0
            weights["momentum"] = 0.0
            weights["energy_air"] = 0.0
            weights["energy_solid"] = 0.0
        elif epoch > phase1_end and epoch <= phase2_end:
            # 阶段2：线性增加PDE权重
            pde_weight_factor = (pde_max_factor) * (epoch - phase1_end) / (phase2_end - phase1_end)
            weights["continuity"] = pde_weight_factor
            weights["momentum"] = pde_weight_factor
            weights["energy_air"] = pde_weight_factor
            weights["energy_solid"] = pde_weight_factor
        else:
            # 阶段3：保持最大PDE权重
            pde_weight_factor = pde_max_factor
            weights["continuity"] = pde_max_factor
            weights["momentum"] = pde_max_factor
            weights["energy_air"] = pde_max_factor
            weights["energy_solid"] = pde_max_factor

        # GradNorm 更新（每10轮更新一次）
        if gradnorm_weights is not None and epoch % 10 == 0:
            gradnorm_weights.compute(components, loss)
            weights.update(gradnorm_weights.get_weights_dict())

        history.append({"epoch": epoch, **components, "lr": scheduler.get_last_lr()[0], **weights, "pde_factor": pde_weight_factor})

        if components["total"] < best_loss:
            best_loss = components["total"]
            best_residuals = residuals
            torch.save(model.state_dict(), out_dir / "best_model.pth")

        if epoch % 50 == 0 or epoch == 1:
            elapsed = (time.time() - t0) / 60
            print(
                f"[{epoch:4d}/{args.epochs}] "
                f"total={components['total']:.4e} "
                f"data={components['data']:.4e} "
                f"cont={components['continuity']:.4e} "
                f"mom={components['momentum_x']:.2e}+{components['momentum_y']:.2e} "
                f"e_air={components['energy_air']:.2e} "
                f"e_sol={components['energy_solid']:.2e} "
                f"bc={components['bc_inlet']:.4e}+{components['bc_wall']:.4e}+{components['bc_outlet']:.4e} "
                f"| {elapsed:.1f}min"
            )
            if gradnorm_weights is not None:
                print(f"        权重: {gradnorm_weights.get_weights_dict()}")

    elapsed_total = (time.time() - t0) / 60
    print(f"\n训练完成: {elapsed_total:.1f} min, best loss = {best_loss:.4e}")

    # 保存训练历史
    with open(out_dir / "train_history.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=history[0].keys())
        writer.writeheader()
        writer.writerows(history)

    # 保存配置
    write_json(out_dir / "config.json", {
        "case_id": args.case_id,
        "epochs": args.epochs,
        "lr": args.lr,
        "gradnorm_enabled": args.gradnorm,
        "weights": weights,
        "n_params": n_params,
        "n_points": n_points,
        "best_loss": best_loss,
        "norm_info": norm_info,
        "声明": "本结果是探索性验证，不替代 PI-CNN-CBAM 主流程",
    })

    # ── 评估 ──
    print("\n" + "=" * 60)
    print("评估")
    print("=" * 60)

    model.load_state_dict(torch.load(out_dir / "best_model.pth", map_location=device))
    model.eval()

    with torch.no_grad():
        pred = model(xy).cpu().numpy()

    target_np = target.cpu().numpy()
    domain_np = domain.cpu().numpy()
    air = domain_np == 0

    from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error

    metrics = {}
    for idx, name in enumerate(["u", "v", "p", "T"]):
        pred_var = pred[:, idx]
        true_var = target_np[:, idx]
        mask = air if name != "T" else np.ones(len(true_var), dtype=bool)
        if mask.sum() > 0:
            mse = mean_squared_error(true_var[mask], pred_var[mask])
            metrics[f"{name}_R2"] = float(r2_score(true_var[mask], pred_var[mask]))
            metrics[f"{name}_MAE"] = float(mean_absolute_error(true_var[mask], pred_var[mask]))
            metrics[f"{name}_RMSE"] = float(math.sqrt(mse))

    print("\n场变量指标（测试 = 训练，单工况）:")
    for k, v in metrics.items():
        print(f"  {k}: {v:.6f}")

    write_json(out_dir / "metrics.json", metrics)

    # ── 可视化 ──
    print("\n生成场变量对比图...")
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(4, 2, figsize=(16, 16))
        labels = ["u [m/s]", "v [m/s]", "p [Pa]", "T [K]"]

        for i, (label, idx) in enumerate(zip(labels, range(4))):
            # COMSOL 真值
            sc0 = axes[i, 0].scatter(x_phys, y_phys, c=target_np[:, idx], s=1, cmap="viridis")
            axes[i, 0].set_title(f"COMSOL {label}")
            plt.colorbar(sc0, ax=axes[i, 0])

            # PINN 预测
            sc1 = axes[i, 1].scatter(x_phys, y_phys, c=pred[:, idx], s=1, cmap="viridis")
            axes[i, 1].set_title(f"PINN {label}")
            plt.colorbar(sc1, ax=axes[i, 1])

        fig.suptitle(f"case_{args.case_id}: COMSOL vs PDE-PINN", fontsize=14)
        fig.tight_layout()
        fig.savefig(out_dir / "field_comparison.png", dpi=150)
        plt.close(fig)

        # 损失曲线
        fig2, ax2 = plt.subplots(figsize=(8, 5))
        epochs = [h["epoch"] for h in history]
        ax2.semilogy(epochs, [h["data"] for h in history], label="data")
        ax2.semilogy(epochs, [h["continuity"] for h in history], label="continuity")
        ax2.semilogy(epochs, [h["energy_air"] for h in history], label="energy_air")
        ax2.semilogy(epochs, [h["bc_inlet"] for h in history], label="bc_inlet")
        ax2.set_xlabel("Epoch")
        ax2.set_ylabel("Loss")
        ax2.legend()
        fig2.tight_layout()
        fig2.savefig(out_dir / "loss_curve.png", dpi=150)
        plt.close(fig2)

        # 残差分布图
        print("生成残差分布图...")
        plot_residual_distribution(x_phys, y_phys, best_residuals, domain_np, out_dir)

        print(f"可视化已保存到 {out_dir}")
    except ImportError as e:
        print(f"[WARN] matplotlib 不可用，跳过可视化: {e}")

    print(f"\n所有结果已保存到 {out_dir}")


if __name__ == "__main__":
    main()