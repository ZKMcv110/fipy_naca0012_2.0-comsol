#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""从 COMSOL .mph 文件导出全场数据（x, y, u, v, p, T）。

对每个 case 在流道区域内生成 80×50 = 4000 点规则网格，
用 CutPoint2D + EvalPoint 分别求值 u, v, p, T 四个场变量，
用翼型多边形射线法判定空气域/固体域。

输出：field_data/case_{id}_full.npz
  - x, y:   (N,) 物理坐标 [m]
  - u, v:   (N,) 速度分量 [m/s]（固体域为 0）
  - p:      (N,) 压力 [Pa]（固体域为 0）
  - T:      (N,) 温度 [K]
  - domain: (N,) 域标记（0=空气, 1=固体）
  - T_wing: 标量，翼型平均温度 [K]

运行环境：venv Python（myenvs_fipynaca2.0，需 mph + jpype）
预计耗时：4-6h（1000 个 case，每个 case 4 次 EvalPoint 求值）
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
import traceback
from pathlib import Path

import numpy as np

# ──────────────────── 路径 ────────────────────

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
PARAM_DIR = PROJECT_ROOT / "七参数_几何掩码代理优化"

FIELD_DATA_DIR = ROOT / "field_data"
ACTIVE_FIELD_DATA_DIR = FIELD_DATA_DIR

# ──────────────────── 导入共用工具 ────────────────────

sys.path.insert(0, str(ROOT))
from common_pde import (
    CHORD, T_AMB, GRID_NX, GRID_NY, make_grid,
)

sys.path.insert(0, str(PARAM_DIR))
from common import naca_airfoil_points

# ──────────────────── 几何函数 ────────────────────


def _make_airfoil_polygons(params: dict) -> list[np.ndarray]:
    """生成 3×8 翼型阵列多边形，坐标与 COMSOL 几何一致。"""
    base = naca_airfoil_points(params, chord=CHORD)
    col_pitch = (1.0 + params["Ts"]) * CHORD
    y_factors = [-1, 0, 1]
    polygons = []
    for j, yf in enumerate(y_factors):
        stagger = (params["Tad"] * CHORD) if j % 2 != 0 else 0.0
        for i in range(8):
            x_shift = i * col_pitch + stagger
            y_shift = yf * params["Tt"] * CHORD
            shifted = base + np.array([x_shift, y_shift])
            center = (x_shift + 0.5 * CHORD, y_shift)
            angle = math.radians(params["theta"])
            cos_a, sin_a = math.cos(angle), math.sin(angle)
            delta = shifted - np.array(center)
            rotated = delta @ np.array([[cos_a, -sin_a],
                                        [sin_a, cos_a]]) + np.array(center)
            polygons.append(rotated)
    return polygons


def mark_solid_domain(x_flat: np.ndarray, y_flat: np.ndarray,
                      polygons: list[np.ndarray]) -> np.ndarray:
    """标记每个网格点的域归属（0=空气, 1=固体）。"""
    n_points = len(x_flat)
    domain = np.zeros(n_points, dtype=np.int32)
    bboxes = []
    for poly in polygons:
        x_min, y_min = poly.min(axis=0)
        x_max, y_max = poly.max(axis=0)
        bboxes.append((x_min, x_max, y_min, y_max))

    for idx in range(n_points):
        px, py = float(x_flat[idx]), float(y_flat[idx])
        for poly, (x_min, x_max, y_min, y_max) in zip(polygons, bboxes):
            if px < x_min or px > x_max or py < y_min or py > y_max:
                continue
            if _point_in_polygon(px, py, poly):
                domain[idx] = 1
                break
    return domain


def _point_in_polygon(x: float, y: float, polygon: np.ndarray) -> bool:
    """射线法判定点是否在多边形内部。"""
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


# ──────────────────── COMSOL 求值 ────────────────────

# 需要提取的场变量（u, v, p 仅流体域有定义，T 全域有定义）
FIELD_EXPRS = ["u", "v", "p", "T"]


