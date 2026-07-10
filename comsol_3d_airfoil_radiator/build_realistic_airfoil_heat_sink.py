#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""真实感三维翼型柱散热器建模入口。

保留中文主脚本，提供 ASCII 文件名入口，避免 Windows 命令行和外部工具
在中文路径参数上传递不稳定。
"""

from __future__ import annotations

import runpy
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parent
    matches = sorted(root.glob("12_*建模.py"))
    if not matches:
        raise FileNotFoundError("未找到 12_真实感翼型柱散热器建模.py")
    runpy.run_path(str(matches[0]), run_name="__main__")


if __name__ == "__main__":
    main()
