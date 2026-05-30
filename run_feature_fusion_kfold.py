#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Run 5-fold validation for the multimodal feature-fusion surrogate model."""

import argparse
import json
import os

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.model_selection import KFold

from train_multimodal_feature_model import (
    PARAM_COLS,
    TARGET_COLS,
    build_features,
    load_labels,
    metrics_for,
    model_candidates,
)


def format_metric(value, digits=4):
    return f"{float(value):.{digits}f}"


def summarize_fold_metrics(rows):
    metric_keys = [key for key in rows[0] if key not in {"fold", "train_count", "val_count"}]
    summary = {}
    for key in metric_keys:
        values = np.asarray([row[key] for row in rows], dtype=float)
        summary[f"{key}_mean"] = float(values.mean())
        summary[f"{key}_std"] = float(values.std(ddof=1))
    return summary


def save_kfold_outputs(rows, summary, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    pd.DataFrame(rows).to_csv(
        os.path.join(output_dir, "feature_fusion_kfold_metrics.csv"),
        index=False,
        encoding="utf-8-sig",
    )
    with open(os.path.join(output_dir, "feature_fusion_kfold_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=4, ensure_ascii=False)

    md_path = os.path.join(output_dir, "feature_fusion_kfold_summary.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("| 指标 | 平均值 | 标准差 |\n")
        f.write("|---|---:|---:|\n")
        for target in ("Nu", "f"):
            for metric in ("R2", "RMSE", "MAE", "MAPE_percent"):
                digits = 6 if target == "f" and metric in {"RMSE", "MAE"} else 4
                mean_key = f"{target}_{metric}_mean"
                std_key = f"{target}_{metric}_std"
                f.write(
                    f"| {target} {metric.replace('_percent', '/%')} | "
                    f"{format_metric(summary[mean_key], digits)} | "
                    f"{format_metric(summary[std_key], digits)} |\n"
                )
    return md_path


def run_feature_fusion_kfold(args):
    df = load_labels(args.labels)
    if args.num_samples:
        df = df.head(args.num_samples).copy()

    features, targets = build_features(df, args.data_dir, args.image_size)
    kfold = KFold(n_splits=args.k_folds, shuffle=True, random_state=args.seed)
    base_model = model_candidates(args.seed)[args.model]

    rows = []
    for fold_id, (train_idx, val_idx) in enumerate(kfold.split(features), start=1):
        model = clone(base_model)
        model.fit(features[train_idx], targets[train_idx])
        pred = model.predict(features[val_idx])
        metrics = metrics_for(targets[val_idx], pred)
        rows.append(
            {
                "fold": fold_id,
                "train_count": int(len(train_idx)),
                "val_count": int(len(val_idx)),
                **{key: float(value) for key, value in metrics.items()},
            }
        )
        print(
            f"[INFO] Fold {fold_id}/{args.k_folds}: "
            f"Nu_R2={metrics['Nu_R2']:.4f}, f_R2={metrics['f_R2']:.4f}"
        )

    summary = {
        "model": args.model,
        "k_folds": args.k_folds,
        "sample_count": int(len(df)),
        "image_size": args.image_size,
        **summarize_fold_metrics(rows),
    }
    md_path = save_kfold_outputs(rows, summary, args.output_dir)
    print(f"[INFO] Saved K-fold summary: {md_path}")


def main():
    parser = argparse.ArgumentParser(description="Validate multimodal feature-fusion model with K-fold split.")
    parser.add_argument("--labels", default=os.path.join("consol_cfddata", "labels.csv"))
    parser.add_argument("--data-dir", default="consol_cfddata")
    parser.add_argument("--output-dir", default=os.path.join("ai_cnn_model_results", "feature_fusion_kfold_5"))
    parser.add_argument("--image-size", type=int, default=24)
    parser.add_argument("--k-folds", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--model", default="FeatureMLP", choices=tuple(model_candidates(42).keys()))
    parser.add_argument("--num-samples", type=int, default=None)
    args = parser.parse_args()
    run_feature_fusion_kfold(args)


if __name__ == "__main__":
    main()