def evaluate_fields(cp_node, num_node, JDoubleArray,
                    x_flat: np.ndarray, y_flat: np.ndarray,
                    ) -> dict[str, np.ndarray]:
    """用 EvalPoint 分别求值 u, v, p, T。

    所有 EvalPoint 共享同一个 CutPoint2D 数据集。
    """
    x_ja = JDoubleArray(x_flat.astype(np.float64).tolist())
    y_ja = JDoubleArray(y_flat.astype(np.float64).tolist())
    cp_node.set("pointx", x_ja)
    cp_node.set("pointy", y_ja)

    fields = {}
    eval_names = []
    for expr in FIELD_EXPRS:
        eval_name = f"pde_eval_{expr}"
        ev = num_node.create(eval_name, "EvalPoint")
        ev.set("data", cp_node.tag())
        ev.set("expr", expr)
        result = ev.computeResult()
        vals = np.array(list(result[0][0]), dtype=np.float32)
        # NaN → 0（固体域点 u/v/p 为 NaN）
        vals = np.nan_to_num(vals, nan=0.0).astype(np.float32)
        fields[expr] = vals
        eval_names.append(eval_name)

    # 清理 EvalPoint 节点
    for name in eval_names:
        try:
            num_node.remove(name)
        except Exception:
            pass

    return fields


# ──────────────────── 核心处理 ────────────────────


def process_one_case(mj, JDoubleArray,
                     case_id: int, params: dict, mph_path: Path,
                     nx: int, ny: int) -> bool:
    """处理单个 case：提取全场数据 + 标记域 + 保存。"""
    x_flat, y_flat = make_grid(
        params["Ta"], params["Tb"], params["Ts"],
        params["Tt"], params["Tad"], params["theta"],
        nx=nx,
        ny=ny,
    )
    n_points = len(x_flat)

    # 获取已有 Solution 数据集
    dset_list = mj.result().dataset()
    existing_tags = list(dset_list.tags())
    sol_tag = existing_tags[0] if existing_tags else None
    if sol_tag is None:
        raise RuntimeError("模型中无数据集")

    # 创建 CutPoint2D
    cp_name = "pde_full_cp"
    cp_node = dset_list.create(cp_name, "CutPoint2D")
    cp_node.set("data", sol_tag)

    num_node = mj.result().numerical()

    # 求值 u, v, p, T
    fields = evaluate_fields(cp_node, num_node, JDoubleArray, x_flat, y_flat)

    # 验证长度
    for name, vals in fields.items():
        if len(vals) != n_points:
            print(f"  [WARN] case_{case_id}: {name} 长度 {len(vals)} != {n_points}")
            fields[name] = np.full(n_points, 0.0, dtype=np.float32)

    # 域判定
    polygons = _make_airfoil_polygons(params)
    domain = mark_solid_domain(x_flat, y_flat, polygons)

    # T_wing
    result_json = mph_path.parent.parent / "result.json"
    data = json.loads(result_json.read_text(encoding="utf-8"))
    delta_T = float(data.get("delta_T", float("nan")))
    T_wing = T_AMB + delta_T

    # 清理 CutPoint2D
    try:
        dset_list.remove(cp_name)
    except Exception:
        pass

    # 保存
    output_path = ACTIVE_FIELD_DATA_DIR / f"case_{case_id}_full.npz"
    np.savez(
        output_path,
        x=x_flat.astype(np.float32),
        y=y_flat.astype(np.float32),
        u=fields["u"],
        v=fields["v"],
        p=fields["p"],
        T=fields["T"],
        domain=domain,
        T_wing=np.float32(T_wing),
    )
    return True


def verify_data(x, y, u, v, p, T, domain, case_id):
    """验证导出数据的合理性。"""
    n = len(T)
    n_air = (domain == 0).sum()
    n_solid = (domain == 1).sum()
    T_valid = T[np.isfinite(T)]
    if len(T_valid) == 0:
        print(f"  [WARN] case_{case_id}: 无有效温度")
        return
    u_air = u[domain == 0]
    print(f"  点: {n} (空气={n_air}, 固体={n_solid}), "
          f"T=[{T_valid.min():.1f}, {T_valid.max():.1f}] K, "
          f"u_air=[{u_air.min():.2f}, {u_air.max():.2f}] m/s")


