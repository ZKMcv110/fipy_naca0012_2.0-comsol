#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""训练 MLP-CNN 流热场重建代理模型。

输入七参数，输出 u/v/p/T 四通道流热场和 Nu/f 性能指标。
eta 不作为独立网络输出，而是由 Nu、f 按综合性能公式计算，并进入训练损失。
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


class FieldDataset(Dataset):
    def __init__(self, arrays: dict[str, np.ndarray], indices: np.ndarray, stats: dict[str, np.ndarray]):
        self.arrays = arrays
        self.indices = indices
        self.stats = stats

    def __len__(self) -> int:
        return int(self.indices.size)

    def __getitem__(self, item: int) -> dict[str, torch.Tensor]:
        idx = int(self.indices[item])
        params = (self.arrays["params"][idx] - self.stats["param_mean"]) / self.stats["param_std"]
        fields = (self.arrays["fields"][idx] - self.stats["field_mean"]) / self.stats["field_std"]
        targets = (self.arrays["targets"][idx] - self.stats["target_mean"]) / self.stats["target_std"]
        eta = (self.arrays["eta"][idx] - self.stats["eta_mean"]) / self.stats["eta_std"]
        return {
            "params": torch.tensor(params, dtype=torch.float32),
            "fields": torch.tensor(fields, dtype=torch.float32),
            "targets": torch.tensor(targets, dtype=torch.float32),
            "eta": torch.tensor(eta, dtype=torch.float32),
            "case_id": torch.tensor(self.arrays["case_id"][idx], dtype=torch.long),
        }


