#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""从COMSOL结果重建七参数标签表。

两种用法：
1. 初始兼容旧数据：从现有 consol_cfddata/labels.csv 复制六参数结果，并补 theta=0。
2. 正式七参数流程：从本目录 comsol_results/case_x/result.json 重建 labels_7param.csv。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from common import OLD_PARAM_COLS, PARAM_COLS, PROJECT_ROOT, ROOT, TARGET_COLS, ensure_dir


EXTRA_COLS = ["delta_p", "delta_T", "Q_total", "image_complete", "failure_reason"]


def from_existing_labels(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = ["case_id"] + OLD_PARAM_COLS + TARGET_COLS
    missing = [name for name in required if name not in df.columns]
    if missing:
        raise ValueError(f"旧标签缺少列: {missing}")
    out = df.copy()
    out["theta"] = 0.0
    for col in EXTRA_COLS:
        if col not in out.columns:
            out[col] = "" if col == "failure_reason" else None
    return out[["case_id"] + PARAM_COLS + TARGET_COLS + EXTRA_COLS]


def from_result_json(results_dir: Path) -> pd.DataFrame:
    rows = []
    for result_path in sorted(results_dir.glob("case_*/result.json")):
        data = json.loads(result_path.read_text(encoding="utf-8"))
        row = {name: data.get(name) for name in ["case_id"] + PARAM_COLS + TARGET_COLS + EXTRA_COLS}
        if row["case_id"] is None:
            row["case_id"] = int(result_path.parent.name.split("_")[-1])
        rows.append(row)
    if not rows:
        raise FileNotFoundError(f"没有找到 result.json: {results_dir}/case_*/result.json")
    return pd.DataFrame(rows).sort_values("case_id").reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="重建七参数 labels_7param.csv")
    parser.add_argument("--existing-labels", default=str(PROJECT_ROOT / "consol_cfddata" / "labels.csv"))
    parser.add_argument("--results-dir", default=str(ROOT / "comsol_results"))
    parser.add_argument("--mode", choices=["existing", "results"], default="existing")
    parser.add_argument("--output", default=str(ROOT / "samples" / "labels_7param.csv"))
    args = parser.parse_args()

    if args.mode == "existing":
        df = from_existing_labels(Path(args.existing_labels))
    else:
        df = from_result_json(Path(args.results_dir))

    out = Path(args.output)
    ensure_dir(out.parent)
    df.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"[OK] 已生成标签表: {out}")
    print(f"[OK] 行数: {len(df)}")


if __name__ == "__main__":
    main()
