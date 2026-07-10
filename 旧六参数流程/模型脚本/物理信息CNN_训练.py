#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))


"""Training script for PI-CNN-CBAM: Physics-Informed CNN with CBAM for Nu/f.

Data sources:
  - consol_cfddata/labels.csv          -> 6 params + Nu/f targets
  - consol_cfddata/case_{N}_cfd_solution/*.png  -> 3 field contour images
  - field_data_npz/grids_64x64.npz     -> T_grid(64x64) + mask for physics loss

Split: reuses ai_cnn_model_results/dataset_split.csv (375/75/50).
"""

import argparse
import glob
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
import torch.nn.functional as F_torch
from PIL import Image
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from torch.utils.data import DataLoader, Dataset

from 物理信息CNN_模型 import PICNNCBAM, physics_loss_laplacian

# --------------- constants ---------------
PARAM_COLS = ["Ta", "Twa", "Tb", "Ts", "Tt", "Tad"]
FIELD_PNGS = ["velocity_magnitude.png", "pressure.png", "temperature.png"]


# ============================================================
#  Dataset
# ============================================================

class PICNNDataset(Dataset):
    """Loads 3 PNG images + 6 params + 64x64 T_grid + mask."""

    def __init__(self, df, indices, data_dir, npz_dir,
                 param_stats, target_stats, t_grid_stats,
                 img_size=224):
        self.df = df.reset_index(drop=True)
        self.indices = list(indices)
        self.data_dir = data_dir
        self.img_size = img_size
        self.param_stats = param_stats
        self.target_stats = target_stats
        self.tg_mean, self.tg_std = t_grid_stats

        # Build case_id -> NPZ index mapping (same sorted-glob as 01_preprocess_grids.py)
        npz_files = sorted(glob.glob(os.path.join(npz_dir, "case_*_field.npz")))
        npz_cids = [int(os.path.basename(f).split("_")[1]) for f in npz_files]
        self.cid_to_npz = {cid: idx for idx, cid in enumerate(npz_cids)}

        # Pre-load grids and masks into memory (~25 MB)
        grids = np.load(os.path.join(npz_dir, "grids_64x64.npz"))
        self._T_all = grids["T_grid"]     # (500, 64, 64) float32
        self._mask_all = grids["mask"]    # (500, 64, 64) float32

        # Pre-load and resize all images (~600 MB for 224x224)
        self._images = {}
        for idx in self.indices:
            case_id = int(self.df.iloc[idx]["case_id"])
            case_dir = os.path.join(data_dir, f"case_{case_id}_cfd_solution")
            imgs = []
            for name in FIELD_PNGS:
                img = Image.open(os.path.join(case_dir, name)).convert("RGB")
                img = img.resize((img_size, img_size), Image.BILINEAR)
                arr = np.asarray(img, dtype=np.float32) / 255.0
                imgs.append(arr)
            # (3, 3, H, W): 3 fields x 3 RGB channels
            self._images[idx] = np.stack(imgs, axis=0)

    def __len__(self):
        return len(self.indices)

    def __getitem__(self, item):
        idx = self.indices[item]
        row = self.df.iloc[idx]

        # Images -> tensor (3, 3, H, W)
        images = torch.tensor(self._images[idx]).permute(0, 3, 1, 2)

        # Params -> z-score normalized
        params = []
        for col in PARAM_COLS:
            m = self.param_stats[f"{col}_mean"]
            s = self.param_stats[f"{col}_std"]
            params.append((float(row[col]) - m) / (s + 1e-8))
        scalars = torch.tensor(params, dtype=torch.float32)

        # Nu/f -> z-score normalized
        nu = (float(row["Nu"]) - self.target_stats["nu_mean"]) / (self.target_stats["nu_std"] + 1e-8)
        f = (float(row["f"]) - self.target_stats["f_mean"]) / (self.target_stats["f_std"] + 1e-8)
        target = torch.tensor([nu, f], dtype=torch.float32)

        # T_grid -> z-score normalized
        case_id = int(row["case_id"])
        npz_idx = self.cid_to_npz[case_id]
        t_grid = (self._T_all[npz_idx] - self.tg_mean) / (self.tg_std + 1e-8)
        t_grid = torch.tensor(t_grid, dtype=torch.float32).unsqueeze(0)  # (1, 64, 64)

        # Mask
        mask = torch.tensor(self._mask_all[npz_idx], dtype=torch.float32).unsqueeze(0)

        return {
            "images": images,
            "scalars": scalars,
            "target": target,
            "t_grid": t_grid,
            "mask": mask,
            "case_id": case_id,
        }


