#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""七参数参数-几何掩码代理优化公共工具。

本目录是新增流程，不能反向依赖或修改旧的六参数脚本。公共模块集中维护
参数顺序、取值范围、翼型坐标和几何掩码生成逻辑，避免多个脚本各写一套。
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent

PARAM_COLS = ["Ta", "Twa", "Tb", "Ts", "Tt", "Tad", "theta"]
OLD_PARAM_COLS = ["Ta", "Twa", "Tb", "Ts", "Tt", "Tad"]
TARGET_COLS = ["Nu", "f"]

PARAM_RANGES = {
    "Ta": (0.00, 0.05),
    "Twa": (0.20, 0.60),
    "Tb": (0.08, 0.15),
    "Ts": (0.50, 1.50),
    "Tt": (0.50, 1.20),
    "Tad": (0.00, 1.00),
    "theta": (-10.0, 10.0),
}

DEFAULT_BASELINE = {
    "Ta": 0.0,
    "Twa": 0.40,
    "Tb": 0.12,
    "Ts": 1.10,
    "Tt": 0.85,
    "Tad": 0.0,
    "theta": 0.0,
}

# Fixed physical domain for strict geometry masks.
# The bounds cover the whole 3x8 array under the current parameter ranges.
# Unlike render_mask(), every sample is projected into this same coordinate box.
FIXED_MASK_BOUNDS = {
    "xmin": -11.0,
    "xmax": 11.0,
    "ymin": -2.2,
    "ymax": 2.2,
}


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {path}")
    return pd.read_csv(path)


def write_json(path: Path, data: dict) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_param_row(row: dict | pd.Series) -> dict[str, float]:
    values = {}
    for name in PARAM_COLS:
        if name not in row:
            raise KeyError(f"缺少参数列: {name}")
        value = float(row[name])
        low, high = PARAM_RANGES[name]
        if not low <= value <= high:
            raise ValueError(f"{name}={value} 超出范围 [{low}, {high}]")
        values[name] = value
    return values


def naca_airfoil_points(params: dict[str, float], chord: float = 1.0, point_count: int = 101) -> np.ndarray:
    """生成闭合NACA四位数翼型点，参数定义与二维COMSOL脚本一致。"""
    ta = float(params["Ta"])
    twa = float(params["Twa"])
    tb = float(params["Tb"])

    def camber(s: float) -> tuple[float, float]:
        if abs(ta) < 1e-12:
            return 0.0, 0.0
        if s < twa:
            return ta / twa**2 * (2 * twa * s - s**2), 2 * ta / twa**2 * (twa - s)
        return (
            ta / (1 - twa) ** 2 * ((1 - 2 * twa) + 2 * twa * s - s**2),
            2 * ta / (1 - twa) ** 2 * (twa - s),
        )

    upper: list[tuple[float, float]] = []
    lower: list[tuple[float, float]] = []
    for index in range(point_count):
        s = index / (point_count - 1)
        yt = tb / 0.2 * (
            0.2969 * math.sqrt(max(s, 0.0))
            - 0.1260 * s
            - 0.3516 * s**2
            + 0.2843 * s**3
            - 0.1036 * s**4
        )
        yc, dyc = camber(s)
        theta = math.atan(dyc)
        upper.append(((s - yt * math.sin(theta)) * chord, (yc + yt * math.cos(theta)) * chord))
        lower.append(((s + yt * math.sin(theta)) * chord, (yc - yt * math.cos(theta)) * chord))
    return np.asarray(upper + list(reversed(lower[1:-1])), dtype=np.float64)


def rotate_points(points: np.ndarray, theta_deg: float, center: tuple[float, float]) -> np.ndarray:
    """绕自身中心旋转翼型点。theta为度，正值表示逆时针旋转。"""
    angle = math.radians(theta_deg)
    c, s = math.cos(angle), math.sin(angle)
    shifted = points - np.asarray(center, dtype=np.float64)
    matrix = np.asarray([[c, -s], [s, c]], dtype=np.float64)
    return shifted @ matrix.T + np.asarray(center, dtype=np.float64)


def array_polygons(params: dict[str, float], chord: float = 1.0) -> list[np.ndarray]:
    """生成3x8翼型阵列多边形，坐标为无量纲几何坐标。"""
    params = validate_param_row(params)
    base = naca_airfoil_points(params, chord=chord)
    col_pitch = (1.0 + params["Ts"]) * chord
    row_pitch = params["Tt"] * chord
    array_len = 7 * col_pitch + params["Tad"] * chord + chord
    x_origin = -array_len / 2
    y_offsets = [-row_pitch, 0.0, row_pitch]

    polygons = []
    for row_idx, y0 in enumerate(y_offsets):
        for col_idx in range(8):
            stagger = params["Tad"] * chord if row_idx % 2 == 1 else 0.0
            x0 = x_origin + col_idx * col_pitch + stagger
            shifted = base + np.asarray([x0, y0])
            center = (x0 + 0.5 * chord, y0)
            polygons.append(rotate_points(shifted, params["theta"], center))
    return polygons


