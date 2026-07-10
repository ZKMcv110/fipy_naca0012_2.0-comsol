#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""旧六参数 CNN 模型定义入口。

项目已将模型脚本整理到 `旧六参数流程/模型脚本/` 目录。本文件保留旧入口，避免依赖
`cnnstep1.py` 的旧训练脚本、笔记或外部命令失效。
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


TARGET = Path(__file__).resolve().parent / "旧六参数流程" / "模型脚本" / "CNN_CBAM_GAP_模型定义.py"


def _load_target() -> None:
    spec = importlib.util.spec_from_file_location("_cnn_cbam_gap_model", TARGET)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载模型定义脚本: {TARGET}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name, value in module.__dict__.items():
        if not name.startswith("__"):
            globals()[name] = value


_load_target()
