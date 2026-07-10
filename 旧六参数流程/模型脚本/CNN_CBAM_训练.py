#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))


"""
CNN+CBAM+GAP 模型训练脚本
基于 cnnstep1.py 的 GAP 防过拟合版本 (AdaptiveAvgPool 1x1)

功能：
  1. 加载 500 个 CFD 算例的流场图像 + 6 个几何参数
  2. 使用 Z-score 归一化，仅用训练集统计量（防数据泄露）
  3. 复用 dataset_split.csv 确保与其他模型公平对比
  4. 训练后自动输出评估指标、散点图、论文表格数据
"""

import argparse
import json
import os
import sys

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(errors="replace")

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from PIL import Image
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from torch.utils.data import DataLoader, Dataset
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from CNN_CBAM_GAP_模型定义 import CFDFieldToPerformanceCNN

# ============================================================
#  常量
# ============================================================
PARAM_COLS = ["Ta", "Twa", "Tb", "Ts", "Tt", "Tad"]
TARGET_COLS = ["Nu", "f"]
FIELD_PNGS = ["velocity_magnitude.png", "pressure.png", "temperature.png"]


# ============================================================
#  数据集
# ============================================================
class CFDDataset(Dataset):
    """加载 3 张流场 PNG + 6 个几何参数 -> Nu/f"""

    def __init__(self, df, indices, data_dir, stats, img_size=224):
        self.df = df.reset_index(drop=True)
        self.indices = list(indices)
        self.data_dir = data_dir
        self.img_size = img_size
        self.p_stats = stats["param"]
        self.t_stats = stats["target"]

    def __len__(self):
        return len(self.indices)

    def __getitem__(self, item):
        idx = self.indices[item]
        row = self.df.iloc[idx]
        case_id = int(row["case_id"])

        # --- 图像 ---
        case_dir = os.path.join(self.data_dir, f"case_{case_id}_cfd_solution")
        imgs = []
        for name in FIELD_PNGS:
            img = Image.open(os.path.join(case_dir, name)).convert("RGB")
            img = img.resize((self.img_size, self.img_size), Image.BILINEAR)
            arr = np.asarray(img, dtype=np.float32) / 255.0
            # 标准化到 [-1, 1]
            arr = (arr - 0.5) / 0.5
            imgs.append(arr)
        images = torch.tensor(np.stack(imgs)).permute(0, 3, 1, 2)  # (3, 3, H, W)

        # --- 参数 Z-score ---
        params = []
        for col in PARAM_COLS:
            m = self.p_stats[f"{col}_mean"]
            s = self.p_stats[f"{col}_std"]
            params.append((float(row[col]) - m) / (s + 1e-8))
        scalars = torch.tensor(params, dtype=torch.float32)

        # --- 目标 Z-score ---
        nu = (float(row["Nu"]) - self.t_stats["nu_mean"]) / (self.t_stats["nu_std"] + 1e-8)
        f  = (float(row["f"])  - self.t_stats["f_mean"])  / (self.t_stats["f_std"]  + 1e-8)
        target = torch.tensor([nu, f], dtype=torch.float32)

        return {"images": images, "scalars": scalars, "target": target, "case_id": case_id}


# ============================================================
#  工具函数
# ============================================================
def set_seed(seed):
    import random
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def load_labels(path):
    df = pd.read_csv(path)
    required = ["case_id"] + PARAM_COLS + TARGET_COLS
    for col in required:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=required)
    df = df[(df["Nu"] > 0) & (df["f"] > 0)].copy()
    df["case_id"] = df["case_id"].astype(int)
    return df.sort_values("case_id").reset_index(drop=True)


