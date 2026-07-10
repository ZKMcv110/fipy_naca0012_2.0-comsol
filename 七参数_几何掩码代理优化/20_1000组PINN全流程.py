#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""1000 组数据集 + PINN 全流程串联脚本。

在现有 500 组 theta500_v2（case_id 20001-20500）基础上，
新增 500 组 LHS 采样（case_id 30001-30500），合并为 1000 组。

步骤：
1. LHS 采样 500 组新样本（如已有则跳过）
2. COMSOL 批量求解新样本（支持断点续跑）
3. 合并两组标签为 1000 组
4. 生成 1000 组几何掩码
5. 创建数据集划分（75/15/10）
6. 训练 PINN 消融模型

用法：
    # 全流程（COMSOL 完成后自动继续）
    python 20_1000组PINN全流程.py

    # 只做采样（不启动 COMSOL）
    python 20_1000组PINN全流程.py --only-sample

    # COMSOL 已跑完，直接从合并标签开始
    python 20_1000组PINN全流程.py --skip-comsol
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from common import PARAM_COLS, ROOT, TARGET_COLS, ensure_dir

PYTHON = sys.executable

# ---- 路径常量 ----
EXTRA_SEED = 123
EXTRA_COUNT = 500
EXTRA_CASE_ID_START = 30001

V2_SAMPLES = ROOT / "samples" / "samples_7param_theta500_v2.csv"
EXTRA_SAMPLES = ROOT / "samples" / "samples_7param_1000_extra.csv"

V2_COMSOL_DIR = ROOT / "comsol_results_theta500_v2"
EXTRA_COMSOL_DIR = ROOT / "comsol_results_1000_extra"

LABELS_1000 = ROOT / "samples" / "labels_7param_1000.csv"
MASK_DIR_1000 = ROOT / "masks_fixed_1000"
SPLIT_FILE_1000 = ROOT / "samples" / "dataset_split_1000.csv"
ABLATION_OUTPUT_1000 = ROOT / "ablation_results_1000"


def run_cmd(cmd: list[str], label: str, env_extra: dict | None = None) -> subprocess.CompletedProcess:
    """运行子进程，统一处理编码和输出。"""
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    if env_extra:
        env.update(env_extra)
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    try:
        print(result.stdout)
    except UnicodeEncodeError:
        pass
    if result.returncode != 0:
        try:
            print(f"[ERROR] {result.stderr}")
        except UnicodeEncodeError:
            pass
        raise RuntimeError(f"{label} 失败")
    return result


def step1_sample_extra() -> None:
    """LHS 采样 500 组新样本。"""
    print("\n" + "=" * 60)
    print("[步骤 1/6] LHS 采样 500 组新样本")
    print("=" * 60)

    if EXTRA_SAMPLES.exists():
        existing = len(pd.read_csv(EXTRA_SAMPLES))
        if existing >= EXTRA_COUNT:
            print(f"[SKIP] 已有 {existing} 组新样本: {EXTRA_SAMPLES}")
            return

    cmd = [
        PYTHON, str(ROOT / "01_七参数LHS采样.py"),
        "--num-samples", str(EXTRA_COUNT),
        "--seed", str(EXTRA_SEED),
        "--case-id-start", str(EXTRA_CASE_ID_START),
        "--output", str(EXTRA_SAMPLES),
    ]
    run_cmd(cmd, "LHS 采样")
    df = pd.read_csv(EXTRA_SAMPLES)
    print(f"[OK] 新样本: {len(df)} 组, case_id {df['case_id'].min()}-{df['case_id'].max()}")
    print(f"[OK] theta 范围: {df['theta'].min():.4f} ~ {df['theta'].max():.4f}")


