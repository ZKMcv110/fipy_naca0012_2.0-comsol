#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""PVT 流热场重建精简版消融实验。

消融组固定为 A0-A5：
A0 只做七参数到 Nu/f 的标量代理；
A1 使用仅由七参数潜在特征驱动的 U-Net；
A2 在 A1 基础上加入 x/y 坐标和固体/流体区域指示；
A3 在 A2 基础上加入 eta 一致性和场梯度一致性损失；
A4 在 A3 基础上加入 CBAM 注意力；A5 在 A3 基础上加入 ECA 注意力。

脚本输出每组 metrics.json，并汇总 ablation_summary.csv/json。
"""

from __future__ import annotations

import argparse
import csv
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.metrics import mean_absolute_error, r2_score
from torch.utils.data import DataLoader, Dataset


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
DEFAULT_DATASET = ROOT / "data" / "field_reconstruction_dataset_320x96_full_pUt.npz"
DEFAULT_FIELD_DIR = PROJECT_ROOT / "七参数_PDE_PINN尝试" / "field_data_320x96"
DEFAULT_OUTPUT_DIR = ROOT / "results" / "pvt_ablation"


@dataclass(frozen=True)
class AblationConfig:
    name: str
    description: str
    model_kind: str
    use_coords: bool
    use_domain: bool
    use_eta_loss: bool
    use_grad_loss: bool
    use_cbam: bool
    predicts_field: bool
    attention: str = "none"


ABLATION_GROUPS = {
    "A0": AblationConfig(
        name="A0",
        description="MLP 标量代理：只预测 Nu/f/eta，不输出 PVT 场",
        model_kind="mlp",
        use_coords=False,
        use_domain=False,
        use_eta_loss=True,
        use_grad_loss=False,
        use_cbam=False,
        predicts_field=False,
    ),
    "A1": AblationConfig(
        name="A1",
        description="基础 U-Net：七参数潜在特征 -> p/U/T + Nu/f",
        model_kind="unet",
        use_coords=False,
        use_domain=False,
        use_eta_loss=False,
        use_grad_loss=False,
        use_cbam=False,
        predicts_field=True,
    ),
    "A2": AblationConfig(
        name="A2",
        description="U-Net + 坐标通道 + 固体/流体区域指示",
        model_kind="unet",
        use_coords=True,
        use_domain=True,
        use_eta_loss=False,
        use_grad_loss=False,
        use_cbam=False,
        predicts_field=True,
    ),
    "A3": AblationConfig(
        name="A3",
        description="U-Net + 条件输入 + eta 一致性 + 梯度一致性",
        model_kind="unet",
        use_coords=True,
        use_domain=True,
        use_eta_loss=True,
        use_grad_loss=True,
        use_cbam=False,
        predicts_field=True,
    ),
    "A4": AblationConfig(
        name="A4",
        description="U-Net + 条件输入 + 物理约束 + CBAM 注意力",
        model_kind="unet",
        use_coords=True,
        use_domain=True,
        use_eta_loss=True,
        use_grad_loss=True,
        use_cbam=True,
        predicts_field=True,
        attention="cbam",
    ),
    "A5": AblationConfig(
        name="A5",
        description="U-Net + 条件输入 + 物理约束 + ECA 注意力",
        model_kind="unet",
        use_coords=True,
        use_domain=True,
        use_eta_loss=True,
        use_grad_loss=True,
        use_cbam=False,
        predicts_field=True,
        attention="eca",
    ),
}


def eta_np(nu: np.ndarray, f_value: np.ndarray, nu0: float, f0: float) -> np.ndarray:
    return (nu / max(nu0, 1e-12)) / np.power(
        np.maximum(f_value, 1e-12) / max(f0, 1e-12),
        1.0 / 3.0,
    )


def eta_torch(nu: torch.Tensor, f_value: torch.Tensor, nu0: float, f0: float) -> torch.Tensor:
    return (nu / max(nu0, 1e-12)) / torch.pow(
        torch.clamp(f_value, min=1e-12) / max(f0, 1e-12),
        1.0 / 3.0,
    )


def split_indices(count: int, seed: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    idx = rng.permutation(count)
    n_train = int(count * 0.7)
    n_val = int(count * 0.15)
    return idx[:n_train], idx[n_train:n_train + n_val], idx[n_train + n_val:]


def infer_grid(data: np.lib.npyio.NpzFile) -> tuple[int, int]:
    xs = np.unique(data["x"])
    ys = np.unique(data["y"])
    if xs.size * ys.size != data["T"].size:
        raise ValueError(f"无法由 x/y 推断规则网格: {xs.size} x {ys.size} != {data['T'].size}")
    return int(ys.size), int(xs.size)


def make_coord_channels(output_hw: tuple[int, int]) -> np.ndarray:
    height, width = output_hw
    y = np.linspace(-1.0, 1.0, height, dtype=np.float32)
    x = np.linspace(-1.0, 1.0, width, dtype=np.float32)
    yy, xx = np.meshgrid(y, x, indexing="ij")
    return np.stack([xx, yy], axis=0)


def load_domain_mask(field_dir: Path, case_id: int, output_hw: tuple[int, int]) -> np.ndarray:
    with np.load(field_dir / f"case_{case_id}_full.npz") as data:
        height, width = infer_grid(data)
        domain = data["domain"].astype(np.float32).reshape(height, width)
    if (height, width) != output_hw:
        tensor = torch.tensor(domain[None, None], dtype=torch.float32)
        domain = F.interpolate(tensor, size=output_hw, mode="nearest").numpy()[0, 0]
    solid = (domain > 0.5).astype(np.float32)
    air = 1.0 - solid
    return np.stack([air, solid], axis=0)


def make_boundary_mask(domain_pair: np.ndarray) -> np.ndarray:
    solid = torch.tensor(domain_pair[1][None, None], dtype=torch.float32)
    dilated = F.max_pool2d(solid, kernel_size=5, stride=1, padding=2)
    eroded = 1.0 - F.max_pool2d(1.0 - solid, kernel_size=5, stride=1, padding=2)
    boundary = ((dilated - eroded) > 0.0).float().numpy()[0, 0]
    return boundary.astype(np.float32)


def make_stats(arrays: dict[str, np.ndarray], train_idx: np.ndarray) -> dict[str, np.ndarray]:
    return {
        "param_mean": arrays["params"][train_idx].mean(axis=0),
        "param_std": arrays["params"][train_idx].std(axis=0) + 1e-6,
        "field_mean": arrays["fields"][train_idx].mean(axis=(0, 2, 3))[:, None, None],
        "field_std": arrays["fields"][train_idx].std(axis=(0, 2, 3))[:, None, None] + 1e-6,
        "target_mean": arrays["targets"][train_idx].mean(axis=0),
        "target_std": arrays["targets"][train_idx].std(axis=0) + 1e-6,
        "eta_mean": arrays["eta"][train_idx].mean(axis=0),
        "eta_std": arrays["eta"][train_idx].std(axis=0) + 1e-6,
    }


def load_arrays(dataset_path: Path, limit: int) -> tuple[dict[str, np.ndarray], list[str], float, float]:
    data = np.load(dataset_path, allow_pickle=True)
    arrays = {
        "case_id": data["case_id"].astype(np.int64),
        "params": data["params"].astype(np.float32),
        "fields": data["fields"].astype(np.float32),
        "targets": data["targets"].astype(np.float32),
        "eta": data["eta"].astype(np.float32),
    }
    if limit > 0:
        for key in arrays:
            arrays[key] = arrays[key][:limit]
    field_names = [str(x) for x in data["field_names"]]
    return arrays, field_names, float(data["nu0"]), float(data["f0"])


class AblationDataset(Dataset):
    def __init__(
        self,
        arrays: dict[str, np.ndarray],
        indices: np.ndarray,
        stats: dict[str, np.ndarray],
        spatial_by_case: dict[int, np.ndarray],
        boundary_by_case: dict[int, np.ndarray],
    ):
        self.arrays = arrays
        self.indices = indices
        self.stats = stats
        self.spatial_by_case = spatial_by_case
        self.boundary_by_case = boundary_by_case

    def __len__(self) -> int:
        return int(self.indices.size)

    def __getitem__(self, item: int) -> dict[str, torch.Tensor]:
        idx = int(self.indices[item])
        case_id = int(self.arrays["case_id"][idx])
        params = (self.arrays["params"][idx] - self.stats["param_mean"]) / self.stats["param_std"]
        fields = (self.arrays["fields"][idx] - self.stats["field_mean"]) / self.stats["field_std"]
        targets = (self.arrays["targets"][idx] - self.stats["target_mean"]) / self.stats["target_std"]
        eta = (self.arrays["eta"][idx] - self.stats["eta_mean"]) / self.stats["eta_std"]
        return {
            "params": torch.tensor(params, dtype=torch.float32),
            "spatial": torch.tensor(self.spatial_by_case[case_id], dtype=torch.float32),
            "fields": torch.tensor(fields, dtype=torch.float32),
            "targets": torch.tensor(targets, dtype=torch.float32),
            "eta": torch.tensor(eta, dtype=torch.float32),
            "boundary": torch.tensor(self.boundary_by_case[case_id], dtype=torch.float32),
            "case_id": torch.tensor(case_id, dtype=torch.long),
        }


def make_attention(name: str, channels: int) -> nn.Module:
    if name == "cbam":
        return CBAM(channels)
    if name == "eca":
        return ECA(channels)
    if name == "none":
        return nn.Identity()
    raise ValueError(f"未知注意力类型: {name}")


class ConvBlock(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, attention: str = "none"):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, 3, padding=1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_channels, out_channels, 3, padding=1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
        )
        self.attn = make_attention(attention, out_channels)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.attn(self.conv(x))


class CBAM(nn.Module):
    def __init__(self, channels: int, reduction: int = 8):
        super().__init__()
        hidden = max(channels // reduction, 4)
        self.mlp = nn.Sequential(
            nn.Conv2d(channels, hidden, 1, bias=False),
            nn.ReLU(inplace=True),
            nn.Conv2d(hidden, channels, 1, bias=False),
        )
        self.spatial = nn.Conv2d(2, 1, kernel_size=7, padding=3, bias=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        avg = F.adaptive_avg_pool2d(x, 1)
        max_value = F.adaptive_max_pool2d(x, 1)
        channel = torch.sigmoid(self.mlp(avg) + self.mlp(max_value))
        x = x * channel
        spatial_input = torch.cat([x.mean(dim=1, keepdim=True), x.amax(dim=1, keepdim=True)], dim=1)
        spatial = torch.sigmoid(self.spatial(spatial_input))
        return x * spatial


class ECA(nn.Module):
    def __init__(self, channels: int, kernel_size: int = 3):
        super().__init__()
        if kernel_size % 2 == 0:
            raise ValueError("ECA kernel_size 必须为奇数")
        self.pool = nn.AdaptiveAvgPool2d(1)
        self.conv = nn.Conv1d(
            in_channels=1,
            out_channels=1,
            kernel_size=kernel_size,
            padding=(kernel_size - 1) // 2,
            bias=False,
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # ECA 只做轻量通道重标定，不引入空间卷积，便于和 CBAM 对比参数开销。
        weights = self.pool(x).squeeze(-1).transpose(-1, -2)
        weights = torch.sigmoid(self.conv(weights)).transpose(-1, -2).unsqueeze(-1)
        return x * weights


class ScalarMLP(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(7, 128),
            nn.ReLU(inplace=True),
            nn.Linear(128, 128),
            nn.ReLU(inplace=True),
            nn.Linear(128, 64),
            nn.ReLU(inplace=True),
            nn.Linear(64, 2),
        )

    def forward(self, params: torch.Tensor, spatial: torch.Tensor | None = None) -> tuple[None, torch.Tensor]:
        return None, self.net(params)


class ConfigurableUNet(nn.Module):
    def __init__(
        self,
        output_hw: tuple[int, int],
        output_channels: int,
        spatial_channels: int,
        attention: str,
        latent_dim: int = 128,
        latent_channels: int = 16,
        base_channels: int = 16,
    ):
        super().__init__()
        self.output_hw = output_hw
        self.param_encoder = nn.Sequential(
            nn.Linear(7, 128),
            nn.ReLU(inplace=True),
            nn.Linear(128, latent_dim),
            nn.ReLU(inplace=True),
        )
        self.latent_to_map = nn.Linear(latent_dim, latent_channels)
        in_channels = spatial_channels + latent_channels
        self.enc1 = ConvBlock(in_channels, base_channels, attention)
        self.enc2 = ConvBlock(base_channels, base_channels * 2, attention)
        self.enc3 = ConvBlock(base_channels * 2, base_channels * 4, attention)
        self.bridge = ConvBlock(base_channels * 4, base_channels * 8, attention)
        self.up3 = nn.ConvTranspose2d(base_channels * 8, base_channels * 4, 2, stride=2)
        self.dec3 = ConvBlock(base_channels * 8, base_channels * 4, attention)
        self.up2 = nn.ConvTranspose2d(base_channels * 4, base_channels * 2, 2, stride=2)
        self.dec2 = ConvBlock(base_channels * 4, base_channels * 2, attention)
        self.up1 = nn.ConvTranspose2d(base_channels * 2, base_channels, 2, stride=2)
        self.dec1 = ConvBlock(base_channels * 2, base_channels, attention)
        self.out_conv = nn.Conv2d(base_channels, output_channels, 1)
        self.head = nn.Sequential(
            nn.Linear(latent_dim, 128),
            nn.ReLU(inplace=True),
            nn.Linear(128, 2),
        )

    def forward(self, params: torch.Tensor, spatial: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        latent = self.param_encoder(params)
        latent_map = self.latent_to_map(latent)[:, :, None, None]
        latent_map = latent_map.expand(-1, -1, spatial.shape[-2], spatial.shape[-1])
        x = torch.cat([spatial, latent_map], dim=1)
        pad_h = (8 - x.shape[-2] % 8) % 8
        if pad_h:
            x = F.pad(x, (0, 0, 0, pad_h), mode="replicate")
        e1 = self.enc1(x)
        e2 = self.enc2(F.max_pool2d(e1, 2))
        e3 = self.enc3(F.max_pool2d(e2, 2))
        bridge = self.bridge(F.max_pool2d(e3, 2))
        d3 = self.up3(bridge)
        d3 = self.dec3(torch.cat([d3, e3], dim=1))
        d2 = self.up2(d3)
        d2 = self.dec2(torch.cat([d2, e2], dim=1))
        d1 = self.up1(d2)
        d1 = self.dec1(torch.cat([d1, e1], dim=1))
        field = self.out_conv(d1)[..., : self.output_hw[0], : self.output_hw[1]]
        return field, self.head(latent)


def denormalize_targets(pred_target: torch.Tensor, stats: dict[str, np.ndarray]) -> tuple[torch.Tensor, torch.Tensor]:
    mean = torch.as_tensor(stats["target_mean"], dtype=pred_target.dtype, device=pred_target.device)
    std = torch.as_tensor(stats["target_std"], dtype=pred_target.dtype, device=pred_target.device)
    raw = pred_target * std + mean
    return raw[:, 0], raw[:, 1]


def normalized_eta_from_target(
    pred_target: torch.Tensor,
    stats: dict[str, np.ndarray],
    nu0: float,
    f0: float,
) -> torch.Tensor:
    nu, f_value = denormalize_targets(pred_target, stats)
    eta = eta_torch(nu, f_value, nu0, f0).unsqueeze(1)
    eta_mean = torch.as_tensor(stats["eta_mean"], dtype=pred_target.dtype, device=pred_target.device)
    eta_std = torch.as_tensor(stats["eta_std"], dtype=pred_target.dtype, device=pred_target.device)
    return (eta - eta_mean) / eta_std


def gradient_loss(pred_field: torch.Tensor, true_field: torch.Tensor) -> torch.Tensor:
    pred_dx = pred_field[..., :, 1:] - pred_field[..., :, :-1]
    true_dx = true_field[..., :, 1:] - true_field[..., :, :-1]
    pred_dy = pred_field[..., 1:, :] - pred_field[..., :-1, :]
    true_dy = true_field[..., 1:, :] - true_field[..., :-1, :]
    return F.l1_loss(pred_dx, true_dx) + F.l1_loss(pred_dy, true_dy)


def compute_loss(
    config: AblationConfig,
    pred_field: torch.Tensor | None,
    true_field: torch.Tensor,
    pred_target: torch.Tensor,
    true_target: torch.Tensor,
    true_eta: torch.Tensor,
    stats: dict[str, np.ndarray],
    nu0: float,
    f0: float,
    field_weights: torch.Tensor,
    alpha: float,
    beta: float,
    gamma: float,
    grad_weight: float,
) -> torch.Tensor:
    target_loss = alpha * F.mse_loss(pred_target[:, 0], true_target[:, 0])
    target_loss = target_loss + beta * F.mse_loss(pred_target[:, 1], true_target[:, 1])
    if config.use_eta_loss:
        pred_eta = normalized_eta_from_target(pred_target, stats, nu0, f0)
        target_loss = target_loss + gamma * F.mse_loss(pred_eta, true_eta)
    if not config.predicts_field:
        return target_loss
    if pred_field is None:
        raise RuntimeError(f"{config.name} 需要预测 PVT 场，但 pred_field 为空")
    field_diff = (pred_field - true_field) ** 2
    field_losses = field_diff.mean(dim=(0, 2, 3))
    loss = torch.sum(field_losses * field_weights) + target_loss
    if config.use_grad_loss:
        loss = loss + grad_weight * gradient_loss(pred_field, true_field)
    return loss


def run_epoch(
    model: nn.Module,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer | None,
    device: torch.device,
    config: AblationConfig,
    stats: dict[str, np.ndarray],
    nu0: float,
    f0: float,
    field_weights: torch.Tensor,
    alpha: float,
    beta: float,
    gamma: float,
    grad_weight: float,
) -> float:
    model.train(optimizer is not None)
    total = 0.0
    count = 0
    for batch in loader:
        params = batch["params"].to(device)
        spatial = batch["spatial"].to(device)
        fields = batch["fields"].to(device)
        targets = batch["targets"].to(device)
        eta = batch["eta"].to(device)
        pred_field, pred_target = model(params, spatial)
        loss = compute_loss(
            config, pred_field, fields, pred_target, targets, eta,
            stats, nu0, f0, field_weights, alpha, beta, gamma, grad_weight,
        )
        if optimizer is not None:
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            optimizer.step()
        batch_size = params.size(0)
        total += float(loss.detach().cpu()) * batch_size
        count += batch_size
    return total / max(count, 1)


def collect_predictions(
    model: nn.Module,
    loader: DataLoader,
    stats: dict[str, np.ndarray],
    device: torch.device,
    predicts_field: bool,
) -> dict[str, np.ndarray]:
    model.eval()
    true_targets, pred_targets, true_fields, pred_fields, boundaries = [], [], [], [], []
    with torch.no_grad():
        for batch in loader:
            pred_field, pred_target = model(batch["params"].to(device), batch["spatial"].to(device))
            pred_target_np = pred_target.cpu().numpy() * stats["target_std"] + stats["target_mean"]
            true_target_np = batch["targets"].numpy() * stats["target_std"] + stats["target_mean"]
            true_targets.append(true_target_np)
            pred_targets.append(pred_target_np)
            if predicts_field and pred_field is not None:
                pred_field_np = pred_field.cpu().numpy() * stats["field_std"] + stats["field_mean"]
                true_field_np = batch["fields"].numpy() * stats["field_std"] + stats["field_mean"]
                pred_fields.append(pred_field_np)
                true_fields.append(true_field_np)
                boundaries.append(batch["boundary"].numpy())
    result = {
        "true_targets": np.concatenate(true_targets),
        "pred_targets": np.concatenate(pred_targets),
    }
    if true_fields:
        result["true_fields"] = np.concatenate(true_fields)
        result["pred_fields"] = np.concatenate(pred_fields)
        result["boundaries"] = np.concatenate(boundaries)
    return result


def safe_r2(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    if np.unique(y_true).size < 2:
        return float("nan")
    return float(r2_score(y_true, y_pred))


def evaluate_metrics(
    config: AblationConfig,
    predictions: dict[str, np.ndarray],
    field_names: list[str],
    nu0: float,
    f0: float,
    train_seconds: float,
) -> dict[str, float | str | None]:
    true_t = predictions["true_targets"]
    pred_t = predictions["pred_targets"]
    eta_true = eta_np(true_t[:, 0], true_t[:, 1], nu0, f0)
    eta_pred = eta_np(pred_t[:, 0], pred_t[:, 1], nu0, f0)
    metrics: dict[str, float | str | None] = {
        "group": config.name,
        "description": config.description,
        "Nu_R2": safe_r2(true_t[:, 0], pred_t[:, 0]),
        "f_R2": safe_r2(true_t[:, 1], pred_t[:, 1]),
        "eta_R2": safe_r2(eta_true, eta_pred),
        "Nu_MAE": float(mean_absolute_error(true_t[:, 0], pred_t[:, 0])),
        "f_MAE": float(mean_absolute_error(true_t[:, 1], pred_t[:, 1])),
        "eta_MAE": float(mean_absolute_error(eta_true, eta_pred)),
        "training_time": float(train_seconds),
    }
    for name in field_names:
        metrics[f"{name}_MAE"] = None
        metrics[f"{name}_RMSE"] = None
    metrics["field_MAE"] = None
    metrics["field_RMSE"] = None
    metrics["boundary_MAE"] = None
    if not config.predicts_field:
        return metrics

    true_f = predictions["true_fields"]
    pred_f = predictions["pred_fields"]
    diff = true_f - pred_f
    metrics["field_MAE"] = float(np.mean(np.abs(diff)))
    metrics["field_RMSE"] = float(np.sqrt(np.mean(diff ** 2)))
    for idx, name in enumerate(field_names):
        channel_diff = diff[:, idx]
        metrics[f"{name}_MAE"] = float(np.mean(np.abs(channel_diff)))
        metrics[f"{name}_RMSE"] = float(np.sqrt(np.mean(channel_diff ** 2)))

    boundary = predictions["boundaries"][:, None, :, :]
    weight_sum = float(np.sum(boundary) * true_f.shape[1])
    if weight_sum > 0:
        metrics["boundary_MAE"] = float(np.sum(np.abs(diff) * boundary) / weight_sum)
    return metrics


def build_spatial_maps(
    config: AblationConfig,
    arrays: dict[str, np.ndarray],
    field_dir: Path,
    output_hw: tuple[int, int],
) -> tuple[dict[int, np.ndarray], dict[int, np.ndarray]]:
    coords = make_coord_channels(output_hw)
    zeros = np.zeros((1, output_hw[0], output_hw[1]), dtype=np.float32)
    spatial_by_case: dict[int, np.ndarray] = {}
    boundary_by_case: dict[int, np.ndarray] = {}
    for raw_case_id in arrays["case_id"]:
        case_id = int(raw_case_id)
        domain_pair = load_domain_mask(field_dir, case_id, output_hw)
        channels: list[np.ndarray] = []
        if config.use_domain:
            channels.extend([domain_pair[0], domain_pair[1]])
        if config.use_coords:
            channels.extend([coords[0], coords[1]])
        if not channels:
            channels = [zeros[0]]
        spatial_by_case[case_id] = np.stack(channels, axis=0).astype(np.float32)
        boundary_by_case[case_id] = make_boundary_mask(domain_pair)
    return spatial_by_case, boundary_by_case


def make_model(config: AblationConfig, output_hw: tuple[int, int], field_count: int, spatial_channels: int) -> nn.Module:
    if config.model_kind == "mlp":
        return ScalarMLP()
    return ConfigurableUNet(
        output_hw=output_hw,
        output_channels=field_count,
        spatial_channels=spatial_channels,
        attention=config.attention,
    )


def save_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=True), encoding="utf-8")


def write_summary(output_dir: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with (output_dir / "ablation_summary.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    save_json(output_dir / "ablation_summary.json", rows)


def collect_metric_rows(output_dir: Path, updated_rows: Iterable[dict[str, object]]) -> list[dict[str, object]]:
    rows_by_group: dict[str, dict[str, object]] = {}
    for group in ABLATION_GROUPS:
        metrics_path = output_dir / group / "metrics.json"
        if metrics_path.exists():
            with metrics_path.open("r", encoding="utf-8") as f:
                row = json.load(f)
            rows_by_group[str(row.get("group", group))] = row
    for row in updated_rows:
        rows_by_group[str(row.get("group"))] = row
    return [rows_by_group[group] for group in ABLATION_GROUPS if group in rows_by_group]


def parse_groups(raw: str) -> list[str]:
    groups = [item.strip().upper() for item in raw.split(",") if item.strip()]
    unknown = [group for group in groups if group not in ABLATION_GROUPS]
    if unknown:
        raise ValueError(f"未知消融组: {unknown}; 可选 {sorted(ABLATION_GROUPS)}")
    return groups


def make_loaders(
    arrays: dict[str, np.ndarray],
    train_idx: np.ndarray,
    val_idx: np.ndarray,
    test_idx: np.ndarray,
    stats: dict[str, np.ndarray],
    spatial_by_case: dict[int, np.ndarray],
    boundary_by_case: dict[int, np.ndarray],
    batch_size: int,
) -> dict[str, DataLoader]:
    return {
        "train": DataLoader(
            AblationDataset(arrays, train_idx, stats, spatial_by_case, boundary_by_case),
            batch_size=batch_size,
            shuffle=True,
        ),
        "val": DataLoader(
            AblationDataset(arrays, val_idx, stats, spatial_by_case, boundary_by_case),
            batch_size=batch_size,
        ),
        "test": DataLoader(
            AblationDataset(arrays, test_idx, stats, spatial_by_case, boundary_by_case),
            batch_size=batch_size,
        ),
    }


def train_one_group(
    config: AblationConfig,
    arrays: dict[str, np.ndarray],
    field_names: list[str],
    nu0: float,
    f0: float,
    train_idx: np.ndarray,
    val_idx: np.ndarray,
    test_idx: np.ndarray,
    args: argparse.Namespace,
    device: torch.device,
) -> dict[str, object]:
    output_hw = tuple(int(x) for x in arrays["fields"].shape[-2:])
    stats = make_stats(arrays, train_idx)
    field_dir = Path(args.field_dir)
    spatial_by_case, boundary_by_case = build_spatial_maps(config, arrays, field_dir, output_hw)
    spatial_channels = next(iter(spatial_by_case.values())).shape[0]
    loaders = make_loaders(
        arrays, train_idx, val_idx, test_idx, stats,
        spatial_by_case, boundary_by_case, args.batch_size,
    )

    group_dir = Path(args.output_dir) / config.name
    group_dir.mkdir(parents=True, exist_ok=True)
    model = make_model(config, output_hw, len(field_names), spatial_channels).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max(args.epochs, 1))
    field_weights = torch.tensor(
        [float(x) for x in args.field_weights.split(",")],
        dtype=torch.float32,
        device=device,
    )
    if field_weights.numel() != len(field_names):
        raise ValueError("--field-weights 数量必须等于 PVT 场通道数")

    best_val = float("inf")
    history: list[dict[str, float]] = []
    start = time.perf_counter()
    for epoch in range(1, args.epochs + 1):
        train_loss = run_epoch(
            model, loaders["train"], optimizer, device, config, stats, nu0, f0,
            field_weights, args.alpha, args.beta, args.gamma, args.grad_weight,
        )
        val_loss = run_epoch(
            model, loaders["val"], None, device, config, stats, nu0, f0,
            field_weights, args.alpha, args.beta, args.gamma, args.grad_weight,
        )
        scheduler.step()
        history.append({"epoch": epoch, "train_loss": train_loss, "val_loss": val_loss})
        if val_loss < best_val:
            best_val = val_loss
            torch.save(model.state_dict(), group_dir / "best_model.pth")
        print(f"{config.name} epoch={epoch:03d} train={train_loss:.6f} val={val_loss:.6f}")
    train_seconds = time.perf_counter() - start

    model.load_state_dict(torch.load(group_dir / "best_model.pth", map_location=device))
    predictions = collect_predictions(model, loaders["test"], stats, device, config.predicts_field)
    metrics = evaluate_metrics(config, predictions, field_names, nu0, f0, train_seconds)
    metrics.update({
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "sample_count": int(arrays["params"].shape[0]),
        "train_count": int(train_idx.size),
        "val_count": int(val_idx.size),
        "test_count": int(test_idx.size),
        "device": str(device),
        "use_coords": config.use_coords,
        "use_domain": config.use_domain,
        "use_eta_loss": config.use_eta_loss,
        "use_grad_loss": config.use_grad_loss,
        "use_cbam": config.use_cbam,
        "attention": config.attention,
        "predicts_field": config.predicts_field,
    })
    save_json(group_dir / "metrics.json", metrics)
    save_json(group_dir / "config.json", {
        "group": config.name,
        "description": config.description,
        "dataset": str(Path(args.dataset).resolve()),
        "field_dir": str(field_dir.resolve()),
        "field_names": field_names,
        "output_hw": list(output_hw),
    })
    with (group_dir / "train_history.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["epoch", "train_loss", "val_loss"])
        writer.writeheader()
        writer.writerows(history)
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="运行 p/U/T 精简版消融实验")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET))
    parser.add_argument("--field-dir", default=str(DEFAULT_FIELD_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--groups", default="A0,A1,A2,A3,A4,A5")
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--lr", type=float, default=5e-4)
    parser.add_argument("--alpha", type=float, default=1.0)
    parser.add_argument("--beta", type=float, default=1.0)
    parser.add_argument("--gamma", type=float, default=0.2)
    parser.add_argument("--grad-weight", type=float, default=0.5)
    parser.add_argument("--field-weights", default="4,6,3")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--limit", type=int, default=0, help="调试用：仅使用前 N 个样本")
    args = parser.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    arrays, field_names, nu0, f0 = load_arrays(Path(args.dataset), args.limit)
    if field_names != ["p", "U", "T"]:
        raise ValueError(f"消融实验要求 p/U/T 三通道数据，当前为 {field_names}")
    train_idx, val_idx, test_idx = split_indices(arrays["params"].shape[0], args.seed)
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    rows: list[dict[str, object]] = []
    output_dir = Path(args.output_dir)
    for group in parse_groups(args.groups):
        metrics = train_one_group(
            ABLATION_GROUPS[group], arrays, field_names, nu0, f0,
            train_idx, val_idx, test_idx, args, device,
        )
        rows.append(metrics)
        write_summary(output_dir, collect_metric_rows(output_dir, rows))
    print(json.dumps(collect_metric_rows(output_dir, rows), ensure_ascii=False, indent=2, allow_nan=True))


if __name__ == "__main__":
    main()
