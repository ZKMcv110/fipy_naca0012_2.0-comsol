#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""基于当前 1000 组数据和 MLP-CNN 代理模型做参数敏感性分析。"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from sklearn.ensemble import RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.preprocessing import MinMaxScaler


ROOT = Path(__file__).resolve().parent
PARAM_NAMES = ["Ta", "Twa", "Tb", "Ts", "Tt", "Tad", "theta"]
TARGET_NAMES = ["Nu", "f", "eta"]
DATASET = ROOT / "data" / "field_reconstruction_dataset_full.npz"
MODEL_DIR = ROOT / "results" / "mlp_cnn_field_multiloss_e10"
BEST_PATH = ROOT / "optimization_results" / "mlp_cnn_de_multiloss_e10" / "best_params.json"
OUT_DIR = ROOT / "analysis_results" / "sensitivity"


def load_de_module():
    path = ROOT / "03_DE优化eta.py"
    spec = importlib.util.spec_from_file_location("mlp_cnn_de", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载模块: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_arrays() -> tuple[pd.DataFrame, np.ndarray]:
    data = np.load(DATASET, allow_pickle=True)
    params = pd.DataFrame(data["params"], columns=PARAM_NAMES)
    targets = pd.DataFrame(data["targets"], columns=["Nu", "f"])
    targets["eta"] = data["eta"].reshape(-1)
    df = pd.concat([params, targets], axis=1)
    return df, data["params"]


def compute_correlations(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    pearson = df[PARAM_NAMES + TARGET_NAMES].corr(method="pearson").loc[PARAM_NAMES, TARGET_NAMES]
    spearman = df[PARAM_NAMES + TARGET_NAMES].corr(method="spearman").loc[PARAM_NAMES, TARGET_NAMES]
    return pearson, spearman


def compute_rf_importance(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    x = df[PARAM_NAMES].to_numpy()
    x = MinMaxScaler().fit_transform(x)
    for target in TARGET_NAMES:
        y = df[target].to_numpy()
        model = RandomForestRegressor(n_estimators=300, random_state=42, min_samples_leaf=3, n_jobs=-1)
        model.fit(x, y)
        perm = permutation_importance(model, x, y, n_repeats=15, random_state=42, n_jobs=-1)
        for name, impurity, permutation in zip(PARAM_NAMES, model.feature_importances_, perm.importances_mean):
            rows.append(
                {
                    "target": target,
                    "parameter": name,
                    "rf_impurity_importance": float(impurity),
                    "rf_permutation_importance": float(max(permutation, 0.0)),
                }
            )
    return pd.DataFrame(rows)


def predict_eta_for_params(params: np.ndarray) -> float:
    module = load_de_module()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model, stats = module.load_model(MODEL_DIR, device)
    pred = module.predict(model, stats, params.astype(np.float32), device)
    return float(pred["eta_pred"])


def local_perturbation(df: pd.DataFrame) -> pd.DataFrame:
    best = json.loads(BEST_PATH.read_text(encoding="utf-8"))["best_params"]
    center = np.asarray([float(best[name]) for name in PARAM_NAMES], dtype=np.float32)
    mins = df[PARAM_NAMES].min().to_numpy(dtype=np.float32)
    maxs = df[PARAM_NAMES].max().to_numpy(dtype=np.float32)
    ranges = np.maximum(maxs - mins, 1e-6)
    rows = []
    for idx, name in enumerate(PARAM_NAMES):
        values = np.linspace(
            max(mins[idx], center[idx] - 0.2 * ranges[idx]),
            min(maxs[idx], center[idx] + 0.2 * ranges[idx]),
            21,
        )
        etas = []
        for value in values:
            vec = center.copy()
            vec[idx] = value
            etas.append(predict_eta_for_params(vec))
        rows.append(
            {
                "parameter": name,
                "value_min": float(values.min()),
                "value_max": float(values.max()),
                "eta_min": float(np.min(etas)),
                "eta_max": float(np.max(etas)),
                "eta_range": float(np.max(etas) - np.min(etas)),
                "eta_center": float(predict_eta_for_params(center)),
            }
        )
    return pd.DataFrame(rows).sort_values("eta_range", ascending=False)


def save_bar(df: pd.DataFrame, target: str, value_col: str, path: Path, title: str) -> None:
    sub = df[df["target"] == target].sort_values(value_col, ascending=True)
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.barh(sub["parameter"], sub[value_col], color="#267c8d")
    ax.set_xlabel(value_col)
    ax.set_title(title)
    ax.grid(axis="x", linestyle="--", linewidth=0.5, alpha=0.35)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def save_nu_f_bar(df: pd.DataFrame, path: Path) -> None:
    pivot = df.pivot(index="parameter", columns="target", values="rf_permutation_importance").loc[PARAM_NAMES]
    fig, ax = plt.subplots(figsize=(8.0, 4.4))
    x = np.arange(len(PARAM_NAMES))
    width = 0.36
    ax.bar(x - width / 2, pivot["Nu"], width, label="Nu", color="#1f77b4")
    ax.bar(x + width / 2, pivot["f"], width, label="f", color="#d9822b")
    ax.set_xticks(x)
    ax.set_xticklabels(PARAM_NAMES)
    ax.set_ylabel("Permutation importance")
    ax.set_title("Parameter sensitivity for Nu and f")
    ax.legend()
    ax.grid(axis="y", linestyle="--", linewidth=0.5, alpha=0.35)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def save_local_bar(local: pd.DataFrame, path: Path) -> None:
    sub = local.sort_values("eta_range", ascending=True)
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.barh(sub["parameter"], sub["eta_range"], color="#6f5aa7")
    ax.set_xlabel("eta variation around DE optimum")
    ax.set_title("Local perturbation sensitivity of eta")
    ax.grid(axis="x", linestyle="--", linewidth=0.5, alpha=0.35)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df, _ = load_arrays()
    pearson, spearman = compute_correlations(df)
    rf = compute_rf_importance(df)
    local = local_perturbation(df)

    pearson.to_csv(OUT_DIR / "pearson_correlation.csv", encoding="utf-8-sig")
    spearman.to_csv(OUT_DIR / "spearman_correlation.csv", encoding="utf-8-sig")
    rf.to_csv(OUT_DIR / "rf_importance.csv", index=False, encoding="utf-8-sig")
    local.to_csv(OUT_DIR / "local_perturbation_eta.csv", index=False, encoding="utf-8-sig")

    save_bar(rf, "eta", "rf_permutation_importance", OUT_DIR / "sensitivity_bar_eta.png", "Parameter sensitivity for eta")
    save_nu_f_bar(rf, OUT_DIR / "sensitivity_bar_Nu_f.png")
    save_local_bar(local, OUT_DIR / "local_perturbation_eta.png")

    summary = {
        "data_source": str(DATASET),
        "model_dir": str(MODEL_DIR),
        "method": [
            "Pearson/Spearman correlation on 1000 CFD labels",
            "RandomForest impurity and permutation importance",
            "Local one-factor perturbation around DE optimum using current MLP-CNN model",
        ],
        "eta_top_rf_permutation": rf[rf["target"] == "eta"]
        .sort_values("rf_permutation_importance", ascending=False)
        .head(3)
        .to_dict(orient="records"),
        "eta_top_local": local.head(3).to_dict(orient="records"),
        "notes": "敏感性分析是数据驱动统计分析和代理模型局部扰动分析，不等同于固定其余参数的严格 CFD 单因素扫描。",
    }
    (OUT_DIR / "sensitivity_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    md = [
        "# 参数敏感性分析结果",
        "",
        "## 方法",
        "",
        "- Pearson/Spearman 相关性：基于 1000 组 CFD 标签。",
        "- 随机森林重要性：基于七参数对 Nu、f、eta 的统计解释。",
        "- 局部扰动：在 DE 最优点附近单参数扰动，使用当前 MLP-CNN 代理模型预测 eta。",
        "",
        "## eta 的随机森林重要性前三",
        "",
    ]
    for row in summary["eta_top_rf_permutation"]:
        md.append(f"- {row['parameter']}: permutation importance = {row['rf_permutation_importance']:.6f}")
    md += ["", "## eta 的局部扰动敏感性前三", ""]
    for row in summary["eta_top_local"]:
        md.append(f"- {row['parameter']}: eta_range = {row['eta_range']:.6f}")
    md += [
        "",
        "## 结论边界",
        "",
        "该结果可用于解释当前样本分布和代理模型最优点附近的参数影响趋势；不能替代严格的 CFD 单因素扫描。",
    ]
    (OUT_DIR / "sensitivity_summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