def step2_comsol_extra() -> None:
    """COMSOL 批量求解 500 组新样本。"""
    print("\n" + "=" * 60)
    print("[步骤 2/6] COMSOL 批量求解新样本")
    print("=" * 60)

    cmd = [
        PYTHON, str(ROOT / "02_七参数COMSOL批量求解.py"),
        "--samples", str(EXTRA_SAMPLES),
        "--output-dir", str(EXTRA_COMSOL_DIR),
        "--timeout", "900",
    ]
    run_cmd(cmd, "COMSOL 批量求解")


def _rebuild_labels_from_results(results_dir: Path) -> pd.DataFrame:
    """从 COMSOL 结果目录重建标签 DataFrame。"""
    rows = []
    for result_path in sorted(results_dir.glob("case_*/result.json")):
        data = json.loads(result_path.read_text(encoding="utf-8"))
        if data.get("Nu") is None or data.get("f") is None:
            continue
        if data.get("failure_reason"):
            continue
        rows.append({
            "case_id": data.get("case_id", int(result_path.parent.name.split("_")[-1])),
            **{name: data.get(name) for name in PARAM_COLS},
            **{name: data.get(name) for name in TARGET_COLS},
            "delta_p": data.get("delta_p"),
            "delta_T": data.get("delta_T"),
            "Q_total": data.get("Q_total"),
            "image_complete": data.get("image_complete", False),
            "failure_reason": "",
        })
    if not rows:
        raise RuntimeError(f"未找到成功求解结果: {results_dir}")
    return pd.DataFrame(rows).sort_values("case_id").reset_index(drop=True)


def step3_merge_labels() -> None:
    """合并 v2 (500) + extra (500) 为 1000 组标签。"""
    print("\n" + "=" * 60)
    print("[步骤 3/6] 合并两组标签为 1000 组")
    print("=" * 60)

    v2_labels = ROOT / "samples" / "labels_7param_theta500_v2.csv"
    if v2_labels.exists():
        df_v2 = pd.read_csv(v2_labels)
    else:
        print(f"[INFO] v2 标签不存在，从 COMSOL 结果重建: {V2_COMSOL_DIR}")
        df_v2 = _rebuild_labels_from_results(V2_COMSOL_DIR)

    df_extra = _rebuild_labels_from_results(EXTRA_COMSOL_DIR)

    overlap = set(df_v2["case_id"].astype(int)) & set(df_extra["case_id"].astype(int))
    if overlap:
        raise ValueError(f"case_id 冲突: {sorted(overlap)[:10]}")

    merged = pd.concat([df_v2, df_extra], ignore_index=True).sort_values("case_id").reset_index(drop=True)
    ensure_dir(LABELS_1000.parent)
    merged.to_csv(LABELS_1000, index=False, encoding="utf-8-sig")

    print(f"[OK] 合并标签: {LABELS_1000}")
    print(f"[OK] v2 样本: {len(df_v2)}, 新增样本: {len(df_extra)}, 合计: {len(merged)}")
    print(f"[OK] theta 范围: {merged['theta'].min():.4f} ~ {merged['theta'].max():.4f}")
    print(f"[OK] theta 唯一值: {merged['theta'].nunique()}")


def step4_generate_masks() -> None:
    """生成 1000 组几何掩码。"""
    print("\n" + "=" * 60)
    print("[步骤 4/6] 生成几何掩码图")
    print("=" * 60)

    cmd = [
        PYTHON, str(ROOT / "04_生成几何掩码图.py"),
        "--labels", str(LABELS_1000),
        "--output-dir", str(MASK_DIR_1000),
        "--image-size", "128",
    ]
    run_cmd(cmd, "掩码生成")


