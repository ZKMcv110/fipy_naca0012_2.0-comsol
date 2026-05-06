#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Train a scalar-only MLP baseline for the paper ablation table.

The model uses only the six geometry parameters:
Ta, Twa, Tb, Ts, Tt, Tad -> Nu, f

It reuses ai_cnn_model_results/dataset_split.csv when available so the MLP and
the multimodal CNN are evaluated on the same test cases.
"""

import argparse
import json
import os
import random
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
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from torch.utils.data import DataLoader, Dataset


PARAM_COLS = ["Ta", "Twa", "Tb", "Ts", "Tt", "Tad"]
TARGET_COLS = ["Nu", "f"]


class ScalarDataset(Dataset):
    def __init__(self, data_frame, indices, stats):
        self.data_frame = data_frame.reset_index(drop=True)
        self.indices = list(indices)
        self.stats = stats

    def __len__(self):
        return len(self.indices)

    def __getitem__(self, item):
        row = self.data_frame.iloc[self.indices[item]]
        x = []
        for col in PARAM_COLS:
            mean = self.stats["param"][f"{col}_mean"]
            std = self.stats["param"][f"{col}_std"]
            x.append((float(row[col]) - mean) / (std + 1e-8))

        y = [
            (float(row["Nu"]) - self.stats["target"]["nu_mean"]) / (self.stats["target"]["nu_std"] + 1e-8),
            (float(row["f"]) - self.stats["target"]["f_mean"]) / (self.stats["target"]["f_std"] + 1e-8),
        ]

        return {
            "x": torch.tensor(x, dtype=torch.float32),
            "y": torch.tensor(y, dtype=torch.float32),
            "case_id": int(row["case_id"]),
        }


class MLPBaseline(nn.Module):
    def __init__(self, input_size=6, output_size=2, dropout=0.15):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_size, 64),
            nn.ReLU(),
            nn.BatchNorm1d(64),
            nn.Dropout(dropout),
            nn.Linear(64, 128),
            nn.ReLU(),
            nn.BatchNorm1d(128),
            nn.Dropout(dropout),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, output_size),
        )

    def forward(self, x):
        return self.net(x)


def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def load_labels(labels_path):
    df = pd.read_csv(labels_path)
    required = ["case_id"] + PARAM_COLS + TARGET_COLS
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns in labels CSV: {missing}")

    for col in required:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=required).copy()
    df = df[(df["Nu"] > 0) & (df["f"] > 0)].copy()
    df["case_id"] = df["case_id"].astype(int)
    df = df.sort_values("case_id").reset_index(drop=True)
    return df


def build_split(df, split_path, seed):
    if os.path.exists(split_path):
        split_df = pd.read_csv(split_path)
        id_to_idx = {int(row.case_id): i for i, row in df.iterrows()}
        splits = {}
        for split_name in ("train", "val", "test"):
            case_ids = split_df.loc[split_df["split"] == split_name, "case_id"].astype(int).tolist()
            indices = [id_to_idx[cid] for cid in case_ids if cid in id_to_idx]
            splits[split_name] = indices
        if all(len(splits[name]) > 0 for name in ("train", "val", "test")):
            print(f"[INFO] Reusing split file: {split_path}")
            return splits["train"], splits["val"], splits["test"]
        print(f"[WARN] Split file exists but is incomplete: {split_path}. Rebuilding split.")

    rng = np.random.default_rng(seed)
    indices = rng.permutation(len(df))
    train_size = int(0.75 * len(indices))
    val_size = int(0.15 * len(indices))
    train_idx = indices[:train_size].tolist()
    val_idx = indices[train_size:train_size + val_size].tolist()
    test_idx = indices[train_size + val_size:].tolist()
    return train_idx, val_idx, test_idx


def calculate_stats(df, train_idx):
    train_df = df.iloc[train_idx]
    stats = {"param": {}, "target": {}}
    for col in PARAM_COLS:
        stats["param"][f"{col}_mean"] = float(train_df[col].mean())
        stats["param"][f"{col}_std"] = float(train_df[col].std())
    stats["target"]["nu_mean"] = float(train_df["Nu"].mean())
    stats["target"]["nu_std"] = float(train_df["Nu"].std())
    stats["target"]["f_mean"] = float(train_df["f"].mean())
    stats["target"]["f_std"] = float(train_df["f"].std())
    return stats


def denormalize(y_norm, stats):
    y_norm = np.asarray(y_norm)
    y = np.zeros_like(y_norm, dtype=float)
    y[:, 0] = y_norm[:, 0] * (stats["target"]["nu_std"] + 1e-8) + stats["target"]["nu_mean"]
    y[:, 1] = y_norm[:, 1] * (stats["target"]["f_std"] + 1e-8) + stats["target"]["f_mean"]
    return y


def mape_percent(true_values, pred_values):
    denom = np.maximum(np.abs(true_values), 1e-12)
    return float(np.mean(np.abs((true_values - pred_values) / denom)) * 100.0)


def target_metrics(true_values, pred_values, prefix):
    mse = float(mean_squared_error(true_values, pred_values))
    return {
        f"{prefix}_R2": float(r2_score(true_values, pred_values)),
        f"{prefix}_MSE": mse,
        f"{prefix}_RMSE": float(np.sqrt(mse)),
        f"{prefix}_MAE": float(mean_absolute_error(true_values, pred_values)),
        f"{prefix}_MAPE_percent": mape_percent(true_values, pred_values),
    }


def train_model(model, train_loader, val_loader, epochs, lr, weight_decay, device, save_path):
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)
    model.to(device)
    best_val = float("inf")
    history = []

    for epoch in range(epochs):
        model.train()
        train_loss = 0.0
        for batch in train_loader:
            x = batch["x"].to(device)
            y = batch["y"].to(device)
            optimizer.zero_grad()
            loss = criterion(model(x), y)
            loss.backward()
            optimizer.step()
            train_loss += loss.item() * x.size(0)

        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for batch in val_loader:
                x = batch["x"].to(device)
                y = batch["y"].to(device)
                loss = criterion(model(x), y)
                val_loss += loss.item() * x.size(0)

        train_loss /= len(train_loader.dataset)
        val_loss /= len(val_loader.dataset)
        history.append({"epoch": epoch + 1, "train_loss": train_loss, "val_loss": val_loss})

        if val_loss < best_val:
            best_val = val_loss
            torch.save(model.state_dict(), save_path)

        if (epoch + 1) % 20 == 0 or epoch == 0:
            print(f"Epoch [{epoch + 1}/{epochs}] train={train_loss:.6f} val={val_loss:.6f}")

    model.load_state_dict(torch.load(save_path, map_location=device))
    return history


def evaluate(model, loader, stats, device):
    model.to(device)
    model.eval()
    true_norm, pred_norm, case_ids = [], [], []
    with torch.no_grad():
        for batch in loader:
            x = batch["x"].to(device)
            y = batch["y"].cpu().numpy()
            pred = model(x).cpu().numpy()
            true_norm.extend(y)
            pred_norm.extend(pred)
            case_ids.extend([int(v) for v in batch["case_id"]])

    true_real = denormalize(np.asarray(true_norm), stats)
    pred_real = denormalize(np.asarray(pred_norm), stats)

    metrics = {}
    metrics.update(target_metrics(true_real[:, 0], pred_real[:, 0], "Nu"))
    metrics.update(target_metrics(true_real[:, 1], pred_real[:, 1], "f"))
    return metrics, true_real, pred_real, case_ids


def save_outputs(output_dir, metrics, true_vals, pred_vals, case_ids, history, stats, cnn_metrics_path):
    os.makedirs(output_dir, exist_ok=True)

    with open(os.path.join(output_dir, "mlp_baseline_metrics.json"), "w", encoding="utf-8") as f:
        json.dump({k: float(v) for k, v in metrics.items()}, f, indent=4)
    with open(os.path.join(output_dir, "mlp_baseline_stats.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=4)

    pd.DataFrame(history).to_csv(os.path.join(output_dir, "mlp_baseline_history.csv"), index=False, encoding="utf-8-sig")

    pred_df = pd.DataFrame({
        "case_id": case_ids,
        "true_Nu": true_vals[:, 0],
        "pred_Nu": pred_vals[:, 0],
        "error_Nu": pred_vals[:, 0] - true_vals[:, 0],
        "true_f": true_vals[:, 1],
        "pred_f": pred_vals[:, 1],
        "error_f": pred_vals[:, 1] - true_vals[:, 1],
    })
    pred_df.to_csv(os.path.join(output_dir, "mlp_baseline_predictions.csv"), index=False, encoding="utf-8-sig")

    mlp_table = pd.DataFrame([
        {
            "model": "MLP",
            "input": "6 geometry parameters",
            "target": "Nu",
            "R2": metrics["Nu_R2"],
            "MSE": metrics["Nu_MSE"],
            "RMSE": metrics["Nu_RMSE"],
            "MAE": metrics["Nu_MAE"],
            "MAPE_percent": metrics["Nu_MAPE_percent"],
        },
        {
            "model": "MLP",
            "input": "6 geometry parameters",
            "target": "f",
            "R2": metrics["f_R2"],
            "MSE": metrics["f_MSE"],
            "RMSE": metrics["f_RMSE"],
            "MAE": metrics["f_MAE"],
            "MAPE_percent": metrics["f_MAPE_percent"],
        },
    ])
    mlp_table.to_csv(os.path.join(output_dir, "mlp_baseline_table8_rows.csv"), index=False, encoding="utf-8-sig")

    comparison_rows = []
    if os.path.exists(cnn_metrics_path):
        cnn_df = pd.read_csv(cnn_metrics_path)
        for _, row in cnn_df.iterrows():
            comparison_rows.append({
                "model": "CBAM-CNN",
                "input": "geometry parameters + field images",
                "target": row["target"],
                "R2": row["R2"],
                "MSE": row["MSE"],
                "RMSE": row["RMSE"],
                "MAE": row["MAE"],
                "MAPE_percent": row["MAPE_percent"],
            })
    comparison_rows.extend(mlp_table.to_dict("records"))

    comparison_df = pd.DataFrame(comparison_rows)
    comparison_csv = os.path.join(output_dir, "paper_table8_model_comparison.csv")
    comparison_md = os.path.join(output_dir, "paper_table8_model_comparison.md")
    comparison_df.to_csv(comparison_csv, index=False, encoding="utf-8-sig")

    with open(comparison_md, "w", encoding="utf-8") as f:
        f.write("| Model | Input | Target | R2 | RMSE | MAE | MAPE/% |\n")
        f.write("|---|---|---|---:|---:|---:|---:|\n")
        for _, row in comparison_df.iterrows():
            f.write(
                f"| {row['model']} | {row['input']} | {row['target']} | "
                f"{float(row['R2']):.4f} | {float(row['RMSE']):.6g} | "
                f"{float(row['MAE']):.6g} | {float(row['MAPE_percent']):.3f} |\n"
            )

    print(f"[INFO] Saved MLP metrics and predictions to: {output_dir}")
    print(f"[INFO] Saved Table 8 comparison: {comparison_csv}")
    print(f"[INFO] Saved Table 8 markdown: {comparison_md}")


def main():
    parser = argparse.ArgumentParser(description="Train scalar-only MLP baseline for paper Table 8.")
    parser.add_argument("--labels", default=os.path.join("consol_cfddata", "labels.csv"))
    parser.add_argument("--output-dir", default="ai_cnn_model_results")
    parser.add_argument("--split-file", default=os.path.join("ai_cnn_model_results", "dataset_split.csv"))
    parser.add_argument("--cnn-metrics", default=os.path.join("ai_cnn_model_results", "paper_table7_metrics.csv"))
    parser.add_argument("--epochs", type=int, default=300)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    set_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[INFO] Device: {device}")

    df = load_labels(args.labels)
    train_idx, val_idx, test_idx = build_split(df, args.split_file, args.seed)
    print(f"[INFO] Split sizes: train={len(train_idx)}, val={len(val_idx)}, test={len(test_idx)}")

    stats = calculate_stats(df, train_idx)
    train_ds = ScalarDataset(df, train_idx, stats)
    val_ds = ScalarDataset(df, val_idx, stats)
    test_ds = ScalarDataset(df, test_idx, stats)

    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False)
    test_loader = DataLoader(test_ds, batch_size=args.batch_size, shuffle=False)

    model = MLPBaseline(input_size=len(PARAM_COLS), output_size=len(TARGET_COLS))
    model_path = os.path.join(args.output_dir, "mlp_baseline_model.pth")
    history = train_model(
        model,
        train_loader,
        val_loader,
        epochs=args.epochs,
        lr=args.lr,
        weight_decay=args.weight_decay,
        device=device,
        save_path=model_path,
    )

    metrics, true_vals, pred_vals, case_ids = evaluate(model, test_loader, stats, device)
    print("[INFO] MLP test metrics:")
    for key, value in metrics.items():
        print(f"  {key}: {value:.6f}")

    save_outputs(args.output_dir, metrics, true_vals, pred_vals, case_ids, history, stats, args.cnn_metrics)


if __name__ == "__main__":
    main()

