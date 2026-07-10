#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""构建 MLP-CNN 流热场重建数据集。

本脚本只读取已有七参数标签和全场 npz 文件，不修改旧目录。
输出一个合并后的训练数据集，并可选输出每个 case 的标准化 npz 文件。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
PARAM_COLS = ["Ta", "Twa", "Tb", "Ts", "Tt", "Tad", "theta"]
TARGET_COLS = ["Nu", "f"]
DEFAULT_FIELD_NAMES = ["u", "v", "p", "T"]
DERIVED_FIELD_NAMES = ["U"]


def parse_field_names(value: str) -> list[str]:
    names = [item.strip() for item in value.split(",") if item.strip()]
    if not names:
        raise ValueError("场通道不能为空")
    allowed = set(DEFAULT_FIELD_NAMES + DERIVED_FIELD_NAMES)
    invalid = [name for name in names if name not in allowed]
    if invalid:
        raise ValueError(f"不支持的场通道: {invalid}，可选: {DEFAULT_FIELD_NAMES + DERIVED_FIELD_NAMES}")
    return names


def eta_value(nu: np.ndarray, f_value: np.ndarray, nu0: float, f0: float) -> np.ndarray:
    return (nu / max(nu0, 1e-12)) / np.power(
        np.maximum(f_value, 1e-12) / max(f0, 1e-12),
        1.0 / 3.0,
    )


def infer_grid(data: np.lib.npyio.NpzFile) -> tuple[int, int]:
    xs = np.unique(data["x"])
    ys = np.unique(data["y"])
    if xs.size * ys.size != data["T"].size:
        raise ValueError(
            f"无法由 x/y 推断规则网格: unique_x={xs.size}, "
            f"unique_y={ys.size}, n={data['T'].size}"
        )
    return int(ys.size), int(xs.size)


def load_field(path: Path, field_names: list[str]) -> np.ndarray:
    data = np.load(path)
    height, width = infer_grid(data)
    channels = []
    for name in field_names:
        if name == "U":
            # COMSOL 速度云图使用 spf.U，即速度大小；由规则采样的 u/v 分量派生。
            u = data["u"].astype(np.float32)
            v = data["v"].astype(np.float32)
            values = np.sqrt(u * u + v * v)
        else:
            values = data[name].astype(np.float32)
        channels.append(values.reshape(height, width))
    return np.stack(channels, axis=0)


def nearest_baseline(labels: pd.DataFrame) -> tuple[float, float]:
    """用最接近原始结构的样本作为 eta 归一化基准。"""

    baseline = {"Ta": 0.0, "Twa": 0.40, "Tb": 0.12, "Ts": 1.10, "Tt": 0.85, "Tad": 0.0}
    dist = sum((labels[name].astype(float) - value) ** 2 for name, value in baseline.items())
    row = labels.loc[dist.idxmin()]
    return float(row["Nu"]), float(row["f"])


def export_case_npz(
    output_dir: Path,
    case_id: int,
    params: np.ndarray,
    field: np.ndarray,
    field_names: list[str],
    nu: float,
    f_value: float,
    eta: float,
) -> None:
    """输出目标要求的逐工况标准格式。"""

    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "params": params.astype(np.float32),
        "Nu": np.float32(nu),
        "f": np.float32(f_value),
        "eta": np.float32(eta),
        "param_names": np.asarray(PARAM_COLS),
        "field_names": np.asarray(field_names),
    }
    for idx, name in enumerate(field_names):
        payload[name] = field[idx].astype(np.float32)
    np.savez_compressed(output_dir / f"case_{case_id}.npz", **payload)


def main() -> None:
    parser = argparse.ArgumentParser(description="构建七参数 MLP-CNN 流热场重建数据集")
    parser.add_argument(
        "--labels",
        default=str(PROJECT_ROOT / "七参数_几何掩码代理优化" / "samples" / "labels_7param_1000.csv"),
        help="七参数标签 CSV，需包含 case_id、七参数、Nu、f",
    )
    parser.add_argument(
        "--field-dir",
        default=str(PROJECT_ROOT / "七参数_PDE_PINN尝试" / "field_data"),
        help="已有 CFD 全场 npz 目录，文件名形如 case_{case_id}_full.npz",
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "data" / "field_reconstruction_dataset.npz"),
        help="合并后的训练数据集输出路径",
    )
    parser.add_argument("--limit", type=int, default=0, help="只构建前 N 个可用样本；0 表示全部")
    parser.add_argument(
        "--field-names",
        default=",".join(DEFAULT_FIELD_NAMES),
        help="需要写入数据集的场通道，逗号分隔；论文 PVT 云图主线可传 p,U,T",
    )
    parser.add_argument(
        "--case-output-dir",
        default="",
        help="可选：输出逐工况标准 npz 目录，格式为 case_id.npz",
    )
    args = parser.parse_args()

    labels = pd.read_csv(args.labels)
    field_dir = Path(args.field_dir)
    field_names = parse_field_names(args.field_names)
    case_output_dir = Path(args.case_output_dir) if args.case_output_dir else None
    fields, params, targets, etas, case_ids = [], [], [], [], []
    nu0, f0 = nearest_baseline(labels)

    for _, row in labels.iterrows():
        case_id = int(row["case_id"])
        field_path = field_dir / f"case_{case_id}_full.npz"
        if not field_path.exists():
            continue

        field = load_field(field_path, field_names)
        param = row[PARAM_COLS].to_numpy(dtype=np.float32)
        target = row[TARGET_COLS].to_numpy(dtype=np.float32)
        eta = float(eta_value(np.array(target[0]), np.array(target[1]), nu0, f0))

        fields.append(field)
        params.append(param)
        targets.append(target)
        etas.append(eta)
        case_ids.append(case_id)

        if case_output_dir is not None:
            export_case_npz(case_output_dir, case_id, param, field, field_names, float(target[0]), float(target[1]), eta)

        if args.limit and len(case_ids) >= args.limit:
            break

    if not case_ids:
        raise FileNotFoundError(f"没有找到可用全场数据: {field_dir}")

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    field_array = np.stack(fields).astype(np.float32)
    params_array = np.stack(params).astype(np.float32)
    target_array = np.stack(targets).astype(np.float32)
    eta_array = np.asarray(etas, dtype=np.float32)[:, None]
    np.savez_compressed(
        out,
        case_id=np.asarray(case_ids, dtype=np.int64),
        params=params_array,
        fields=field_array,
        targets=target_array,
        eta=eta_array,
        param_names=np.asarray(PARAM_COLS),
        field_names=np.asarray(field_names),
        target_names=np.asarray(["Nu", "f"]),
        nu0=np.float32(nu0),
        f0=np.float32(f0),
    )
    summary = {
        "dataset": str(out),
        "sample_count": len(case_ids),
        "field_shape": list(field_array.shape),
        "field_names": field_names,
        "case_id_min": int(min(case_ids)),
        "case_id_max": int(max(case_ids)),
        "Nu0": nu0,
        "f0": f0,
        "case_npz_dir": str(case_output_dir) if case_output_dir is not None else "",
        "case_npz_format": f"params, {', '.join(field_names)}, Nu, f, eta",
    }
    (out.parent / "dataset_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