def step5_create_split() -> None:
    """创建 1000 组数据集划分（75/15/10）。"""
    print("\n" + "=" * 60)
    print("[步骤 5/6] 创建数据集划分")
    print("=" * 60)

    df = pd.read_csv(LABELS_1000)
    df = df.dropna(subset=["case_id"] + PARAM_COLS + TARGET_COLS)
    df = df[(df["Nu"] > 0) & (df["f"] > 0)]

    rng = np.random.default_rng(42)
    indices = rng.permutation(len(df))
    n_train = int(0.75 * len(indices))
    n_val = int(0.15 * len(indices))
    train_idx = indices[:n_train]
    val_idx = indices[n_train:n_train + n_val]
    test_idx = indices[n_train + n_val:]

    rows = []
    for idx in train_idx:
        rows.append({"split": "train", "row_index": int(idx), "case_id": int(df.iloc[idx]["case_id"])})
    for idx in val_idx:
        rows.append({"split": "val", "row_index": int(idx), "case_id": int(df.iloc[idx]["case_id"])})
    for idx in test_idx:
        rows.append({"split": "test", "row_index": int(idx), "case_id": int(df.iloc[idx]["case_id"])})

    split_df = pd.DataFrame(rows)
    ensure_dir(SPLIT_FILE_1000.parent)
    split_df.to_csv(SPLIT_FILE_1000, index=False, encoding="utf-8-sig")
    print(f"[OK] 数据集划分: {SPLIT_FILE_1000}")
    print(f"[OK] 有效样本: {len(df)}, train={len(train_idx)}, val={len(val_idx)}, test={len(test_idx)}")


def step6_train_ablation() -> None:
    """训练 PINN 消融模型。"""
    print("\n" + "=" * 60)
    print("[步骤 6/6] 训练 PINN 消融模型")
    print("=" * 60)

    cmd = [
        PYTHON, str(ROOT / "09_消融实验_PI_CNN_CBAM.py"),
        "--labels", str(LABELS_1000),
        "--mask-dir", str(MASK_DIR_1000),
        "--split-file", str(SPLIT_FILE_1000),
        "--output-dir", str(ABLATION_OUTPUT_1000),
        "--epochs", "100",
        "--batch-size", "32",
        "--image-size", "128",
        "--lr", "1e-3",
        "--weight-decay", "1e-4",
        "--pi-weight", "0.05",
        "--gp-weight", "0.01",
        "--seed", "42",
    ]
    result = subprocess.run(cmd, capture_output=False, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError("消融训练失败")


def check_comsol_progress(results_dir: Path, expected: int) -> tuple[int, int]:
    """检查 COMSOL 完成度。"""
    if not results_dir.exists():
        return 0, expected
    result_files = list(results_dir.glob("case_*/result.json"))
    success = 0
    for path in result_files:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("Nu") is not None and data.get("f") is not None and not data.get("failure_reason"):
            success += 1
    return success, expected


def main() -> None:
    parser = argparse.ArgumentParser(description="1000 组数据集 + PINN 全流程")
    parser.add_argument("--only-sample", action="store_true", help="只做 LHS 采样，不启动 COMSOL")
    parser.add_argument("--skip-comsol", action="store_true", help="跳过 COMSOL 求解（已完成时）")
    args = parser.parse_args()

    print("=" * 60)
    print("1000 组数据集 + PINN 全流程")
    print("=" * 60)

    step1_sample_extra()

    if args.only_sample:
        print("\n[完成] 仅采样模式，已生成 500 组新样本")
        return

    if not args.skip_comsol:
        step2_comsol_extra()
    else:
        success, expected = check_comsol_progress(EXTRA_COMSOL_DIR, EXTRA_COUNT)
        print(f"\n[跳过 COMSOL] 当前进度: {success}/{expected}")
        if success < 10:
            raise RuntimeError(f"成功求解仅 {success} 组，不足以继续")

    step3_merge_labels()
    step4_generate_masks()
    step5_create_split()
    step6_train_ablation()

    print("\n" + "=" * 60)
    print("[完成] 全流程执行完毕")
    print(f"  标签文件: {LABELS_1000}")
    print(f"  掩码目录: {MASK_DIR_1000}")
    print(f"  数据划分: {SPLIT_FILE_1000}")
    print(f"  消融结果: {ABLATION_OUTPUT_1000}")
    print("=" * 60)


if __name__ == "__main__":
    main()
