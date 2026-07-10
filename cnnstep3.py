#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""旧六参数 CNN 预测入口。

实际预测脚本已整理为 `旧六参数流程/模型脚本/CNN_CBAM_预测.py`。保留本文件是为了兼容
旧命令：`python cnnstep3.py --case-id 1`。
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path


TARGET = Path(__file__).resolve().parent / "旧六参数流程" / "模型脚本" / "CNN_CBAM_预测.py"


if __name__ == "__main__":
    sys.path.insert(0, str(TARGET.parent))
    runpy.run_path(str(TARGET), run_name="__main__")
