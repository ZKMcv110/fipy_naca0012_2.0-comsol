#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""七参数几何掩码代理模型消融实验。

本脚本不依赖 CFD 云图，输入只包含七参数和由参数生成的几何掩码图。
消融顺序（逐步加组件）：
1. baseline  — 基线：纯参数 MLP
2. mask      — 加几何掩码编码器 + 参数融合
3. cbam      — 加 CBAM 注意力
4. pi        — 加物理约束损失
5. gp        — 加梯度惩罚（完整模型）
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from torch.utils.data import DataLoader, Dataset

from common import PARAM_COLS, ROOT, TARGET_COLS, baseline_from_labels, ensure_dir, normalize, render_fixed_domain_mask, write_json


class MaskParamDataset(Dataset):
    def __init__(self, df: pd.DataFrame, mask_dir: Path, stats: dict, image_size: int):
        self.df = df.reset_index(drop=True)
        self.mask_dir = mask_dir
        self.stats = stats
        self.image_size = image_size

    def __len__(self) -> int:
        return len(self.df)

    def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
        row = self.df.iloc[index]
        case_id = int(row["case_id"])
        mask_path = self.mask_dir / f"case_{case_id}_mask.png"
        if not mask_path.exists():
            params = {name: float(row[name]) for name in PARAM_COLS}
            render_fixed_domain_mask(params, mask_path, image_size=self.image_size)

        mask = Image.open(mask_path).convert("L").resize((self.image_size, self.image_size))
        mask_arr = 1.0 - np.asarray(mask, dtype=np.float32) / 255.0
        params = row[PARAM_COLS].to_numpy(dtype=np.float32)
        target = row[TARGET_COLS].to_numpy(dtype=np.float32)
        params_norm = normalize(params, self.stats["param_mean"], self.stats["param_std"])
        target_norm = normalize(target, self.stats["target_mean"], self.stats["target_std"])
        return {
            "mask": torch.tensor(mask_arr[None, :, :], dtype=torch.float32),
            "params": torch.tensor(params_norm, dtype=torch.float32),
            "target": torch.tensor(target_norm, dtype=torch.float32),
            "target_real": torch.tensor(target, dtype=torch.float32),
            "case_id": torch.tensor(case_id, dtype=torch.long),
        }