def render_mask(
    params: dict[str, float],
    output_path: Path | None = None,
    image_size: int = 128,
    padding_ratio: float = 0.10,
) -> Image.Image:
    """由七参数直接渲染几何掩码图。

    白色为空气域，黑色为翼型管固体域。该图只表达几何，不包含任何CFD云图信息。
    """
    polygons = array_polygons(params, chord=1.0)
    all_points = np.vstack(polygons)
    min_xy = all_points.min(axis=0)
    max_xy = all_points.max(axis=0)
    span = max_xy - min_xy
    span[span == 0] = 1.0
    pad = span.max() * padding_ratio
    min_xy -= pad
    max_xy += pad
    span = max_xy - min_xy

    canvas = Image.new("L", (image_size, image_size), color=255)
    draw = ImageDraw.Draw(canvas)
    for poly in polygons:
        x = (poly[:, 0] - min_xy[0]) / span[0] * (image_size - 1)
        y = (poly[:, 1] - min_xy[1]) / span[1] * (image_size - 1)
        # 图像坐标y轴向下，几何坐标y轴向上。
        points = [(float(px), float(image_size - 1 - py)) for px, py in zip(x, y)]
        draw.polygon(points, fill=0)

    if output_path is not None:
        ensure_dir(output_path.parent)
        canvas.save(output_path)
    return canvas


def render_fixed_domain_mask(
    params: dict[str, float],
    output_path: Path | None = None,
    image_size: int = 128,
    bounds: dict[str, float] | None = None,
) -> Image.Image:
    """Render a strict binary geometry mask on a shared physical coordinate domain.

    Pixel value convention in the saved PNG is identical to render_mask():
    white = fluid region, black = solid airfoil region. During training the
    dataset converts it to solid=1 and fluid=0.
    """
    domain = FIXED_MASK_BOUNDS if bounds is None else bounds
    xmin = float(domain["xmin"])
    xmax = float(domain["xmax"])
    ymin = float(domain["ymin"])
    ymax = float(domain["ymax"])
    if not (xmin < xmax and ymin < ymax):
        raise ValueError(f"invalid fixed mask bounds: {domain}")

    canvas = Image.new("L", (image_size, image_size), color=255)
    draw = ImageDraw.Draw(canvas)
    x_span = xmax - xmin
    y_span = ymax - ymin

    for poly in array_polygons(params, chord=1.0):
        x = (poly[:, 0] - xmin) / x_span * (image_size - 1)
        y = (poly[:, 1] - ymin) / y_span * (image_size - 1)
        points = [(float(px), float(image_size - 1 - py)) for px, py in zip(x, y)]
        draw.polygon(points, fill=0)

    if output_path is not None:
        ensure_dir(output_path.parent)
        canvas.save(output_path)
    return canvas


def lhs_sample(count: int, seed: int = 42) -> pd.DataFrame:
    """生成七参数LHS样本，不依赖scipy。"""
    rng = np.random.default_rng(seed)
    data = {}
    for name in PARAM_COLS:
        low, high = PARAM_RANGES[name]
        bins = (np.arange(count) + rng.random(count)) / count
        rng.shuffle(bins)
        data[name] = low + bins * (high - low)
    df = pd.DataFrame(data)
    df.insert(0, "case_id", np.arange(1, count + 1, dtype=int))
    return df


def eta_value(nu: float, f_value: float, nu0: float = 1.0, f0: float = 1.0) -> float:
    return (float(nu) / max(float(nu0), 1e-12)) / ((float(f_value) / max(float(f0), 1e-12)) ** (1.0 / 3.0))


def baseline_from_labels(labels: pd.DataFrame) -> tuple[float, float]:
    """从现有标签中找最接近默认基准的Nu0/f0。找不到时退化为第一行。"""
    df = labels.copy()
    for name in OLD_PARAM_COLS:
        df[f"dist_{name}"] = (df[name].astype(float) - DEFAULT_BASELINE[name]) ** 2
    dist_cols = [f"dist_{name}" for name in OLD_PARAM_COLS]
    idx = df[dist_cols].sum(axis=1).idxmin()
    return float(df.loc[idx, "Nu"]), float(df.loc[idx, "f"])


def normalize(values: np.ndarray, mean: Iterable[float], std: Iterable[float]) -> np.ndarray:
    return (values - np.asarray(mean, dtype=np.float32)) / (np.asarray(std, dtype=np.float32) + 1e-8)


def denormalize(values: np.ndarray, mean: Iterable[float], std: Iterable[float]) -> np.ndarray:
    return values * (np.asarray(std, dtype=np.float32) + 1e-8) + np.asarray(mean, dtype=np.float32)
