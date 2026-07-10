#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""根据七参数表生成几何掩码图。

掩码图由参数直接绘制，不调用COMSOL，不包含速度、温度、压力等物理场结果。
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from common import PARAM_COLS, ROOT, ensure_dir, render_fixed_domain_mask, render_mask


def main() -> None:
    parser = argparse.ArgumentParser(description="生成七参数几何掩码图")
    parser.add_argument("--labels", default=str(ROOT / "samples" / "labels_7param_1000.csv"))
    parser.add_argument("--output-dir", default=str(ROOT / "masks_fixed_1000"))
    parser.add_argument("--image-size", type=int, default=128)
    parser.add_argument("--legacy-adaptive", action="store_true", help="use legacy per-sample adaptive outline image")
    parser.add_argument("--limit", type=int, default=0, help="仅生成前N张；0表示全部")
    args = parser.parse_args()

    df = pd.read_csv(args.labels)
    missing = [col for col in ["case_id"] + PARAM_COLS if col not in df.columns]
    if missing:
        raise ValueError(f"标签表缺少必要列: {missing}")

    out_dir = ensure_dir(Path(args.output_dir))
    count = 0
    for _, row in df.iterrows():
        if args.limit and count >= args.limit:
            break
        params = {name: float(row[name]) for name in PARAM_COLS}
        case_id = int(row["case_id"])
        output_path = out_dir / f"case_{case_id}_mask.png"
        if args.legacy_adaptive:
            render_mask(params, output_path, image_size=args.image_size)
        else:
            render_fixed_domain_mask(params, output_path, image_size=args.image_size)
        count += 1

    print(f"[OK] 已生成几何掩码图: {out_dir}")
    print(f"[OK] 数量: {count}")


if __name__ == "__main__":
    main()
