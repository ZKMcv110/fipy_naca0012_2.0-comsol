# -*- coding: utf-8 -*-
"""扫描全项目 metrics/summary JSON，生成 docs/41-指标台账.md 横向对比总表。

用法：
    python 工具脚本/生成指标台账.py
    python 工具脚本/生成指标台账.py --output docs/41-指标台账.md

设计要点：
- 只读取，不修改任何结果文件。
- K 折目录（路径含 fold_XX）自动聚合成 均值±标准差。
- 字段名大小写与命名变体统一归一，避免遗漏。
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SCAN_ROOTS = [
    "七参数_MLP_CNN流场重建",
    "七参数_几何掩码代理优化",
    "七参数_PDE_PINN尝试",
    "comsol_3d_airfoil_radiator",
    "归档/旧六参数模型结果",
]

EXCLUDE_DIRS = {
    "myenvs_fipynaca2.0",
    "第三方工具",
    "CLIProxyAPI",
    "参考文献资料",
    "skills",
    "node_modules",
    "__pycache__",
    ".git",
    ".workbuddy",
}

# 台账关注的核心指标，按显示顺序排列
CORE_FIELDS = ["Nu_R2", "Nu_RMSE", "Nu_MAE", "f_R2", "f_RMSE", "f_MAE", "eta_R2", "T_R2"]

# 字段名归一化：小写去下划线后的别名映射
# 只收录 R²/RMSE/MAE；MSE 与 RMSE 量纲不同，不混入同一列以免误读
FIELD_ALIASES = {
    "nur2": "Nu_R2",
    "nur2score": "Nu_R2",
    "nurmse": "Nu_RMSE",
    "numae": "Nu_MAE",
    "fr2": "f_R2",
    "fr2score": "f_R2",
    "frmse": "f_RMSE",
    "fmae": "f_MAE",
    "etar2": "eta_R2",
    "tr2": "T_R2",
    "ur2": "u_R2",
    "vr2": "v_R2",
    "pr2": "p_R2",
}


def iter_metric_files() -> list[Path]:
    """收集所有指标 JSON，跳过环境与第三方目录。"""
    files: list[Path] = []
    for rel_root in SCAN_ROOTS:
        base = ROOT / rel_root
        if not base.exists():
            continue
        for path in base.rglob("*.json"):
            if any(part in EXCLUDE_DIRS for part in path.parts):
                continue
            name = path.name.lower()
            if "metric" in name or "summary" in name or "结果" in name:
                files.append(path)
    return sorted(files)


def normalize_key(raw_key: str) -> str | None:
    """把各种命名变体统一成台账字段名，无法识别返回 None。"""
    compact = raw_key.lower().replace("_", "").replace(" ", "")
    return FIELD_ALIASES.get(compact)


def load_metrics(path: Path) -> dict[str, float]:
    """读取单个 JSON，抽取台账关注的数值字段。"""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return {}

    if not isinstance(data, dict):
        return {}

    found: dict[str, float] = {}
    for key, value in data.items():
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            continue
        field = normalize_key(key)
        if field and field not in found:
            found[field] = float(value)
    return found


def group_key(path: Path) -> tuple[str, bool]:
    """按「实验目录 + 指标文件名」分组。

    路径含 fold_XX 时去掉该层级，使各折合并为一行（K 折聚合）。
    同一目录下不同名的指标文件保持独立，避免把 MLP 基线与多模态融合
    等不同模型的指标错误地平均成一行。
    """
    try:
        rel = path.relative_to(ROOT)
    except ValueError:
        rel = path

    parts = list(rel.parts[:-1])
    is_kfold = any(p.lower().startswith("fold") for p in parts)
    kept = [p for p in parts if not p.lower().startswith("fold")]
    stem = path.stem
    key = "/".join(kept + [stem]) if kept else stem
    return key, is_kfold


def aggregate(records: list[dict[str, float]]) -> dict[str, str]:
    """单条直接格式化；多条（K 折）输出 均值±标准差。"""
    if not records:
        return {}

    if len(records) == 1:
        return {k: f"{v:.4f}" for k, v in records[0].items()}

    out: dict[str, str] = {}
    for field in CORE_FIELDS:
        values = [r[field] for r in records if field in r]
        if not values:
            continue
        mean = statistics.fmean(values)
        std = statistics.stdev(values) if len(values) > 1 else 0.0
        out[field] = f"{mean:.4f}±{std:.4f}"
    return out


def build_rows() -> list[tuple[str, int, dict[str, str]]]:
    """聚合成台账行：实验目录、样本份数、指标。"""
    grouped: dict[str, list[dict[str, float]]] = defaultdict(list)
    for path in iter_metric_files():
        metrics = load_metrics(path)
        if not metrics:
            continue
        key, _ = group_key(path)
        grouped[key].append(metrics)

    rows = [(key, len(recs), aggregate(recs)) for key, recs in grouped.items()]
    return sorted(rows, key=lambda r: r[0])


def render(rows: list[tuple[str, int, dict[str, str]]], present_fields: list[str]) -> str:
    """渲染 Markdown 表格。"""
    header = ["实验 / 结果目录", "份数"] + present_fields
    lines = [
        "| " + " | ".join(header) + " |",
        "|" + "|".join(["---"] * len(header)) + "|",
    ]
    for key, count, metrics in rows:
        cells = [f"`{key}`", str(count)]
        cells += [metrics.get(f, "—") for f in present_fields]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="生成项目指标台账")
    parser.add_argument("--output", default="docs/41-指标台账.md", help="输出 Markdown 路径")
    args = parser.parse_args()

    rows = build_rows()
    present_fields = [f for f in CORE_FIELDS if any(f in m for _, _, m in rows)]

    table = render(rows, present_fields)
    doc = f"""# 指标台账

全项目实验指标的横向对比总表，由 `工具脚本/生成指标台账.py` 自动生成，请勿手工编辑。
重新生成：

```powershell
python 工具脚本/生成指标台账.py
```

- `份数` 大于 1 表示 K 折或多次运行，数值格式为 `均值±标准差`。
- `—` 表示该实验未产出此指标。
- 路径含 `smoke` 的行为冒烟测试，只跑少量 epoch 验证流程通断，**指标不代表模型性能**，对比时请跳过。
- 本表只做汇总，**不判断优劣**；结论以各实验报告与 [`决策记录.md`](决策记录.md) 为准。

## 总表

{table}

## 说明

- 扫描范围：{'、'.join(f'`{r}`' for r in SCAN_ROOTS)}
- 排除目录：环境与第三方依赖（{'、'.join(sorted(EXCLUDE_DIRS))}）
- 已收录实验目录数：{len(rows)}
"""

    out_path = ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(doc, encoding="utf-8")
    print(f"已生成 {out_path}（{len(rows)} 个实验目录）")


if __name__ == "__main__":
    main()