def build_split(df, split_path, seed):
    """复用已有 split 文件，或新建 75/15/10 划分"""
    if os.path.exists(split_path):
        split_df = pd.read_csv(split_path)
        id_to_idx = {int(r.case_id): i for i, r in df.iterrows()}
        splits = {}
        for name in ("train", "val", "test"):
            cids = split_df.loc[split_df["split"] == name, "case_id"].astype(int).tolist()
            splits[name] = [id_to_idx[c] for c in cids if c in id_to_idx]
        if all(len(v) > 0 for v in splits.values()):
            print(f"[INFO] 复用已有划分: {split_path}")
            return splits["train"], splits["val"], splits["test"]

    rng = np.random.default_rng(seed)
    perm = rng.permutation(len(df))
    n_train = int(0.75 * len(perm))
    n_val = int(0.15 * len(perm))
    return perm[:n_train].tolist(), perm[n_train:n_train + n_val].tolist(), perm[n_train + n_val:].tolist()


def compute_stats(df, train_idx):
    """仅用训练集计算 Z-score 统计量"""
    tdf = df.iloc[train_idx]
    ps = {}
    for col in PARAM_COLS:
        ps[f"{col}_mean"] = float(tdf[col].mean())
        ps[f"{col}_std"]  = float(tdf[col].std())
    ts = {
        "nu_mean": float(tdf["Nu"].mean()), "nu_std": float(tdf["Nu"].std()),
        "f_mean":  float(tdf["f"].mean()),  "f_std":  float(tdf["f"].std()),
    }
    return {"param": ps, "target": ts}


def denormalize(y_norm, stats):
    y = np.asarray(y_norm, dtype=float).copy()
    y[:, 0] = y[:, 0] * (stats["nu_std"] + 1e-8) + stats["nu_mean"]
    y[:, 1] = y[:, 1] * (stats["f_std"]  + 1e-8) + stats["f_mean"]
    return y


def mape_pct(y_true, y_pred):
    return float(np.mean(np.abs((y_true - y_pred) / np.maximum(np.abs(y_true), 1e-12))) * 100)


def calc_metrics(y_true, y_pred, prefix):
    mse = float(mean_squared_error(y_true, y_pred))
    return {
        f"{prefix}_R2":   float(r2_score(y_true, y_pred)),
        f"{prefix}_MSE":  mse,
        f"{prefix}_RMSE": float(np.sqrt(mse)),
        f"{prefix}_MAE":  float(mean_absolute_error(y_true, y_pred)),
        f"{prefix}_MAPE_pct": mape_pct(y_true, y_pred),
    }


# ============================================================
#  训练
# ============================================================
def train_one_epoch(model, loader, optimizer, criterion, device):
    model.train()
    total_loss, n = 0.0, 0
    for batch in loader:
        imgs = batch["images"].to(device)
        sca  = batch["scalars"].to(device)
        tgt  = batch["target"].to(device)
        optimizer.zero_grad()
        out = model(imgs, sca)
        loss = criterion(out, tgt)
        loss.backward()
        optimizer.step()
        total_loss += loss.item() * imgs.size(0)
        n += imgs.size(0)
    return total_loss / n


@torch.no_grad()
def eval_loss(model, loader, criterion, device):
    model.eval()
    total_loss, n = 0.0, 0
    for batch in loader:
        imgs = batch["images"].to(device)
        sca  = batch["scalars"].to(device)
        tgt  = batch["target"].to(device)
        out = model(imgs, sca)
        loss = criterion(out, tgt)
        total_loss += loss.item() * imgs.size(0)
        n += imgs.size(0)
    return total_loss / n


@torch.no_grad()
def full_evaluate(model, loader, stats, device):
    """完整测试评估 + 反归一化"""
    model.eval()
    all_true, all_pred, all_cids = [], [], []
    for batch in loader:
        imgs = batch["images"].to(device)
        sca  = batch["scalars"].to(device)
        out = model(imgs, sca)
        all_true.append(batch["target"].numpy())
        all_pred.append(out.cpu().numpy())
        all_cids.extend(batch["case_id"])

    true_real = denormalize(np.vstack(all_true), stats["target"])
    pred_real = denormalize(np.vstack(all_pred), stats["target"])

    metrics = {}
    metrics.update(calc_metrics(true_real[:, 0], pred_real[:, 0], "Nu"))
    metrics.update(calc_metrics(true_real[:, 1], pred_real[:, 1], "f"))
    return metrics, true_real, pred_real, all_cids


