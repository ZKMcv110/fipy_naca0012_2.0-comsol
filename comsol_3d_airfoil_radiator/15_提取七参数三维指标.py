#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""提取七参数真实芯片散热器三维验证指标。

对比对象必须来自同一三维建模脚本和同一求解口径。默认保留旧
`pi_cbam_best` 对照，也支持通过命令行传入新的最终候选结构。
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "generated_7param_chip_heat_sink" / "results"
DEFAULT_MODEL_PATHS = {
    "baseline": ROOT / "generated_realistic_heat_sink" / "baseline" / "baseline_realistic_airfoil_heat_sink.mph",
    "pi_cbam_best": ROOT
    / "generated_7param_chip_heat_sink"
    / "pi_cbam_best"
    / "pi_cbam_best_realistic_airfoil_heat_sink.mph",
}


@dataclass(frozen=True)
class ThreeDimensionalResult:
    case: str
    model_path: str
    t_chip_avg_k: float
    t_chip_max_k: float
    t_chip_min_k: float
    t_out_avg_k: float
    p_in_avg_pa: float
    p_out_avg_pa: float
    delta_p_pa: float
    r_th_k_per_w: float
    delta_t_out_k: float
    r_th_ratio: float | None = None
    delta_p_ratio: float | None = None
    eta_3d: float | None = None
    nu_3d: float | None = None
    f_3d: float | None = None
    nu_ratio: float | None = None
    f_ratio: float | None = None
    eta_nu_f_3d: float | None = None


def first_scalar(value: Any) -> float:
    """COMSOL 结果经常是多层 Java 数组，统一取第一个标量。"""
    while hasattr(value, "__len__") and not isinstance(value, (str, bytes)):
        try:
            if len(value) == 0:
                raise ValueError("COMSOL 返回空结果")
            value = value[0]
        except TypeError:
            break
    return float(value)


def safe_evaluate(model: Any, expression: str, default: float) -> float:
    try:
        return first_scalar(model.evaluate(expression))
    except Exception:
        return default


def equivalent_nu_f(model: Any, heat_power: float, t_chip_avg: float, t_in: float, delta_p: float) -> tuple[float, float]:
    """基于三维芯片热阻和通道压降定义等效 Nu/f，便于与二维指标叙述保持一致。"""
    l_channel = safe_evaluate(model, "L_channel", 0.06)
    w_channel = safe_evaluate(model, "W_channel", 0.028)
    h_channel = safe_evaluate(model, "H_channel", 0.016)
    l_chip = safe_evaluate(model, "L_chip", 0.018)
    w_chip = safe_evaluate(model, "W_chip", l_chip)
    u0 = safe_evaluate(model, "U0", 0.5)
    rho_air = 1.2
    k_air = 0.026
    hydraulic_diameter = 2.0 * w_channel * h_channel / max(w_channel + h_channel, 1e-12)
    chip_area = max(l_chip * w_chip, 1e-12)
    h_eq = heat_power / max(chip_area * (t_chip_avg - t_in), 1e-12)
    nu_3d = h_eq * hydraulic_diameter / k_air
    f_3d = delta_p * hydraulic_diameter / max(0.5 * rho_air * u0**2 * l_channel, 1e-12)
    return nu_3d, f_3d


class ComsolEvaluator:
    def __init__(self, java_model: Any) -> None:
        self.result = java_model.result()
        self.index = 0

    def evaluate(self, feature_type: str, selection: str, expression: str) -> float:
        self.index += 1
        tag = f"eval_{self.index}"
        numerical = self.result.numerical().create(tag, feature_type)
        numerical.selection().named(selection)
        numerical.set("expr", expression)
        try:
            return first_scalar(numerical.computeResult())
        finally:
            try:
                self.result.numerical().remove(tag)
            except Exception:
                pass


def evaluate_case(client: Any, case: str, model_path: Path) -> ThreeDimensionalResult:
    if not model_path.exists():
        raise FileNotFoundError(model_path)

    model = client.load(str(model_path.resolve()))
    evaluator = ComsolEvaluator(model.java)
    t_in = first_scalar(model.evaluate("T_in"))
    heat_power = first_scalar(model.evaluate("P0"))

    t_chip_avg = evaluator.evaluate("AvVolume", "sel_chip", "T")
    t_chip_max = evaluator.evaluate("MaxVolume", "sel_chip", "T")
    t_chip_min = evaluator.evaluate("MinVolume", "sel_chip", "T")
    t_out_avg = evaluator.evaluate("AvSurface", "sel_outlet", "T")
    p_in_avg = evaluator.evaluate("AvSurface", "sel_inlet", "p")
    p_out_avg = evaluator.evaluate("AvSurface", "sel_outlet", "p")
    delta_p = abs(p_in_avg - p_out_avg)
    nu_3d, f_3d = equivalent_nu_f(model, heat_power, t_chip_avg, t_in, delta_p)

    return ThreeDimensionalResult(
        case=case,
        model_path=str(model_path.resolve()),
        t_chip_avg_k=t_chip_avg,
        t_chip_max_k=t_chip_max,
        t_chip_min_k=t_chip_min,
        t_out_avg_k=t_out_avg,
        p_in_avg_pa=p_in_avg,
        p_out_avg_pa=p_out_avg,
        delta_p_pa=delta_p,
        r_th_k_per_w=(t_chip_avg - t_in) / heat_power,
        delta_t_out_k=t_out_avg - t_in,
        nu_3d=nu_3d,
        f_3d=f_3d,
    )