# ============================================================
#  Helpers
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
    required = ["case_id"] + PARAM_COLS + ["Nu", "f"]
    for col in required:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=required)
    df = df[(df["Nu"] > 0) & (df["f"] > 0)].copy()
    df["case_id"] = df["case_id"].astype(int)
    return df.sort_values("case_id").reset_index(drop=True)


def build_split(df, split_path, seed):
    """Reuse existing split file, or create new 75/15/10 split."""
    if os.path.exists(split_path):
        split_df = pd.read_csv(split_path)
        id_to_idx = {int(row.case_id): i for i, row in df.iterrows()}
        splits = {}
        for name in ("train", "val", "test"):
            cids = split_df.loc[split_df["split"] == name, "case_id"].astype(int).tolist()
            splits[name] = [id_to_idx[c] for c in cids if c in id_to_idx]
        if all(len(v) > 0 for v in splits.values()):
            print(f"[INFO] Reusing split: {split_path}")
            return splits["train"], splits["val"], splits["test"]

    rng = np.random.default_rng(seed)
    perm = rng.permutation(len(df))
    n_train = int(0.75 * len(perm))
    n_val = int(0.15 * len(perm))
    return perm[:n_train].tolist(), perm[n_train:n_train + n_val].tolist(), perm[n_train + n_val:].tolist()


def compute_stats(df, train_idx):
    """Z-score stats from training set only."""
    tdf = df.iloc[train_idx]
    ps = {}
    for col in PARAM_COLS:
        ps[f"{col}_mean"] = float(tdf[col].mean())
        ps[f"{col}_std"] = float(tdf[col].std())
    ts = {
        "nu_mean": float(tdf["Nu"].mean()),
        "nu_std": float(tdf["Nu"].std()),
        "f_mean": float(tdf["f"].mean()),
        "f_std": float(tdf["f"].std()),
    }
    return ps, ts


def compute_tgrid_stats(npz_dir, df, train_idx):
    """Compute T_grid z-score stats from training cases."""
    npz_files = sorted(glob.glob(os.path.join(npz_dir, "case_*_field.npz")))
    npz_cids = [int(os.path.basename(f).split("_")[1]) for f in npz_files]
    cid_to_npz = {cid: idx for idx, cid in enumerate(npz_cids)}

    grids = np.load(os.path.join(npz_dir, "grids_64x64.npz"))
    T_all = grids["T_grid"]

    train_cids = df.iloc[train_idx]["case_id"].astype(int).tolist()
    train_npz_idx = [cid_to_npz[c] for c in train_cids if c in cid_to_npz]
    T_train = T_all[train_npz_idx]
    return float(T_train.mean()), float(T_train.std())


def denormalize(y_norm, stats):
    y = np.asarray(y_norm, dtype=float).copy()
    y[:, 0] = y[:, 0] * (stats["nu_std"] + 1e-8) + stats["nu_mean"]
    y[:, 1] = y[:, 1] * (stats["f_std"] + 1e-8) + stats["f_mean"]
    return y


def mape_pct(y_true, y_pred):
    return float(np.mean(np.abs((y_true - y_pred) / np.maximum(np.abs(y_true), 1e-12))) * 100)


def calc_metrics(y_true, y_pred, prefix):
    mse = float(mean_squared_error(y_true, y_pred))
    return {
        f"{prefix}_R2": float(r2_score(y_true, y_pred)),
        f"{prefix}_MSE": mse,
        f"{prefix}_RMSE": float(np.sqrt(mse)),
        f"{prefix}_MAE": float(mean_absolute_error(y_true, y_pred)),
        f"{prefix}_MAPE_pct": mape_pct(y_true, y_pred),
    }


# ============================================================
#  Training & Evaluation
# ============================================================