# ============================================================
#  绘图
# ============================================================
def plot_scatter(true_vals, pred_vals, save_dir):
    """Nu/f 真实值 vs 预测值散点图"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    for ax, col, color in [(ax1, 0, "#1f77b4"), (ax2, 1, "#ff7f0e")]:
        t = true_vals[:, col]
        p = pred_vals[:, col]
        m = calc_metrics(t, p, ["Nu", "f"][col])
        ax.scatter(t, p, alpha=0.75, c=color, edgecolors="white", s=56, linewidth=0.8)
        lo, hi = t.min() - abs(t.min()) * 0.05, t.max() + abs(t.max()) * 0.05
        ax.plot([lo, hi], [lo, hi], "r--", lw=2, label="y=x")
        ax.set_xlim(lo, hi); ax.set_ylim(lo, hi)
        name = ["Nu", "f"][col]
        r2 = m[f"{name}_R2"]
        mae = m[f"{name}_MAE"]
        ax.set_title(f"{name} (n={len(t)}, R2={r2:.3f}, MAE={mae:.4f})")
        ax.set_xlabel(f"CFD True {name}")
        ax.set_ylabel(f"Predicted {name}")
        ax.legend(); ax.grid(False)

    plt.tight_layout()
    path = os.path.join(save_dir, "cnn_cbam_gap_scatter.png")
    plt.savefig(path, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"[INFO] 散点图已保存: {path}")


def plot_history(history, save_dir):
    """训练损失收敛曲线"""
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot([h["train"] for h in history], label="Train Loss", linewidth=2)
    ax.plot([h["val"] for h in history], label="Val Loss", linewidth=2)
    ax.set_title("CNN+CBAM+GAP Training Convergence")
    ax.set_xlabel("Epoch"); ax.set_ylabel("MSE Loss")
    ax.legend(); ax.grid(True, alpha=0.3)
    path = os.path.join(save_dir, "cnn_cbam_gap_loss.png")
    plt.savefig(path, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"[INFO] 损失曲线已保存: {path}")


# ============================================================
#  主程序
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="训练 CNN+CBAM+GAP 模型预测 Nu/f")
    parser.add_argument("--labels",     default=os.path.join("consol_cfddata", "labels.csv"))
    parser.add_argument("--data-dir",   default="consol_cfddata")
    parser.add_argument("--split-file", default=os.path.join("ai_cnn_model_results", "dataset_split.csv"))
    parser.add_argument("--output-dir", default="cnn_cbam_gap_results")
    parser.add_argument("--epochs",     type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr",         type=float, default=5e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--img-size",   type=int, default=224)
    parser.add_argument("--seed",       type=int, default=42)
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    set_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[INFO] 设备: {device}")

    # ---- 加载数据 ----
    df = load_labels(args.labels)
    train_idx, val_idx, test_idx = build_split(df, args.split_file, args.seed)
    print(f"[INFO] 数据划分: train={len(train_idx)} val={len(val_idx)} test={len(test_idx)}")

    stats = compute_stats(df, train_idx)
    with open(os.path.join(args.output_dir, "dataset_stats.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=4, ensure_ascii=False)

    # ---- DataLoader ----
    train_ds = CFDDataset(df, train_idx, args.data_dir, stats, args.img_size)
    val_ds   = CFDDataset(df, val_idx,   args.data_dir, stats, args.img_size)
    test_ds  = CFDDataset(df, test_idx,  args.data_dir, stats, args.img_size)

    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True,  num_workers=2, pin_memory=True)
    val_loader   = DataLoader(val_ds,   batch_size=args.batch_size, shuffle=False, num_workers=2, pin_memory=True)
    test_loader  = DataLoader(test_ds,  batch_size=args.batch_size, shuffle=False, num_workers=2, pin_memory=True)

    # ---- 模型 (cnnstep1.py GAP 版本) ----
    model = CFDFieldToPerformanceCNN(num_fields=3, num_scalars=len(PARAM_COLS), output_size=2).to(device)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"[INFO] 模型参数量: {n_params:,}")

    optimizer = optim.Adam(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=30, gamma=0.5)
    criterion = nn.MSELoss()

    # ---- 训练循环 ----
    best_val = float("inf")
    patience = 0
    history = []

    for epoch in range(1, args.epochs + 1):
        tr = train_one_epoch(model, train_loader, optimizer, criterion, device)
        vl = eval_loss(model, val_loader, criterion, device)
        scheduler.step()
        history.append({"epoch": epoch, "train": tr, "val": vl})

        if vl < best_val:
            best_val = vl
            patience = 0
            torch.save(model.state_dict(), os.path.join(args.output_dir, "cnn_cbam_gap_best.pth"))
        else:
            patience += 1

        if epoch % 10 == 0 or epoch == 1:
            mark = "*" if patience == 0 else ""
            print(f"Epoch [{epoch}/{args.epochs}]  Train={tr:.6f}  Val={vl:.6f}  {mark}")

        if patience >= 40:
            print(f"[INFO] 早停: epoch {epoch} (40 轮无改善)")
            break

    print(f"[INFO] 最佳验证损失: {best_val:.6f}")

    # ---- 加载最佳模型 & 评估 ----
    model.load_state_dict(torch.load(os.path.join(args.output_dir, "cnn_cbam_gap_best.pth"), map_location=device))
    metrics, true_vals, pred_vals, case_ids = full_evaluate(model, test_loader, stats, device)

    print("\n===== 测试集指标 =====")
    print(f"  Nu: R2={metrics['Nu_R2']:.4f}  RMSE={metrics['Nu_RMSE']:.4f}  "
          f"MAE={metrics['Nu_MAE']:.4f}  MAPE={metrics['Nu_MAPE_pct']:.2f}%")
    print(f"  f:  R2={metrics['f_R2']:.4f}  RMSE={metrics['f_RMSE']:.6f}  "
          f"MAE={metrics['f_MAE']:.6f}  MAPE={metrics['f_MAPE_pct']:.2f}%")

    eta_pred = pred_vals[:, 0] / np.maximum(pred_vals[:, 1], 1e-12) ** (1.0 / 3)
    eta_true = true_vals[:, 0] / np.maximum(true_vals[:, 1], 1e-12) ** (1.0 / 3)
    print(f"  eta: R2={r2_score(eta_true, eta_pred):.4f}  MAE={mean_absolute_error(eta_true, eta_pred):.4f}")

    # ---- 保存结果 ----
    with open(os.path.join(args.output_dir, "cnn_cbam_gap_metrics.json"), "w", encoding="utf-8") as f:
        json.dump({k: float(v) for k, v in metrics.items()}, f, indent=4, ensure_ascii=False)

    pd.DataFrame(history).to_csv(
        os.path.join(args.output_dir, "cnn_cbam_gap_history.csv"), index=False, encoding="utf-8-sig")

    # 逐样本预测明细
    detail_df = pd.DataFrame({
        "case_id": case_ids,
        "true_Nu": true_vals[:, 0], "pred_Nu": pred_vals[:, 0],
        "true_f":  true_vals[:, 1], "pred_f":  pred_vals[:, 1],
    })
    detail_df.to_csv(os.path.join(args.output_dir, "cnn_cbam_gap_predictions.csv"),
                     index=False, encoding="utf-8-sig")

    # 绘图
    plot_scatter(true_vals, pred_vals, args.output_dir)
    plot_history(history, args.output_dir)

    print(f"\n[INFO] 全部结果已保存到: {args.output_dir}")


if __name__ == "__main__":
    main()