def add_ratios(results: list[ThreeDimensionalResult], baseline_case: str = "baseline") -> list[ThreeDimensionalResult]:
    baseline = next(item for item in results if item.case == baseline_case)
    updated: list[ThreeDimensionalResult] = []
    for item in results:
        r_th_ratio = item.r_th_k_per_w / baseline.r_th_k_per_w
        delta_p_ratio = item.delta_p_pa / baseline.delta_p_pa
        eta_3d = (baseline.r_th_k_per_w / item.r_th_k_per_w) / (delta_p_ratio ** (1.0 / 3.0))
        nu_ratio = item.nu_3d / baseline.nu_3d
        f_ratio = item.f_3d / baseline.f_3d
        eta_nu_f_3d = nu_ratio / (f_ratio ** (1.0 / 3.0))
        updated.append(
            ThreeDimensionalResult(
                **{
                    **asdict(item),
                    "r_th_ratio": r_th_ratio,
                    "delta_p_ratio": delta_p_ratio,
                    "eta_3d": eta_3d,
                    "nu_ratio": nu_ratio,
                    "f_ratio": f_ratio,
                    "eta_nu_f_3d": eta_nu_f_3d,
                }
            )
        )
    return updated


def parse_case_specs(specs: list[str], baseline_case: str, baseline_model: Path) -> dict[str, Path]:
    """解析 name=path 形式的候选模型参数，baseline 始终作为对照保留。"""
    paths = {baseline_case: baseline_model}
    if not specs:
        paths["pi_cbam_best"] = DEFAULT_MODEL_PATHS["pi_cbam_best"]
        return paths
    for spec in specs:
        if "=" not in spec:
            raise ValueError(f"--case 必须使用 name=path 格式: {spec}")
        name, raw_path = spec.split("=", 1)
        name = name.strip()
        if not name:
            raise ValueError(f"--case 名称不能为空: {spec}")
        paths[name] = Path(raw_path)
    return paths


def write_outputs(results: list[ThreeDimensionalResult], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = [asdict(item) for item in results]
    (out_dir / "seven_param_3d_summary.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    with (out_dir / "seven_param_3d_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    names = {
        "baseline": "基准结构",
        "pi_cbam_best": "七参数PI-CNN-CBAM候选结构",
        "baseline_1000_best": "1000组baseline最终候选结构",
    }
    lines = [
        "| 结构 | 芯片平均温度/K | 压降/Pa | 等效热阻/(K/W) | Nu3D | f3D | Nu/Nu0 | f/f0 | η3D(Nu/f) |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in results:
        lines.append(
            "| {name} | {tavg:.3f} | {dp:.6f} | {rth:.3f} | {nu:.3f} | {ff:.6f} | {nur:.3f} | {fr:.3f} | {eta:.3f} |".format(
                name=names.get(item.case, item.case),
                tavg=item.t_chip_avg_k,
                dp=item.delta_p_pa,
                rth=item.r_th_k_per_w,
                nu=item.nu_3d,
                ff=item.f_3d,
                nur=item.nu_ratio,
                fr=item.f_ratio,
                eta=item.eta_nu_f_3d,
            )
        )
    (out_dir / "seven_param_3d_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="提取七参数三维验证指标。")
    parser.add_argument("--output-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--baseline-case", default="baseline")
    parser.add_argument("--baseline-model", type=Path, default=DEFAULT_MODEL_PATHS["baseline"])
    parser.add_argument(
        "--case",
        action="append",
        default=[],
        help="候选模型，格式为 name=path。可重复传入；baseline 会自动加入作为对照。",
    )
    args = parser.parse_args()
    model_paths = parse_case_specs(args.case, args.baseline_case, args.baseline_model)

    import mph

    client = mph.start(cores=4)
    try:
        results = [evaluate_case(client, case, path) for case, path in model_paths.items()]
        write_outputs(add_ratios(results, args.baseline_case), args.output_dir)
        print(f"[INFO] 已输出七参数三维指标: {args.output_dir}")
    finally:
        try:
            client.disconnect()
        except Exception:
            pass


if __name__ == "__main__":
    main()