def train_one_epoch(model, loader, optimizer, device, alpha, lam):
    model.train()
    total = s_s = s_f = s_p = 0.0
    for batch in loader:
        imgs = batch["images"].to(device)
        sca = batch["scalars"].to(device)
        tgt = batch["target"].to(device)
        tg = batch["t_grid"].to(device)
        msk = batch["mask"].to(device)

        nu_f, field = model(imgs, sca, return_field=True)

        loss_nu = F_torch.mse_loss(nu_f[:, 0], tgt[:, 0])
        loss_f = F_torch.mse_loss(nu_f[:, 1], tgt[:, 1])
        loss_field = F_torch.mse_loss(field * msk, tg * msk)
        loss_phys = physics_loss_laplacian(field, msk)
        loss = loss_nu + loss_f + alpha * loss_field + lam * loss_phys

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        bs = imgs.size(0)
        total += bs
        s_s += loss_nu.item() * bs
        s_f += loss_f.item() * bs
        s_p += loss_phys.item() * bs
    return s_s / total, s_f / total, s_p / total


@torch.no_grad()
def eval_model(model, loader, device, alpha, lam):
    model.eval()
    total = s_s = s_f = s_p = 0.0
    for batch in loader:
        imgs = batch["images"].to(device)
        sca = batch["scalars"].to(device)
        tgt = batch["target"].to(device)
        tg = batch["t_grid"].to(device)
        msk = batch["mask"].to(device)

        nu_f, field = model(imgs, sca, return_field=True)
        loss_nu = F_torch.mse_loss(nu_f[:, 0], tgt[:, 0])
        loss_f = F_torch.mse_loss(nu_f[:, 1], tgt[:, 1])
        loss_field = F_torch.mse_loss(field * msk, tg * msk)
        loss_phys = physics_loss_laplacian(field, msk)
        loss = loss_nu + loss_f + alpha * loss_field + lam * loss_phys

        bs = imgs.size(0)
        total += bs
        s_s += loss_nu.item() * bs
        s_f += loss_f.item() * bs
        s_p += loss_phys.item() * bs
    return s_s / total, s_f / total, s_p / total


@torch.no_grad()
def full_evaluate(model, loader, target_stats, device):
    """Full test evaluation with denormalized metrics."""
    model.eval()
    all_true, all_pred, all_cids = [], [], []
    for batch in loader:
        imgs = batch["images"].to(device)
        sca = batch["scalars"].to(device)
        nu_f = model(imgs, sca, return_field=False)
        # In eval mode without return_field, model returns tensor directly
        if isinstance(nu_f, tuple):
            nu_f = nu_f[0]
        all_true.append(batch["target"].numpy())
        all_pred.append(nu_f.cpu().numpy())
        all_cids.extend(batch["case_id"])

    true_real = denormalize(np.vstack(all_true), target_stats)
    pred_real = denormalize(np.vstack(all_pred), target_stats)

    metrics = {}
    metrics.update(calc_metrics(true_real[:, 0], pred_real[:, 0], "Nu"))
    metrics.update(calc_metrics(true_real[:, 1], pred_real[:, 1], "f"))

    print("\n===== Test Metrics =====")
    print(f"  Nu: R2={metrics['Nu_R2']:.4f}  RMSE={metrics['Nu_RMSE']:.4f}  "
          f"MAE={metrics['Nu_MAE']:.4f}  MAPE={metrics['Nu_MAPE_pct']:.2f}%")
    print(f"  f:  R2={metrics['f_R2']:.4f}  RMSE={metrics['f_RMSE']:.6f}  "
          f"MAE={metrics['f_MAE']:.6f}  MAPE={metrics['f_MAPE_pct']:.2f}%")

    # eta = Nu / f^(1/3)
    eta_pred = pred_real[:, 0] / np.maximum(pred_real[:, 1], 1e-12) ** (1.0 / 3)
    eta_true = true_real[:, 0] / np.maximum(true_real[:, 1], 1e-12) ** (1.0 / 3)
    print(f"  eta: R2={r2_score(eta_true, eta_pred):.4f}  "
          f"MAE={mean_absolute_error(eta_true, eta_pred):.4f}")

    return metrics


