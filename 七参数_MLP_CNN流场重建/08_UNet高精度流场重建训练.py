#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""训练条件 U-Net 高精度流热场重建模型。

输入仍以七参数为主，同时显式加入由 COMSOL 采样数据导出的 air/solid
domain mask 和规则坐标通道，缓解仅靠七参数解码时边界被过度平滑的问题。
该脚本不覆盖旧 MLP-CNN 结果，默认输出到新的 results 子目录。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.metrics import mean_absolute_error, r2_score
from torch.utils.data import DataLoader, Dataset


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
DEFAULT_FIELD_NAMES = ["u", "v", "p", "T"]


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


def load_domain_mask(field_dir: Path, case_id: int, output_hw: tuple[int, int]) -> np.ndarray:
    path = field_dir / f"case_{case_id}_full.npz"
    with np.load(path) as data:
        height, width = infer_grid(data)
        domain = data["domain"].astype(np.float32).reshape(height, width)
    if (height, width) != output_hw:
        tensor = torch.tensor(domain[None, None], dtype=torch.float32)
        domain = F.interpolate(tensor, size=output_hw, mode="nearest").numpy()[0, 0]
    solid = (domain > 0.5).astype(np.float32)
    air = 1.0 - solid
    return np.stack([air, solid], axis=0)


def make_coord_channels(output_hw: tuple[int, int]) -> np.ndarray:
    height, width = output_hw
    y = np.linspace(-1.0, 1.0, height, dtype=np.float32)
    x = np.linspace(-1.0, 1.0, width, dtype=np.float32)
    yy, xx = np.meshgrid(y, x, indexing="ij")
    return np.stack([xx, yy], axis=0)


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


class FieldMaskDataset(Dataset):
    def __init__(
        self,
        arrays: dict[str, np.ndarray],
        indices: np.ndarray,
        stats: dict[str, np.ndarray],
        masks: dict[int, np.ndarray],
        coords: np.ndarray,
    ):
        self.arrays = arrays
        self.indices = indices
        self.stats = stats
        self.masks = masks
        self.coords = coords.astype(np.float32)

    def __len__(self) -> int:
        return int(self.indices.size)

    def __getitem__(self, item: int) -> dict[str, torch.Tensor]:
        idx = int(self.indices[item])
        case_id = int(self.arrays["case_id"][idx])
        params = (self.arrays["params"][idx] - self.stats["param_mean"]) / self.stats["param_std"]
        fields = (self.arrays["fields"][idx] - self.stats["field_mean"]) / self.stats["field_std"]
        targets = (self.arrays["targets"][idx] - self.stats["target_mean"]) / self.stats["target_std"]
        eta = (self.arrays["eta"][idx] - self.stats["eta_mean"]) / self.stats["eta_std"]
        spatial = np.concatenate([self.masks[case_id], self.coords], axis=0)
        return {
            "params": torch.tensor(params, dtype=torch.float32),
            "spatial": torch.tensor(spatial, dtype=torch.float32),
            "fields": torch.tensor(fields, dtype=torch.float32),
            "targets": torch.tensor(targets, dtype=torch.float32),
            "eta": torch.tensor(eta, dtype=torch.float32),
            "case_id": torch.tensor(case_id, dtype=torch.long),
        }


