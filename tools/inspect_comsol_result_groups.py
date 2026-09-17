#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""列出 COMSOL MPH 模型中的结果图组。

用于确认模型里是否已经存在 COMSOL 求解后自动生成的模板图，
例如“温度和流体流动”“温度”“速度”“压力”等。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def java_tags(container: Any) -> list[str]:
    try:
        return [str(tag) for tag in list(container.tags())]
    except Exception:
        return []


def safe_label(node: Any) -> str:
    try:
        return str(node.label())
    except Exception:
        return ""


def safe_type(node: Any) -> str:
    try:
        return str(node.getType())
    except Exception:
        return ""


def collect_result_groups(model_path: Path) -> dict[str, Any]:
    import mph

    client = mph.start(cores=2)
    try:
        model = client.load(str(model_path.resolve()))
        java_model = model.java
        result = java_model.result()
        groups = []
        for tag in java_tags(result):
            group = java_model.result(tag)
            features = []
            for feature_tag in java_tags(group.feature()):
                feature = group.feature(feature_tag)
                features.append(
                    {
                        "tag": feature_tag,
                        "label": safe_label(feature),
                        "type": safe_type(feature),
                    }
                )
            groups.append(
                {
                    "tag": tag,
                    "label": safe_label(group),
                    "type": safe_type(group),
                    "features": features,
                }
            )
        return {"model": str(model_path.resolve()), "result_groups": groups}
    finally:
        try:
            client.disconnect()
        except Exception:
            pass


def main() -> None:
    parser = argparse.ArgumentParser(description="列出 MPH 模型中的结果图组。")
    parser.add_argument("model", type=Path)
    parser.add_argument("--json", type=Path, default=None, help="可选：保存完整 JSON。")
    args = parser.parse_args()

    payload = collect_result_groups(args.model)
    for group in payload["result_groups"]:
        print(f"{group['tag']}\t{group['type']}\t{group['label']}")
        for feature in group["features"]:
            print(f"  - {feature['tag']}\t{feature['type']}\t{feature['label']}")
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