# ──────────────────── 入口 ────────────────────


def collect_cases() -> list[tuple[int, Path, Path]]:
    """扫描所有 COMSOL 结果目录。"""
    cases = []
    for comsol_dir in [
        PARAM_DIR / "comsol_results_theta500_v2",
        PARAM_DIR / "comsol_results_1000_extra",
    ]:
        if not comsol_dir.exists():
            continue
        for case_dir in sorted(comsol_dir.iterdir()):
            if not case_dir.is_dir():
                continue
            mph_path = case_dir / "cfd_solution" / "model.mph"
            result_json = case_dir / "result.json"
            if mph_path.exists() and result_json.exists():
                case_id = int(case_dir.name.split("_")[1])
                cases.append((case_id, mph_path, result_json))
    return cases


def main():
    global ACTIVE_FIELD_DATA_DIR
    parser = argparse.ArgumentParser(description="从 COMSOL .mph 导出全场数据 (u,v,p,T)")
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--end", type=int, default=None)
    parser.add_argument("--no-skip", action="store_true")
    parser.add_argument("--nx", type=int, default=GRID_NX, help="x 方向规则采样点数")
    parser.add_argument("--ny", type=int, default=GRID_NY, help="y 方向规则采样点数")
    parser.add_argument("--output-dir", default=str(FIELD_DATA_DIR), help="全场 npz 输出目录")
    args = parser.parse_args()
    ACTIVE_FIELD_DATA_DIR = Path(args.output_dir)

    all_cases = collect_cases()
    print(f"共发现 {len(all_cases)} 个有效 case")

    end_idx = args.end if args.end is not None else len(all_cases)
    cases = all_cases[args.start:end_idx]
    print(f"本次处理: [{args.start}, {end_idx})，共 {len(cases)} 个")

    ACTIVE_FIELD_DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"采样网格: nx={args.nx}, ny={args.ny}, 输出目录: {ACTIVE_FIELD_DATA_DIR}")

    import jpype
    import mph

    print("[INFO] 启动 COMSOL 客户端...")
    client = mph.start()
    JDoubleArray = jpype.JArray(jpype.JDouble)

    success_count = 0
    fail_count = 0
    skip_count = 0
    t_start = time.time()

    try:
        for idx, (case_id, mph_path, result_json) in enumerate(cases):
            output_path = ACTIVE_FIELD_DATA_DIR / f"case_{case_id}_full.npz"
            if not args.no_skip and output_path.exists():
                skip_count += 1
                continue

            elapsed = time.time() - t_start
            total_done = success_count + fail_count
            eta_str = ""
            if total_done > 0:
                per_case = elapsed / total_done
                remaining = per_case * (len(cases) - idx)
                eta_str = f", ETA {remaining/60:.0f}min"

            print(f"[{idx+1}/{len(cases)}] case_{case_id} "
                  f"(成功={success_count}, 失败={fail_count}, "
                  f"跳过={skip_count}{eta_str})")

            try:
                params = json.loads(result_json.read_text(encoding="utf-8"))

                model = client.load(str(mph_path))
                mj = model.java

                process_one_case(mj, JDoubleArray, case_id, params, mph_path, args.nx, args.ny)

                data = np.load(output_path)
                verify_data(
                    data["x"], data["y"], data["u"], data["v"],
                    data["p"], data["T"], data["domain"], case_id,
                )

                success_count += 1
                client.remove(model)

            except Exception as e:
                fail_count += 1
                print(f"  [FAIL] case_{case_id}: {e}")
                traceback.print_exc()
                try:
                    client.remove(model)
                except Exception:
                    pass

    except KeyboardInterrupt:
        print("\n[INFO] 用户中断")
    finally:
        print("[INFO] 断开 COMSOL...")
        client.disconnect()

    elapsed_min = (time.time() - t_start) / 60
    print(f"\n导出完成: 成功={success_count}, 失败={fail_count}, "
          f"跳过={skip_count}, 耗时={elapsed_min:.1f}min")


if __name__ == "__main__":
    main()