# ============================================================
#  Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Train PI-CNN-CBAM for Nu/f prediction")
    parser.add_argument("--labels", default=os.path.join("consol_cfddata", "labels.csv"))
    parser.add_argument("--data-dir", default="consol_cfddata")
    parser.add_argument("--npz-dir", default=os.path.join("consol_cfddata", "field_data_npz"))
    parser.add_argument("--split-file", default=os.path.join("ai_cnn_model_results", "dataset_split.csv"))
    parser.add_argument("--output-dir", default="pi_cnn_nuf_results")
    parser.add_argument("--epochs", type=int, default=200)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=5e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--alpha", type=float, default=0.1,
                        help="Weight for auxiliary field MSE loss")
    parser.add_argument("--lam", type=float, default=0.001,
                        help="Weight for Laplacian physics loss")
    parser.add_argument("--img-size", type=int, default=224)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    set_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[INFO] Device: {device}")

    # ---- Load data ----
    df = load_labels(args.labels)
    train_idx, val_idx, test_idx = build_split(df, args.split_file, args.seed)
    print(f"[INFO] Split: train={len(train_idx)} val={len(val_idx)} test={len(test_idx)}")

    param_stats, target_stats = compute_stats(df, train_idx)
    tg_mean, tg_std = compute_tgrid_stats(args.npz_dir, df, train_idx)
    print(f"[INFO] T_grid stats: mean={tg_mean:.1f}K  std={tg_std:.1f}K")

    # ---- Datasets ----
    train_ds = PICNNDataset(df, train_idx, args.data_dir, args.npz_dir,
                            param_stats, target_stats, (tg_mean, tg_std), args.img_size)
    val_ds = PICNNDataset(df, val_idx, args.data_dir, args.npz_dir,
                          param_stats, target_stats, (tg_mean, tg_std), args.img_size)
    test_ds = PICNNDataset(df, test_idx, args.data_dir, args.npz_dir,
                           param_stats, target_stats, (tg_mean, tg_std), args.img_size)

    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True,
                              num_workers=2, pin_memory=True)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False,
                            num_workers=2, pin_memory=True)
    test_loader = DataLoader(test_ds, batch_size=args.batch_size, shuffle=False,
                             num_workers=2, pin_memory=True)

    # ---- Model ----
    model = PICNNCBAM(num_fields=3, num_scalars=6, output_size=2,
                      img_size=args.img_size).to(device)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"[INFO] Model: {n_params:,} params")

    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=30, gamma=0.5)

    # ---- Training loop ----
    best_val = float("inf")
    best_epoch = 0
    patience_ctr = 0
    history = []

    for epoch in range(1, args.epochs + 1):
        tr_nu, tr_f, tr_p = train_one_epoch(model, train_loader, optimizer, device,
                                             args.alpha, args.lam)
        v_nu, v_f, v_p = eval_model(model, val_loader, device, args.alpha, args.lam)
        scheduler.step()

        val_total = v_nu + v_f + args.alpha * 0  # track scalar loss for model selection
        history.append({
            "epoch": epoch,
            "train_nu": tr_nu, "train_f": tr_f, "train_phys": tr_p,
            "val_nu": v_nu, "val_f": v_f, "val_phys": v_p,
        })

        if val_total < best_val:
            best_val = val_total
            best_epoch = epoch
            patience_ctr = 0
            save_path = os.path.join(args.output_dir, "pi_cnn_nuf_best.pt")
            torch.save(model.state_dict(), save_path)
        else:
            patience_ctr += 1

        if epoch % 10 == 0 or epoch == 1:
            print(f"Epoch [{epoch}/{args.epochs}]  "
                  f"Train Nu={tr_nu:.5f} f={tr_f:.5f} phys={tr_p:.2e}  "
                  f"Val Nu={v_nu:.5f} f={v_f:.5f}  "
                  f"{'*' if patience_ctr == 0 else ''}")

        if patience_ctr >= 50:
            print(f"[INFO] Early stop at epoch {epoch} (50 epochs no improvement)")
            break

    print(f"\n[INFO] Best model: epoch {best_epoch}, val_scalar_loss={best_val:.6f}")

    # ---- Final evaluation ----
    model.load_state_dict(torch.load(
        os.path.join(args.output_dir, "pi_cnn_nuf_best.pt"), map_location=device))
    metrics = full_evaluate(model, test_loader, target_stats, device)

    # ---- Save ----
    with open(os.path.join(args.output_dir, "pi_cnn_nuf_metrics.json"), "w", encoding="utf-8") as f:
        json.dump({k: float(v) for k, v in metrics.items()}, f, indent=4, ensure_ascii=False)
    pd.DataFrame(history).to_csv(
        os.path.join(args.output_dir, "pi_cnn_nuf_history.csv"), index=False, encoding="utf-8-sig")
    with open(os.path.join(args.output_dir, "pi_cnn_nuf_stats.json"), "w", encoding="utf-8") as f:
        json.dump({"param": param_stats, "target": target_stats,
                    "t_grid_mean": tg_mean, "t_grid_std": tg_std}, f, indent=4)
    print(f"\n[INFO] Results saved to: {args.output_dir}")


if __name__ == "__main__":
    main()