class ChannelAttention(nn.Module):
    def __init__(self, channels: int, ratio: int = 8):
        super().__init__()
        hidden = max(channels // ratio, 1)
        self.shared = nn.Sequential(
            nn.Conv2d(channels, hidden, 1, bias=False),
            nn.ReLU(inplace=True),
            nn.Conv2d(hidden, channels, 1, bias=False),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        avg = self.shared(F.adaptive_avg_pool2d(x, 1))
        max_v = self.shared(F.adaptive_max_pool2d(x, 1))
        return torch.sigmoid(avg + max_v)


class SpatialAttention(nn.Module):
    def __init__(self, kernel_size: int = 7):
        super().__init__()
        padding = kernel_size // 2
        self.conv = nn.Conv2d(2, 1, kernel_size, padding=padding, bias=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        avg = torch.mean(x, dim=1, keepdim=True)
        max_v, _ = torch.max(x, dim=1, keepdim=True)
        return torch.sigmoid(self.conv(torch.cat([avg, max_v], dim=1)))


class CBAM(nn.Module):
    def __init__(self, channels: int):
        super().__init__()
        self.ca = ChannelAttention(channels)
        self.sa = SpatialAttention()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x * self.ca(x)
        x = x * self.sa(x)
        return x


class MaskEncoder(nn.Module):
    def __init__(self, use_cbam: bool = False):
        super().__init__()
        layers: list[nn.Module] = [
            nn.Conv2d(1, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(32, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(64, 128, 3, padding=1), nn.BatchNorm2d(128), nn.ReLU(),
        ]
        if use_cbam:
            layers.append(CBAM(128))
        layers.extend([
            nn.MaxPool2d(2),
            nn.Conv2d(128, 256, 3, padding=1), nn.BatchNorm2d(256), nn.ReLU(),
            nn.AdaptiveAvgPool2d((1, 1)),
        ])
        self.net = nn.Sequential(*layers)

    def forward(self, mask: torch.Tensor) -> torch.Tensor:
        return self.net(mask).flatten(1)


class ParamMLP(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(len(PARAM_COLS), 64), nn.ReLU(),
            nn.Linear(64, 128), nn.ReLU(),
            nn.Linear(128, 64), nn.ReLU(),
            nn.Linear(64, 2),
        )

    def forward(self, mask: torch.Tensor, params: torch.Tensor) -> torch.Tensor:
        return self.net(params)


class MaskCNN(nn.Module):
    def __init__(self, use_cbam: bool = False):
        super().__init__()
        self.encoder = MaskEncoder(use_cbam=use_cbam)
        self.head = nn.Sequential(nn.Linear(256, 128), nn.ReLU(), nn.Linear(128, 2))

    def forward(self, mask: torch.Tensor, params: torch.Tensor) -> torch.Tensor:
        return self.head(self.encoder(mask))


class FusionModel(nn.Module):
    def __init__(self, use_cbam: bool = False, use_params: bool = True):
        super().__init__()
        self.use_params = use_params
        self.encoder = MaskEncoder(use_cbam=use_cbam)
        if use_params:
            self.param_mlp = nn.Sequential(
                nn.Linear(len(PARAM_COLS), 64), nn.ReLU(),
                nn.Linear(64, 128), nn.ReLU(),
            )
        head_in = 256 + 128 if use_params else 256
        self.head = nn.Sequential(
            nn.Linear(head_in, 256), nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, 128), nn.ReLU(),
            nn.Linear(128, 2),
        )

    def forward(self, mask: torch.Tensor, params: torch.Tensor) -> torch.Tensor:
        img_feat = self.encoder(mask)
        if self.use_params:
            return self.head(torch.cat([img_feat, self.param_mlp(params)], dim=1))
        return self.head(img_feat)


def load_labels(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = ["case_id"] + PARAM_COLS + TARGET_COLS
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"标签表缺少必要列: {missing}")
    for col in PARAM_COLS + TARGET_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=required)
    df = df[(df["Nu"] > 0) & (df["f"] > 0)].copy()
    df["case_id"] = df["case_id"].astype(int)
    return df.sort_values("case_id").reset_index(drop=True)


def build_split(df: pd.DataFrame, split_file: Path | None, seed: int) -> tuple[list[int], list[int], list[int]]:
    if split_file and split_file.exists():
        split_df = pd.read_csv(split_file)
        id_to_idx = {int(row.case_id): idx for idx, row in df.iterrows()}
        splits = []
        for name in ["train", "val", "test"]:
            ids = split_df.loc[split_df["split"] == name, "case_id"].astype(int).tolist()
            splits.append([id_to_idx[cid] for cid in ids if cid in id_to_idx])
        if all(splits):
            return tuple(splits)  # type: ignore[return-value]

    rng = np.random.default_rng(seed)
    idx = rng.permutation(len(df)).tolist()
    n_train = int(0.75 * len(idx))
    n_val = int(0.15 * len(idx))
    return idx[:n_train], idx[n_train:n_train + n_val], idx[n_train + n_val:]


def compute_stats(df: pd.DataFrame, train_idx: list[int]) -> dict:
    train_df = df.iloc[train_idx]
    return {
        "param_mean": train_df[PARAM_COLS].mean().to_numpy(dtype=np.float32).tolist(),
        "param_std": (train_df[PARAM_COLS].std().to_numpy(dtype=np.float32) + 1e-8).tolist(),
        "target_mean": train_df[TARGET_COLS].mean().to_numpy(dtype=np.float32).tolist(),
        "target_std": (train_df[TARGET_COLS].std().to_numpy(dtype=np.float32) + 1e-8).tolist(),
    }


# 消融实验：从最简基线逐步加组件，观察每步提升
# baseline = 纯参数 MLP，每步新增一个组件
ABLATION_CONFIGS = {
    "baseline": {"use_cbam": False, "use_params": True,  "use_pi": False, "use_gp": False, "desc": "基线：纯参数 MLP"},
    "mask":     {"use_cbam": False, "use_params": True,  "use_pi": False, "use_gp": False, "desc": "+ 几何掩码编码器 + 参数融合"},
    "cbam":     {"use_cbam": True,  "use_params": True,  "use_pi": False, "use_gp": False, "desc": "+ CBAM 注意力"},
    "pi":       {"use_cbam": True,  "use_params": True,  "use_pi": True,  "use_gp": False, "desc": "+ 物理约束损失"},
    "gp":       {"use_cbam": True,  "use_params": True,  "use_pi": True,  "use_gp": True,  "desc": "+ 梯度惩罚（完整模型）"},
}


def make_model(name: str) -> nn.Module:
    cfg = ABLATION_CONFIGS.get(name)
    if cfg is None:
        raise ValueError(f"未知模型: {name}，可选: {list(ABLATION_CONFIGS)}")
    if name == "baseline":
        return ParamMLP()
    return FusionModel(use_cbam=cfg["use_cbam"], use_params=cfg["use_params"])


def denorm_tensor(y_norm: torch.Tensor, stats: dict, device: torch.device) -> torch.Tensor:
    mean = torch.tensor(stats["target_mean"], dtype=torch.float32, device=device)
    std = torch.tensor(stats["target_std"], dtype=torch.float32, device=device)
    return y_norm * std + mean


def physics_loss(y_norm: torch.Tensor, target_norm: torch.Tensor, stats: dict, nu0: float, f0: float, device: torch.device) -> torch.Tensor:
    """物理约束损失：正值惩罚 + eta = (Nu/Nu0) / (f/f0)^(1/3) 一致性。"""
    pred = denorm_tensor(y_norm, stats, device)
    true = denorm_tensor(target_norm, stats, device)
    nu_pred = pred[:, 0]
    f_pred = torch.clamp(pred[:, 1], min=1e-8)
    nu_true = true[:, 0]
    f_true = torch.clamp(true[:, 1], min=1e-8)
    eta_pred = (nu_pred / nu0) / torch.pow(f_pred / f0, 1.0 / 3.0)
    eta_true = (nu_true / nu0) / torch.pow(f_true / f0, 1.0 / 3.0)
    positive_penalty = torch.mean(torch.relu(-pred[:, 0]) ** 2 + torch.relu(-pred[:, 1]) ** 2)
    eta_penalty = F.mse_loss(eta_pred, eta_true)
    return positive_penalty + 0.1 * eta_penalty


def gradient_penalty(model: nn.Module, mask: torch.Tensor, params: torch.Tensor) -> torch.Tensor:
    """WGAN-GP 风格梯度惩罚：约束输出对输入参数的梯度范数接近 1，增强平滑性。"""
    params_gp = params.clone().requires_grad_(True)
    pred = model(mask, params_gp)
    gradients = torch.autograd.grad(
        outputs=pred.sum(), inputs=params_gp, create_graph=True,
    )[0]
    return ((gradients.norm(2, dim=1) - 1) ** 2).mean()


def train_epoch(model: nn.Module, loader: DataLoader, optimizer, device: torch.device, stats: dict, nu0: float, f0: float, pi_weight: float, gp_weight: float = 0.0) -> float:
    model.train()
    total_loss = 0.0
    total_n = 0
    for batch in loader:
        mask = batch["mask"].to(device)
        params = batch["params"].to(device)
        target = batch["target"].to(device)
        pred = model(mask, params)
        loss = F.mse_loss(pred, target)
        if pi_weight > 0:
            loss = loss + pi_weight * physics_loss(pred, target, stats, nu0, f0, device)
        if gp_weight > 0:
            loss = loss + gp_weight * gradient_penalty(model, mask, params)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        n = mask.size(0)
        total_loss += float(loss.item()) * n
        total_n += n
    return total_loss / max(total_n, 1)


@torch.no_grad()
def eval_loss(model: nn.Module, loader: DataLoader, device: torch.device, stats: dict, nu0: float, f0: float, pi_weight: float) -> float:
    model.eval()
    total_loss = 0.0
    total_n = 0
    for batch in loader:
        mask = batch["mask"].to(device)
        params = batch["params"].to(device)
        target = batch["target"].to(device)
        pred = model(mask, params)
        loss = F.mse_loss(pred, target)
        if pi_weight > 0:
            loss = loss + pi_weight * physics_loss(pred, target, stats, nu0, f0, device)
        n = mask.size(0)
        total_loss += float(loss.item()) * n
        total_n += n
    return total_loss / max(total_n, 1)


@torch.no_grad()
def predict_all(model: nn.Module, loader: DataLoader, stats: dict, device: torch.device) -> tuple[np.ndarray, np.ndarray, list[int]]:
    model.eval()
    pred_list, true_list, case_ids = [], [], []
    mean = np.asarray(stats["target_mean"], dtype=np.float32)
    std = np.asarray(stats["target_std"], dtype=np.float32)
    for batch in loader:
        pred_norm = model(batch["mask"].to(device), batch["params"].to(device)).cpu().numpy()
        true_norm = batch["target"].numpy()
        pred_list.append(pred_norm * std + mean)
        true_list.append(true_norm * std + mean)
        case_ids.extend(batch["case_id"].numpy().astype(int).tolist())
    return np.vstack(true_list), np.vstack(pred_list), case_ids


def calc_metrics(true: np.ndarray, pred: np.ndarray, nu0: float, f0: float) -> dict:
    metrics = {}
    for idx, name in enumerate(["Nu", "f"]):
        mse = mean_squared_error(true[:, idx], pred[:, idx])
        metrics[f"{name}_R2"] = float(r2_score(true[:, idx], pred[:, idx]))
        metrics[f"{name}_MAE"] = float(mean_absolute_error(true[:, idx], pred[:, idx]))
        metrics[f"{name}_RMSE"] = float(math.sqrt(mse))
    eta_true = (true[:, 0] / nu0) / np.power(np.maximum(true[:, 1], 1e-12) / f0, 1.0 / 3.0)
    eta_pred = (pred[:, 0] / nu0) / np.power(np.maximum(pred[:, 1], 1e-12) / f0, 1.0 / 3.0)
    metrics["eta_R2"] = float(r2_score(eta_true, eta_pred))
    metrics["eta_MAE"] = float(mean_absolute_error(eta_true, eta_pred))
    return metrics


def plot_history(history: list[dict], out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot([row["epoch"] for row in history], [row["train_loss"] for row in history], label="train")
    ax.plot([row["epoch"] for row in history], [row["val_loss"] for row in history], label="val")
    ax.set_xlabel("Epoch")
    ax.set_ylabel("Loss")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def plot_scatter(true: np.ndarray, pred: np.ndarray, out_path: Path, title: str) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(9, 4))
    for idx, name in enumerate(["Nu", "f"]):
        ax = axes[idx]
        ax.scatter(true[:, idx], pred[:, idx], s=18, alpha=0.75)
        vmin = min(float(true[:, idx].min()), float(pred[:, idx].min()))
        vmax = max(float(true[:, idx].max()), float(pred[:, idx].max()))
        ax.plot([vmin, vmax], [vmin, vmax], "r--", linewidth=1)
        ax.set_xlabel(f"CFD true {name}")
        ax.set_ylabel(f"Predicted {name}")
        ax.set_title(name)
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def plot_ablation(summary: pd.DataFrame, out_path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    x = np.arange(len(summary))
    axes[0].bar(x - 0.2, summary["Nu_R2"], width=0.4, label="Nu")
    axes[0].bar(x + 0.2, summary["f_R2"], width=0.4, label="f")
    axes[0].set_ylabel("R2")
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(summary["model"], rotation=20, ha="right")
    axes[0].legend()
    axes[1].bar(x - 0.2, summary["Nu_MAE"], width=0.4, label="Nu")
    axes[1].bar(x + 0.2, summary["f_MAE"], width=0.4, label="f")
    axes[1].set_ylabel("MAE")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(summary["model"], rotation=20, ha="right")
    axes[1].legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def run_one_model(name: str, loaders: dict, stats: dict, nu0: float, f0: float, args, device: torch.device) -> dict:
    out_dir = ensure_dir(Path(args.output_dir) / name)
    # 跳过已完成的模型
    history_file = out_dir / "train_history.csv"
    metrics_file = out_dir / "metrics.json"
    if history_file.exists() and metrics_file.exists():
        print(f"[SKIP] {name} 已训练完成，跳过")
        import json as _json
        existing = _json.loads(metrics_file.read_text(encoding="utf-8"))
        return {"model": name, **existing}
    cfg = ABLATION_CONFIGS.get(name, {})
    write_json(out_dir / "config.json", cfg)
    model = make_model(name).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    pi_weight = args.pi_weight if cfg.get("use_pi", False) else 0.0
    # 梯度惩罚需要 use_gp=True 且模型输出依赖 params
    gp_weight = args.gp_weight if (cfg.get("use_gp", False) and cfg.get("use_params", True)) else 0.0
    best_val = float("inf")
    history = []
    best_path = out_dir / "best_model.pth"
    for epoch in range(1, args.epochs + 1):
        train_loss = train_epoch(model, loaders["train"], optimizer, device, stats, nu0, f0, pi_weight, gp_weight)
        val_loss = eval_loss(model, loaders["val"], device, stats, nu0, f0, pi_weight)
        history.append({"epoch": epoch, "train_loss": train_loss, "val_loss": val_loss})
        if val_loss < best_val:
            best_val = val_loss
            torch.save(model.state_dict(), best_path)
        print(f"[INFO] {name} epoch={epoch} train={train_loss:.6f} val={val_loss:.6f}")

    model.load_state_dict(torch.load(best_path, map_location=device))
    true, pred, case_ids = predict_all(model, loaders["test"], stats, device)
    metrics = calc_metrics(true, pred, nu0, f0)
    pd.DataFrame(history).to_csv(out_dir / "train_history.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame({
        "case_id": case_ids,
        "Nu_true": true[:, 0],
        "Nu_pred": pred[:, 0],
        "f_true": true[:, 1],
        "f_pred": pred[:, 1],
    }).to_csv(out_dir / "test_predictions.csv", index=False, encoding="utf-8-sig")
    write_json(out_dir / "metrics.json", metrics)
    plot_history(history, out_dir / "loss_curve.png")
    plot_scatter(true, pred, out_dir / "prediction_scatter.png", name)
    return {"model": name, **metrics}


def main() -> None:
    parser = argparse.ArgumentParser(description="七参数几何掩码代理模型消融实验")
    parser.add_argument("--labels", default=str(ROOT / "samples" / "labels_7param_1000.csv"))
    parser.add_argument("--mask-dir", default=str(ROOT / "masks_fixed_1000"))
    parser.add_argument(
        "--split-file",
        default=str(ROOT / "samples" / "dataset_split_1000.csv"),
        help="可选的数据集划分CSV；默认使用七参数目录内的划分文件，不读取旧六参数结果目录。",
    )
    parser.add_argument("--output-dir", default=str(ROOT / "ablation_results_1000"))
    parser.add_argument("--models", nargs="*", default=list(ABLATION_CONFIGS.keys()))
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--image-size", type=int, default=128)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--pi-weight", type=float, default=0.05)
    parser.add_argument("--gp-weight", type=float, default=0.01, help="梯度惩罚权重（WGAN-GP 风格）")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    out_dir = ensure_dir(Path(args.output_dir))
    df = load_labels(Path(args.labels))
    split_file = Path(args.split_file) if args.split_file else None
    train_idx, val_idx, test_idx = build_split(df, split_file, args.seed)
    stats = compute_stats(df, train_idx)
    nu0, f0 = baseline_from_labels(df)
    write_json(out_dir / "stats.json", {**stats, "baseline": {"Nu0": nu0, "f0": f0}})

    mask_dir = ensure_dir(Path(args.mask_dir))
    datasets = {
        "train": MaskParamDataset(df.iloc[train_idx], mask_dir, stats, args.image_size),
        "val": MaskParamDataset(df.iloc[val_idx], mask_dir, stats, args.image_size),
        "test": MaskParamDataset(df.iloc[test_idx], mask_dir, stats, args.image_size),
    }
    loaders = {
        name: DataLoader(ds, batch_size=args.batch_size, shuffle=(name == "train"))
        for name, ds in datasets.items()
    }
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[INFO] device={device} train={len(train_idx)} val={len(val_idx)} test={len(test_idx)}")

    rows = []
    for name in args.models:
        result = run_one_model(name, loaders, stats, nu0, f0, args, device)
        result["desc"] = ABLATION_CONFIGS.get(name, {}).get("desc", "")
        rows.append(result)
    summary = pd.DataFrame(rows)
    summary.to_csv(out_dir / "ablation_summary.csv", index=False, encoding="utf-8-sig")
    write_json(out_dir / "ablation_summary.json", rows)
    plot_ablation(summary, out_dir / "ablation_bar.png")
    print(f"[OK] 消融实验完成: {out_dir / 'ablation_summary.csv'}")


if __name__ == "__main__":
    main()