class ParamToFieldNet(nn.Module):
    def __init__(self, output_hw: tuple[int, int], latent_dim: int = 256):
        super().__init__()
        self.output_hw = output_hw
        self.encoder = nn.Sequential(
            nn.Linear(7, 128),
            nn.ReLU(),
            nn.Linear(128, latent_dim),
            nn.ReLU(),
        )
        self.seed_h, self.seed_w = 5, 8
        self.to_seed = nn.Linear(latent_dim, 128 * self.seed_h * self.seed_w)
        self.decoder = nn.Sequential(
            nn.Upsample(scale_factor=2, mode="bilinear", align_corners=False),
            nn.Conv2d(128, 96, 3, padding=1),
            nn.ReLU(),
            nn.Upsample(scale_factor=2, mode="bilinear", align_corners=False),
            nn.Conv2d(96, 64, 3, padding=1),
            nn.ReLU(),
            nn.Upsample(scale_factor=2, mode="bilinear", align_corners=False),
            nn.Conv2d(64, 32, 3, padding=1),
            nn.ReLU(),
            nn.Conv2d(32, 4, 3, padding=1),
        )
        self.head = nn.Sequential(
            nn.Linear(latent_dim, 128),
            nn.ReLU(),
            nn.Linear(128, 2),
        )

    def forward(self, params: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        latent = self.encoder(params)
        seed = self.to_seed(latent).view(-1, 128, self.seed_h, self.seed_w)
        field = self.decoder(seed)
        field = F.interpolate(field, size=self.output_hw, mode="bilinear", align_corners=False)
        return field, self.head(latent)


def split_indices(count: int, seed: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    idx = rng.permutation(count)
    n_train = int(count * 0.7)
    n_val = int(count * 0.15)
    return idx[:n_train], idx[n_train:n_train + n_val], idx[n_train + n_val:]


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


def compute_loss(
    pred_field: torch.Tensor,
    true_field: torch.Tensor,
    pred_target: torch.Tensor,
    true_target: torch.Tensor,
    true_eta: torch.Tensor,
    stats: dict[str, np.ndarray],
    nu0: float,
    f0: float,
    alpha: float,
    beta: float,
    gamma: float,
) -> tuple[torch.Tensor, dict[str, float]]:
    field_losses = [F.mse_loss(pred_field[:, i], true_field[:, i]) for i in range(pred_field.shape[1])]
    nu_loss = F.mse_loss(pred_target[:, 0], true_target[:, 0])
    f_loss = F.mse_loss(pred_target[:, 1], true_target[:, 1])
    pred_eta = normalized_eta_from_target(pred_target, stats, nu0, f0)
    eta_loss = F.mse_loss(pred_eta, true_eta)
    loss = sum(field_losses) + alpha * nu_loss + beta * f_loss + gamma * eta_loss
    parts = {
        "L_u": float(field_losses[0].detach().cpu()),
        "L_v": float(field_losses[1].detach().cpu()),
        "L_p": float(field_losses[2].detach().cpu()),
        "L_T": float(field_losses[3].detach().cpu()),
        "L_Nu": float(nu_loss.detach().cpu()),
        "L_f": float(f_loss.detach().cpu()),
        "L_eta": float(eta_loss.detach().cpu()),
    }
    return loss, parts


def run_epoch(model, loader, optimizer, device, stats, nu0, f0, alpha, beta, gamma) -> tuple[float, dict[str, float]]:
    model.train(optimizer is not None)
    total, count = 0.0, 0
    part_sums: dict[str, float] = {}
    for batch in loader:
        params = batch["params"].to(device)
        fields = batch["fields"].to(device)
        targets = batch["targets"].to(device)
        eta = batch["eta"].to(device)
        pred_field, pred_target = model(params)
        loss, parts = compute_loss(pred_field, fields, pred_target, targets, eta, stats, nu0, f0, alpha, beta, gamma)
        if optimizer is not None:
            optimizer.zero_grad()
            loss.backward()
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
            pred_field, pred_target = model(batch["params"].to(device))
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
    parser = argparse.ArgumentParser(description="训练 MLP-CNN 流热场重建代理模型")
    parser.add_argument("--dataset", default=str(ROOT / "data" / "field_reconstruction_dataset.npz"))
    parser.add_argument("--output-dir", default=str(ROOT / "results" / "mlp_cnn_field"))
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--alpha", type=float, default=1.0, help="Nu 损失权重")
    parser.add_argument("--beta", type=float, default=1.0, help="f 损失权重")
    parser.add_argument("--gamma", type=float, default=0.2, help="eta 损失权重")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    data = np.load(args.dataset, allow_pickle=True)
    arrays = {name: data[name] for name in ["case_id", "params", "fields", "targets", "eta"]}
    field_names = [str(x) for x in data["field_names"]]
    nu0, f0 = float(data["nu0"]), float(data["f0"])
    train_idx, val_idx, test_idx = split_indices(arrays["params"].shape[0], args.seed)
    stats = make_stats(arrays, train_idx)

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
        output_hw=np.asarray(arrays["fields"].shape[-2:], dtype=np.int64),
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = ParamToFieldNet(tuple(arrays["fields"].shape[-2:])).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)

    loaders = {
        "train": DataLoader(FieldDataset(arrays, train_idx, stats), batch_size=args.batch_size, shuffle=True),
        "val": DataLoader(FieldDataset(arrays, val_idx, stats), batch_size=args.batch_size),
        "test": DataLoader(FieldDataset(arrays, test_idx, stats), batch_size=args.batch_size),
    }

    history = []
    best_val = float("inf")
    for epoch in range(1, args.epochs + 1):
        train_loss, train_parts = run_epoch(
            model, loaders["train"], optimizer, device, stats, nu0, f0, args.alpha, args.beta, args.gamma
        )
        val_loss, val_parts = run_epoch(
            model, loaders["val"], None, device, stats, nu0, f0, args.alpha, args.beta, args.gamma
        )
        row = {"epoch": epoch, "train_loss": train_loss, "val_loss": val_loss}
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
        "loss_formula": "L_u + L_v + L_p + L_T + alpha*L_Nu + beta*L_f + gamma*L_eta",
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
        "output_hw": list(arrays["fields"].shape[-2:]),
        "field_names": field_names,
        "target_names": ["Nu", "f"],
        "model": "ParamToFieldNet",
        "loss_formula": metrics["loss_formula"],
        "alpha": args.alpha,
        "beta": args.beta,
        "gamma": args.gamma,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "seed": args.seed,
    }
    (out_dir / "config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    history_keys = list(history[0].keys()) if history else ["epoch", "train_loss", "val_loss"]
    history_array = np.array([[row.get(key, np.nan) for key in history_keys] for row in history], dtype=float)
    np.savetxt(
        out_dir / "train_history.csv",
        history_array,
        delimiter=",",
        header=",".join(history_keys),
        comments="",
    )

    for i in range(min(3, len(case_ids))):
        save_field_comparison(out_dir, int(case_ids[i]), true_f[i], pred_f[i], field_names)
    save_prediction_scatter(out_dir, true_t, pred_t, eta_true, eta_pred)
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
