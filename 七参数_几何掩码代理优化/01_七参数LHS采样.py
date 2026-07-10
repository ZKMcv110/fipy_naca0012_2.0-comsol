
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""生成七参数LHS采样表。

输出字段固定为 case_id, Ta, Twa, Tb, Ts, Tt, Tad, theta。
该脚本只生成参数组合，不调用COMSOL。
"""

from __future__ import annotations

import argparse
from pathlib import Path

from common import ROOT, ensure_dir, lhs_sample


def main() -> None:
    parser = argparse.ArgumentParser(description="生成七参数LHS采样表")
    parser.add_argument("--num-samples", type=int, default=50, help="样本数量，例如50、100、300、500")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", default=str(ROOT / "samples" / "samples_7param.csv"))
    args = parser.parse_args()

    if args.num_samples <= 0:
        raise ValueError("--num-samples 必须大于0")

    df = lhs_sample(args.num_samples, seed=args.seed)
    out = Path(args.output)
    ensure_dir(out.parent)
    df.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"[OK] 已生成七参数采样表: {out}")
    print(f"[OK] 样本数量: {len(df)}")


if __name__ == "__main__":
    main()