class ConvBlock(nn.Module):
    def __init__(self, in_channels: int, out_channels: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, 3, padding=1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_channels, out_channels, 3, padding=1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class ConditionalUNet(nn.Module):
    def __init__(
        self,
        output_hw: tuple[int, int],
        output_channels: int = 4,
        spatial_channels: int = 4,
        latent_dim: int = 128,
        latent_channels: int = 16,
        base_channels: int = 32,
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
        self.enc1 = ConvBlock(in_channels, base_channels)
        self.enc2 = ConvBlock(base_channels, base_channels * 2)
        self.enc3 = ConvBlock(base_channels * 2, base_channels * 4)
        self.bridge = ConvBlock(base_channels * 4, base_channels * 8)
        self.up3 = nn.ConvTranspose2d(base_channels * 8, base_channels * 4, 2, stride=2)
        self.dec3 = ConvBlock(base_channels * 8, base_channels * 4)
        self.up2 = nn.ConvTranspose2d(base_channels * 4, base_channels * 2, 2, stride=2)
        self.dec2 = ConvBlock(base_channels * 4, base_channels * 2)
        self.up1 = nn.ConvTranspose2d(base_channels * 2, base_channels, 2, stride=2)
        self.dec1 = ConvBlock(base_channels * 2, base_channels)
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
        # 50x80 不能被 8 整除，先补到 56x80，输出后裁回原尺寸。
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


def normalized_eta_from_target(pred_target: torch.Tensor, stats: dict[str, np.ndarray], nu0: float, f0: float) -> torch.Tensor:
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
    pred_field: torch.Tensor,
    true_field: torch.Tensor,
    pred_target: torch.Tensor,
    true_target: torch.Tensor,
    true_eta: torch.Tensor,
    stats: dict[str, np.ndarray],
    nu0: float,
    f0: float,
    weights: torch.Tensor,
    alpha: float,
    beta: float,
    gamma: float,
    grad_weight: float,
) -> tuple[torch.Tensor, dict[str, float]]:
    field_diff = (pred_field - true_field) ** 2
    field_losses = field_diff.mean(dim=(0, 2, 3))
    weighted_field = torch.sum(field_losses * weights)
    grad = gradient_loss(pred_field, true_field)
    nu_loss = F.mse_loss(pred_target[:, 0], true_target[:, 0])
    f_loss = F.mse_loss(pred_target[:, 1], true_target[:, 1])
    pred_eta = normalized_eta_from_target(pred_target, stats, nu0, f0)
    eta_loss = F.mse_loss(pred_eta, true_eta)
    loss = weighted_field + grad_weight * grad + alpha * nu_loss + beta * f_loss + gamma * eta_loss
    parts = {f"L_field_{idx}": float(value.detach().cpu()) for idx, value in enumerate(field_losses)}
    parts.update({
        "L_grad": float(grad.detach().cpu()),
        "L_Nu": float(nu_loss.detach().cpu()),
        "L_f": float(f_loss.detach().cpu()),
        "L_eta": float(eta_loss.detach().cpu()),
    })
    return loss, parts


def run_epoch(
    model,
    loader,
    optimizer,
    device,
    stats,
    nu0,
    f0,
    weights,
    alpha,
    beta,
    gamma,
    grad_weight,
) -> tuple[float, dict[str, float]]:
    model.train(optimizer is not None)
    total, count = 0.0, 0
    part_sums: dict[str, float] = {}
    for batch in loader:
        params = batch["params"].to(device)
        spatial = batch["spatial"].to(device)
        fields = batch["fields"].to(device)
        targets = batch["targets"].to(device)
        eta = batch["eta"].to(device)
        pred_field, pred_target = model(params, spatial)
        loss, parts = compute_loss(
            pred_field, fields, pred_target, targets, eta,
            stats, nu0, f0, weights, alpha, beta, gamma, grad_weight,
        )
        if optimizer is not None:
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            optimizer.step()
        batch_size = params.size(0)
        total += float(loss.item()) * batch_size
        count += batch_size
        for key, value in parts.items():
            part_sums[key] = part_sums.get(key, 0.0) + value * batch_size
    return total / max(count, 1), {key: value / max(count, 1) for key, value in part_sums.items()}


def collect_predictions(model, loader, stats, device) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    model.eval()
    true_t, pred_t, true_f, pred_f, case_ids = [], [], [], [], []
    with torch.no_grad():
        for batch in loader:
            pred_field, pred_target = model(batch["params"].to(device), batch["spatial"].to(device))
            pred_target_np = pred_target.cpu().numpy() * stats["target_std"] + stats["target_mean"]
            true_target_np = batch["targets"].numpy() * stats["target_std"] + stats["target_mean"]
            pred_field_np = pred_field.cpu().numpy() * stats["field_std"] + stats["field_mean"]
            true_field_np = batch["fields"].numpy() * stats["field_std"] + stats["field_mean"]
            pred_t.append(pred_target_np)
            true_t.append(true_target_np)
            pred_f.append(pred_field_np)
            true_f.append(true_field_np)
            case_ids.append(batch["case_id"].numpy())
    return tuple(map(np.concatenate, [true_t, pred_t, true_f, pred_f, case_ids]))


def save_field_comparison(out_dir: Path, case_id: int, true_field: np.ndarray, pred_field: np.ndarray, names: list[str]) -> None:
    fig, axes = plt.subplots(len(names), 3, figsize=(9, 9))
    for i, name in enumerate(names):
        diff = pred_field[i] - true_field[i]
        for ax, data, title in zip(axes[i], [true_field[i], pred_field[i], diff], ["CFD", "Pred", "Error"]):
            im = ax.imshow(data, origin="lower", aspect="auto", cmap="viridis")
            ax.set_title(f"{name} {title}")
            ax.axis("off")
            fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(out_dir / f"case_{case_id}_field_compare.png", dpi=160)
    plt.close(fig)


def save_physical_field_comparison(
    out_dir: Path,
    field_dir: Path,
    case_id: int,
    true_field: np.ndarray,
    pred_field: np.ndarray,
    names: list[str],
) -> None:
    """按 COMSOL 采样点真实物理比例导出长条流道对比图。"""

    with np.load(field_dir / f"case_{case_id}_full.npz") as data:
        x = data["x"]
        y = data["y"]
        extent = [float(x.min()), float(x.max()), float(y.min()), float(y.max())]
        height, width = infer_grid(data)
        domain = data["domain"].reshape(height, width)
    solid = np.ma.masked_where(domain <= 0, domain)

    fig, axes = plt.subplots(len(names), 3, figsize=(13, 5.8), constrained_layout=True)
    for i, name in enumerate(names):
        diff = pred_field[i] - true_field[i]
        for ax, data, title in zip(axes[i], [true_field[i], pred_field[i], diff], ["COMSOL sample", "Pred", "Error"]):
            im = ax.imshow(data, origin="lower", extent=extent, aspect="equal", cmap="viridis")
            ax.imshow(solid, origin="lower", extent=extent, aspect="equal", cmap="gray_r", alpha=0.45)
            ax.set_title(f"{name} {title}")
            ax.set_xlabel("x / m")
            ax.set_ylabel("y / m")
            fig.colorbar(im, ax=ax, fraction=0.028, pad=0.012)
    fig.savefig(out_dir / f"case_{case_id}_physical_compare.png", dpi=180)
    plt.close(fig)


def save_prediction_scatter(out_dir: Path, true_t: np.ndarray, pred_t: np.ndarray, eta_true: np.ndarray, eta_pred: np.ndarray) -> None:
    labels = [("Nu", true_t[:, 0], pred_t[:, 0]), ("f", true_t[:, 1], pred_t[:, 1]), ("eta", eta_true, eta_pred)]
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.6))
    for ax, (name, y_true, y_pred) in zip(axes, labels):
        ax.scatter(y_true, y_pred, s=18, alpha=0.75)
        low = float(min(np.min(y_true), np.min(y_pred)))
        high = float(max(np.max(y_true), np.max(y_pred)))
        ax.plot([low, high], [low, high], "k--", linewidth=1)
        ax.set_xlabel(f"CFD {name}")
        ax.set_ylabel(f"Pred {name}")
        ax.set_title(name)
        ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.35)
    fig.tight_layout()
    fig.savefig(out_dir / "prediction_scatter.png", dpi=180)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="训练条件 U-Net 高精度流热场重建模型")
    parser.add_argument("--dataset", default=str(ROOT / "data" / "field_reconstruction_dataset_full.npz"))
    parser.add_argument("--field-dir", default=str(PROJECT_ROOT / "七参数_PDE_PINN尝试" / "field_data"))
    parser.add_argument("--output-dir", default=str(ROOT / "results" / "unet_mask_field_e30"))
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=5e-4)
    parser.add_argument("--alpha", type=float, default=1.0, help="Nu 损失权重")
    parser.add_argument("--beta", type=float, default=1.0, help="f 损失权重")
    parser.add_argument("--gamma", type=float, default=0.2, help="eta 损失权重")
    parser.add_argument("--grad-weight", type=float, default=0.2, help="场梯度损失权重")
    parser.add_argument("--field-weights", default="1,3,2,1.5", help="u,v,p,T 场损失权重")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--limit", type=int, default=0, help="调试用：仅使用前 N 个样本")
    args = parser.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    data = np.load(args.dataset, allow_pickle=True)
    arrays = {name: data[name] for name in ["case_id", "params", "fields", "targets", "eta"]}
    if args.limit:
        for key in arrays:
            arrays[key] = arrays[key][: args.limit]
    field_names = [str(x) for x in data["field_names"]]
    nu0, f0 = float(data["nu0"]), float(data["f0"])
    output_hw = tuple(int(x) for x in arrays["fields"].shape[-2:])
    train_idx, val_idx, test_idx = split_indices(arrays["params"].shape[0], args.seed)
    stats = make_stats(arrays, train_idx)
    coords = make_coord_channels(output_hw)

    field_dir = Path(args.field_dir)
    masks = {
        int(case_id): load_domain_mask(field_dir, int(case_id), output_hw)
        for case_id in arrays["case_id"]
    }

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    np.savez(
        out_dir / "normalization_stats.npz",
        param_mean=stats["param_mean"],
        param_std=stats["param_std"],
        field_mean=stats["field_mean"],
        field_std=stats["field_std"],
        target_mean=stats["target_mean"],
        target_std=stats["target_std"],
        eta_mean=stats["eta_mean"],
        eta_std=stats["eta_std"],
        nu0=np.float32(nu0),
        f0=np.float32(f0),
        output_hw=np.asarray(output_hw, dtype=np.int64),
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    field_weight_values = [float(x) for x in args.field_weights.split(",")]
    if len(field_weight_values) != len(field_names):
        raise ValueError(f"--field-weights 数量必须等于场通道数量: {len(field_weight_values)} != {len(field_names)}")
    weights = torch.tensor(field_weight_values, dtype=torch.float32, device=device)
    model = ConditionalUNet(output_hw, output_channels=len(field_names)).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max(args.epochs, 1))

    loaders = {
        "train": DataLoader(FieldMaskDataset(arrays, train_idx, stats, masks, coords), batch_size=args.batch_size, shuffle=True),
        "val": DataLoader(FieldMaskDataset(arrays, val_idx, stats, masks, coords), batch_size=args.batch_size),
        "test": DataLoader(FieldMaskDataset(arrays, test_idx, stats, masks, coords), batch_size=args.batch_size),
    }

    history = []
    best_val = float("inf")
    for epoch in range(1, args.epochs + 1):
        train_loss, train_parts = run_epoch(
            model, loaders["train"], optimizer, device, stats, nu0, f0,
            weights, args.alpha, args.beta, args.gamma, args.grad_weight,
        )
        val_loss, val_parts = run_epoch(
            model, loaders["val"], None, device, stats, nu0, f0,
            weights, args.alpha, args.beta, args.gamma, args.grad_weight,
        )
        scheduler.step()
        row = {"epoch": epoch, "train_loss": train_loss, "val_loss": val_loss, "lr": scheduler.get_last_lr()[0]}
        row.update({f"train_{k}": v for k, v in train_parts.items()})
        row.update({f"val_{k}": v for k, v in val_parts.items()})
        history.append(row)
        if val_loss < best_val:
            best_val = val_loss
            torch.save(model.state_dict(), out_dir / "best_model.pth")
        print(f"epoch={epoch:03d} train={train_loss:.6f} val={val_loss:.6f}")

    model.load_state_dict(torch.load(out_dir / "best_model.pth", map_location=device))
    true_t, pred_t, true_f, pred_f, case_ids = collect_predictions(model, loaders["test"], stats, device)
    eta_true = eta_np(true_t[:, 0], true_t[:, 1], nu0, f0)
    eta_pred = eta_np(pred_t[:, 0], pred_t[:, 1], nu0, f0)
    metrics = {
        "sample_count": int(arrays["params"].shape[0]),
        "train_count": int(train_idx.size),
        "val_count": int(val_idx.size),
        "test_count": int(test_idx.size),
        "device": str(device),
        "model": "ConditionalUNet",
        "condition_inputs": "seven parameters + air/solid domain mask + normalized x/y coordinates",
        "field_weights": args.field_weights,
        "grad_weight": args.grad_weight,
        "loss_formula": f"weighted({','.join(field_names)}) + grad_weight*L_grad + alpha*L_Nu + beta*L_f + gamma*L_eta",
        "alpha": args.alpha,
        "beta": args.beta,
        "gamma": args.gamma,
        "Nu_R2": float(r2_score(true_t[:, 0], pred_t[:, 0])),
        "Nu_MAE": float(mean_absolute_error(true_t[:, 0], pred_t[:, 0])),
        "f_R2": float(r2_score(true_t[:, 1], pred_t[:, 1])),
        "f_MAE": float(mean_absolute_error(true_t[:, 1], pred_t[:, 1])),
        "eta_R2": float(r2_score(eta_true, eta_pred)),
        "eta_MAE": float(mean_absolute_error(eta_true, eta_pred)),
        "field_MAE": float(np.mean(np.abs(true_f - pred_f))),
        "field_RMSE": float(np.sqrt(np.mean((true_f - pred_f) ** 2))),
    }
    for idx, name in enumerate(field_names):
        diff = true_f[:, idx] - pred_f[:, idx]
        metrics[f"{name}_MAE"] = float(np.mean(np.abs(diff)))
        metrics[f"{name}_RMSE"] = float(np.sqrt(np.mean(diff ** 2)))

    config = {
        "dataset": str(Path(args.dataset).resolve()),
        "field_dir": str(field_dir.resolve()),
        "output_hw": list(output_hw),
        "field_names": field_names,
        "target_names": ["Nu", "f"],
        "model": "ConditionalUNet",
        "output_channels": len(field_names),
        "condition_inputs": metrics["condition_inputs"],
        "loss_formula": metrics["loss_formula"],
        "field_weights": args.field_weights,
        "grad_weight": args.grad_weight,
        "alpha": args.alpha,
        "beta": args.beta,
        "gamma": args.gamma,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "lr": args.lr,
        "seed": args.seed,
    }
    (out_dir / "config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    history_keys = list(history[0].keys()) if history else ["epoch", "train_loss", "val_loss"]
    history_array = np.array([[row.get(key, np.nan) for key in history_keys] for row in history], dtype=float)
    np.savetxt(out_dir / "train_history.csv", history_array, delimiter=",", header=",".join(history_keys), comments="")

    for i in range(min(3, len(case_ids))):
        save_field_comparison(out_dir, int(case_ids[i]), true_f[i], pred_f[i], field_names)
        save_physical_field_comparison(out_dir, field_dir, int(case_ids[i]), true_f[i], pred_f[i], field_names)
    save_prediction_scatter(out_dir, true_t, pred_t, eta_true, eta_pred)
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
