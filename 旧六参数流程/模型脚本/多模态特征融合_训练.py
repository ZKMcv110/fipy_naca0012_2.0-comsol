#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Train fast multimodal regressors using geometry plus field-image features.

This is a practical small-data multimodal baseline. It does not relabel results:
it uses the same train/validation/test split and selects the model by validation
performance before reporting test metrics.
"""

import argparse
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(errors="replace")

import joblib
import numpy as np
import pandas as pd
from PIL import Image
from sklearn.ensemble import ExtraTreesRegressor, GradientBoostingRegressor, RandomForestRegressor
from sklearn.kernel_ridge import KernelRidge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.multioutput import MultiOutputRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.compose import TransformedTargetRegressor


PARAM_COLS = ["Ta", "Twa", "Tb", "Ts", "Tt", "Tad"]
TARGET_COLS = ["Nu", "f"]
FIELD_FILES = ["velocity_magnitude.png", "pressure.png", "temperature.png"]


def load_labels(path):
    df = pd.read_csv(path)
    required = ["case_id"] + PARAM_COLS + TARGET_COLS
    for col in required:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=required)
    df = df[(df["Nu"] > 0) & (df["f"] > 0)].copy()
    df["case_id"] = df["case_id"].astype(int)
    return df.sort_values("case_id").reset_index(drop=True)


def build_split(df, split_path):
    split_df = pd.read_csv(split_path)
    id_to_idx = {int(row.case_id): i for i, row in df.iterrows()}
    result = {}
    for split in ("train", "val", "test"):
        case_ids = split_df.loc[split_df["split"] == split, "case_id"].astype(int).tolist()
        result[split] = [id_to_idx[cid] for cid in case_ids if cid in id_to_idx]
    return result["train"], result["val"], result["test"]


def image_features(path, size):
    img = Image.open(path).convert("RGB").resize((size, size))
    arr = np.asarray(img, dtype=np.float32) / 255.0
    gray = arr.mean(axis=2)

    stats = []
    for channel in [arr[:, :, 0], arr[:, :, 1], arr[:, :, 2], gray]:
        stats.extend([
            channel.mean(),
            channel.std(),
            channel.min(),
            channel.max(),
            np.percentile(channel, 5),
            np.percentile(channel, 25),
            np.percentile(channel, 50),
            np.percentile(channel, 75),
            np.percentile(channel, 95),
        ])

    # Low-resolution spatial signature keeps some field layout information.
    spatial = gray.reshape(size, size)
    row_profile = spatial.mean(axis=1)
    col_profile = spatial.mean(axis=0)
    return np.concatenate([np.asarray(stats, dtype=np.float32), row_profile, col_profile])


def build_features(df, data_dir, image_size):
    rows = []
    for _, row in df.iterrows():
        case_id = int(row["case_id"])
        case_dir = os.path.join(data_dir, f"case_{case_id}_cfd_solution")
        feat = [float(row[col]) for col in PARAM_COLS]
        for name in FIELD_FILES:
            feat.extend(image_features(os.path.join(case_dir, name), image_size))
        rows.append(feat)
    return np.asarray(rows, dtype=np.float32), df[TARGET_COLS].to_numpy(dtype=np.float32)


def mape_percent(y_true, y_pred):
    return float(np.mean(np.abs((y_true - y_pred) / np.maximum(np.abs(y_true), 1e-12))) * 100.0)


def target_metrics(y_true, y_pred, prefix):
    mse = float(mean_squared_error(y_true, y_pred))
    return {
        f"{prefix}_R2": float(r2_score(y_true, y_pred)),
        f"{prefix}_MSE": mse,
        f"{prefix}_RMSE": float(np.sqrt(mse)),
        f"{prefix}_MAE": float(mean_absolute_error(y_true, y_pred)),
        f"{prefix}_MAPE_percent": mape_percent(y_true, y_pred),
    }


def metrics_for(y_true, y_pred):
    metrics = {}
    metrics.update(target_metrics(y_true[:, 0], y_pred[:, 0], "Nu"))
    metrics.update(target_metrics(y_true[:, 1], y_pred[:, 1], "f"))
    return metrics


def score(metrics):
    return metrics["Nu_R2"] + metrics["f_R2"] - 0.02 * (
        metrics["Nu_MAPE_percent"] + metrics["f_MAPE_percent"]
    )


def model_candidates(seed):
    return {
        "ExtraTrees": ExtraTreesRegressor(
            n_estimators=600,
            max_features=0.65,
            min_samples_leaf=1,
            random_state=seed,
            n_jobs=1,
        ),
        "RandomForest": RandomForestRegressor(
            n_estimators=500,
            max_features=0.7,
            min_samples_leaf=1,
            random_state=seed,
            n_jobs=1,
        ),
        "GradientBoosting": MultiOutputRegressor(
            GradientBoostingRegressor(
                n_estimators=420,
                learning_rate=0.035,
                max_depth=2,
                min_samples_leaf=3,
                random_state=seed,
            )
        ),
        "FeatureMLP": TransformedTargetRegressor(
            regressor=MLPRegressor(
                hidden_layer_sizes=(160, 96, 48),
                activation="relu",
                solver="adam",
                alpha=1e-3,
                learning_rate_init=5e-4,
                max_iter=3000,
                early_stopping=True,
                validation_fraction=0.18,
                n_iter_no_change=100,
                random_state=seed,
            ),
            transformer=StandardScaler(),
        ),
        "KernelRidge": KernelRidge(alpha=0.25, kernel="rbf", gamma=0.015),
    }


def save_outputs(args, name, model, metrics, y_true, y_pred, case_ids):
    os.makedirs(args.output_dir, exist_ok=True)
    prefix = os.path.join(args.output_dir, "multimodal_feature")
    joblib.dump(model, prefix + "_model.joblib")
    with open(prefix + "_metrics.json", "w", encoding="utf-8") as f:
        json.dump({"model": name, **{k: float(v) for k, v in metrics.items()}}, f, indent=4)

    pred_df = pd.DataFrame({
        "case_id": case_ids,
        "true_Nu": y_true[:, 0],
        "pred_Nu": y_pred[:, 0],
        "error_Nu": y_pred[:, 0] - y_true[:, 0],
        "true_f": y_true[:, 1],
        "pred_f": y_pred[:, 1],
        "error_f": y_pred[:, 1] - y_true[:, 1],
    })
    pred_df.to_csv(prefix + "_predictions.csv", index=False, encoding="utf-8-sig")

    mlp_metrics_path = os.path.join(args.output_dir, "mlp_baseline_metrics.json")
    if os.path.exists(mlp_metrics_path):
        with open(mlp_metrics_path, "r", encoding="utf-8") as f:
            mlp_metrics = json.load(f)

        rows = [
            {
                "model": "MLP",
                "input": "6 geometry parameters",
                "target": "Nu",
                "R2": mlp_metrics["Nu_R2"],
                "MSE": mlp_metrics["Nu_MSE"],
                "RMSE": mlp_metrics["Nu_RMSE"],
                "MAE": mlp_metrics["Nu_MAE"],
                "MAPE_percent": mlp_metrics["Nu_MAPE_percent"],
            },
            {
                "model": "MLP",
                "input": "6 geometry parameters",
                "target": "f",
                "R2": mlp_metrics["f_R2"],
                "MSE": mlp_metrics["f_MSE"],
                "RMSE": mlp_metrics["f_RMSE"],
                "MAE": mlp_metrics["f_MAE"],
                "MAPE_percent": mlp_metrics["f_MAPE_percent"],
            },
            {
                "model": "Multimodal-Fusion",
                "input": "geometry parameters + field image features",
                "target": "Nu",
                "R2": metrics["Nu_R2"],
                "MSE": metrics["Nu_MSE"],
                "RMSE": metrics["Nu_RMSE"],
                "MAE": metrics["Nu_MAE"],
                "MAPE_percent": metrics["Nu_MAPE_percent"],
            },
            {
                "model": "Multimodal-Fusion",
                "input": "geometry parameters + field image features",
                "target": "f",
                "R2": metrics["f_R2"],
                "MSE": metrics["f_MSE"],
                "RMSE": metrics["f_RMSE"],
                "MAE": metrics["f_MAE"],
                "MAPE_percent": metrics["f_MAPE_percent"],
            },
        ]
        comparison_df = pd.DataFrame(rows)
        comparison_csv = os.path.join(args.output_dir, "paper_table8_model_comparison.csv")
        comparison_md = os.path.join(args.output_dir, "paper_table8_model_comparison.md")
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
        print(f"[INFO] Updated paper Table 8 comparison: {comparison_csv}")

    print(f"[INFO] Saved multimodal feature model: {prefix}_model.joblib")


def main():
    parser = argparse.ArgumentParser(description="Train fast multimodal image-feature regressors.")
    parser.add_argument("--labels", default=os.path.join("consol_cfddata", "labels.csv"))
    parser.add_argument("--data-dir", default="consol_cfddata")
    parser.add_argument("--split-file", default=os.path.join("ai_cnn_model_results", "dataset_split.csv"))
    parser.add_argument("--output-dir", default="ai_cnn_model_results")
    parser.add_argument("--image-size", type=int, default=24)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    df = load_labels(args.labels)
    train_idx, val_idx, test_idx = build_split(df, args.split_file)
    print(f"[INFO] Split sizes: train={len(train_idx)}, val={len(val_idx)}, test={len(test_idx)}")
    print("[INFO] Extracting geometry + field-image features...")
    x, y = build_features(df, args.data_dir, args.image_size)

    x_train, y_train = x[train_idx], y[train_idx]
    x_val, y_val = x[val_idx], y[val_idx]
    x_test, y_test = x[test_idx], y[test_idx]

    best = None
    for name, regressor in model_candidates(args.seed).items():
        model = make_pipeline(StandardScaler(), regressor)
        model.fit(x_train, y_train)
        val_pred = model.predict(x_val)
        val_metrics = metrics_for(y_val, val_pred)
        val_score = score(val_metrics)
        print(f"[INFO] {name} validation score={val_score:.6f}, Nu_R2={val_metrics['Nu_R2']:.4f}, f_R2={val_metrics['f_R2']:.4f}")
        if best is None or val_score > best["score"]:
            best = {"name": name, "model": model, "score": val_score, "val_metrics": val_metrics}

    test_pred = best["model"].predict(x_test)
    test_metrics = metrics_for(y_test, test_pred)
    print(f"[INFO] Selected model by validation score: {best['name']}")
    print("[INFO] Multimodal feature test metrics:")
    for key, value in test_metrics.items():
        print(f"  {key}: {value:.6f}")

    test_case_ids = df.iloc[test_idx]["case_id"].astype(int).tolist()
    save_outputs(args, best["name"], best["model"], test_metrics, y_test, test_pred, test_case_ids)


if __name__ == "__main__":
    main()
