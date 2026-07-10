from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(r"F:\pyProject\fipy_naca0012_2.0")
THESIS = Path(r"D:\Desktop\大论文初稿\完整论文初稿.md")
OUT = Path(r"D:\Desktop\大论文初稿\论文图表补全")
FIG_DIR = OUT / "figures"
TAB_DIR = OUT / "tables"
SRC_DIR = OUT / "source_index"
SCR_DIR = OUT / "scripts"
REP_DIR = OUT / "reports"


plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def md_table(headers: list[str], rows: list[list[object]]) -> str:
    out = ["| " + " | ".join(headers) + " |"]
    out.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for row in rows:
        out.append("| " + " | ".join("" if v is None else str(v) for v in row) + " |")
    return "\n".join(out) + "\n"


def write_md_table(path: Path, title: str, headers: list[str], rows: list[list[object]], source: str) -> None:
    text = f"# {title}\n\n数据来源：`{source}`\n\n" + md_table(headers, rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def copy_asset(src: Path, dst_name: str) -> tuple[str, str]:
    if not src.exists():
        return "缺失", ""
    dst = FIG_DIR / dst_name
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return "已完成", str(dst)


def save_line_plot(rows: list[dict[str, str]], x_col: str, y_cols: list[str], labels: list[str], title: str, y_label: str, out: Path) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7.2, 4.2), dpi=180)
    x = [float(r[x_col]) for r in rows if r.get(x_col)]
    for col, label in zip(y_cols, labels):
        y = [float(r[col]) for r in rows if r.get(x_col) and r.get(col)]
        ax.plot(x[: len(y)], y, linewidth=1.8, label=label)
    ax.set_title(title)
    ax.set_xlabel(x_col)
    ax.set_ylabel(y_label)
    ax.grid(True, alpha=0.25)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)
    return out


def save_3d_metrics_plot(rows: list[dict[str, str]], out: Path) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    labels = [r["case"] for r in rows]
    metrics = [("t_chip_avg_k", "Tavg/K"), ("t_chip_max_k", "Tmax/K"), ("delta_p_pa", "压降/Pa"), ("eta_3d", "eta_3d")]
    fig, axes = plt.subplots(2, 2, figsize=(8.0, 5.6), dpi=180)
    for ax, (key, title) in zip(axes.ravel(), metrics):
        values = [float(r[key]) for r in rows]
        ax.bar(labels, values, color=["#4C78A8", "#F58518"][: len(values)])
        ax.set_title(title)
        ax.tick_params(axis="x", rotation=15)
        ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)
    return out


def extract_markdown_table(text: str, table_id: str) -> tuple[list[str], list[list[str]]] | None:
    marker = re.search(rf"^\*\*{re.escape(table_id)}\s+.+?\*\*\s*$", text, re.M)
    if not marker:
        return None
    tail = text[marker.end():]
    table_lines = []
    started = False
    for line in tail.splitlines():
        stripped = line.strip()
        if stripped.startswith("|"):
            started = True
            table_lines.append(stripped)
        elif started:
            break
        elif stripped:
            continue
    if len(table_lines) < 3:
        return None
    headers = [c.strip() for c in table_lines[0].strip("|").split("|")]
    rows = []
    for line in table_lines[2:]:
        row = [c.strip() for c in line.strip("|").split("|")]
        if len(row) == len(headers):
            rows.append(row)
    if not rows:
        return None
    blank_like = {"", "-", "待补充", "TODO", "TBD"}
    if any(any(cell in blank_like for cell in row) for row in rows):
        return None
    return headers, rows


def extract_items(text: str) -> list[dict[str, str]]:
    items: dict[str, dict[str, str]] = {}
    for m in re.finditer(r"^\*\*((图|表)(\d+)-(\d+)\s+(.+?))\*\*", text, re.M):
        full, kind, chap, no, title = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
        item_id = f"{kind}{chap}-{no}"
        items.setdefault(
            item_id,
            {"编号": item_id, "类型": "图" if kind == "图" else "表", "标题": title.strip(), "章节": f"第{chap}章", "原占位文本": full},
        )
    for m in re.finditer(r"^(图|表)(\d+)-(\d+)\s+(.+)$", text, re.M):
        kind, chap, no, title = m.group(1), m.group(2), m.group(3), m.group(4)
        item_id = f"{kind}{chap}-{no}"
        items.setdefault(
            item_id,
            {"编号": item_id, "类型": "图" if kind == "图" else "表", "标题": title.strip(), "章节": f"第{chap}章", "原占位文本": f"{kind}{chap}-{no} {title.strip()}"},
        )
    return sorted(items.values(), key=lambda x: (x["类型"], int(x["编号"][1:].split("-")[0]), int(x["编号"].split("-")[1])))


def main() -> None:
    for d in (FIG_DIR, TAB_DIR, SRC_DIR, SCR_DIR, REP_DIR):
        d.mkdir(parents=True, exist_ok=True)

    thesis_hash = sha256(THESIS)
    text = THESIS.read_text(encoding="utf-8")
    items = extract_items(text)

    metrics = read_json(ROOT / "七参数_MLP_CNN流场重建/results/unet_pUt_320x96_full_e50/metrics.json")
    kfold = read_json(ROOT / "七参数_MLP_CNN流场重建/results/pvt_unet_kfold_3_e20/kfold_summary.json")
    ablation = read_json(ROOT / "七参数_MLP_CNN流场重建/results/pvt_ablation/ablation_summary.json")
    best = read_json(ROOT / "七参数_MLP_CNN流场重建/optimization_results/mlp_cnn_de_multiloss_e10/best_params.json")
    validation = read_json(ROOT / "七参数_MLP_CNN流场重建/validation_results/mlp_cnn_de_multiloss_e10/final_validation_report.json")
    sensitivity = read_json(ROOT / "七参数_MLP_CNN流场重建/analysis_results/sensitivity/sensitivity_summary.json")
    grid_rows = read_csv(ROOT / "七参数_MLP_CNN流场重建/analysis_results/grid_independence/grid_independence_summary.csv")
    summary_3d = read_csv(ROOT / "comsol_3d_airfoil_radiator/generated_chip_airfoil_heat_sink/results/seven_param_3d_summary.csv")
    baseline_3d = read_json(ROOT / "comsol_3d_airfoil_radiator/generated_chip_airfoil_heat_sink/chip_baseline_reference/chip_baseline_reference_realistic_build_notes.json")["params"]
    optimized_3d = read_json(ROOT / "comsol_3d_airfoil_radiator/generated_chip_airfoil_heat_sink/chip_mlp_cnn_de_multiloss_e10/chip_mlp_cnn_de_multiloss_e10_realistic_build_notes.json")["params"]
    train_history = read_csv(ROOT / "七参数_MLP_CNN流场重建/results/unet_pUt_320x96_full_e50/train_history.csv")
    de_history = read_csv(ROOT / "七参数_MLP_CNN流场重建/optimization_results/mlp_cnn_de_multiloss_e10/de_history.csv")

    generated_training = save_line_plot(
        train_history,
        "epoch",
        ["train_loss", "val_loss"],
        ["训练损失", "验证损失"],
        "MLP-CNN 训练与验证损失",
        "loss",
        FIG_DIR / "图4-2_train_val_loss.png",
    )
    generated_de = save_line_plot(
        de_history,
        "generation",
        ["best_eta"],
        ["最优 eta"],
        "差分进化优化收敛曲线",
        "eta",
        FIG_DIR / "图4-11_de_convergence.png",
    )
    generated_3d_metrics = save_3d_metrics_plot(summary_3d, FIG_DIR / "图5-8_3d_metrics.png")

    figure_sources = {
        "图1-1": ROOT / "大论文初稿/figures/fig1_mlp_cnn_technical_route.svg",
        "图1-2": ROOT / "大论文初稿/figures/fig1_2_technical_route.svg",
        "图2-1": ROOT / "大论文初稿/figures/fig2_1_heat_transfer_path.svg",
        "图2-2": ROOT / "大论文初稿/figures/fig2_2_tube_wake_comparison.svg",
        "图2-3": ROOT / "大论文初稿/figures/fig2_3_parameter_definition.svg",
        "图2-4": ROOT / "大论文初稿/figures/fig2_4_method_framework.svg",
        "图2-5": ROOT / "大论文初稿/figures/fig4_1_7param_picnn_cbam_architecture.svg",
        "图2-6": ROOT / "大论文初稿/figures/fig4_7_de_convergence_schematic.svg",
        "图3-1": ROOT / "大论文初稿/figures/fig3_1_2d_domain.svg",
        "图3-2": ROOT / "大论文初稿/figures/fig3_3_mesh_comsol.png",
        "图3-3": ROOT / "大论文初稿/figures/fig3_7_velocity_field.png",
        "图3-4": ROOT / "大论文初稿/figures/fig3_9_pressure_field.png",
        "图3-5": ROOT / "大论文初稿/figures/fig3_8_temperature_field.png",
        "图3-6": ROOT / "大论文初稿/figures/fig3_6_multimodal_dataset.svg",
        "图3-7": ROOT / "大论文初稿/figures/fig3_7_velocity_field.png",
        "图3-8": ROOT / "大论文初稿/figures/fig3_9_pressure_field.png",
        "图3-9": ROOT / "大论文初稿/figures/fig3_8_temperature_field.png",
        "图3-10": ROOT / "七参数_MLP_CNN流场重建/analysis_results/sensitivity/sensitivity_bar_Nu_f.png",
        "图3-11": ROOT / "七参数_MLP_CNN流场重建/analysis_results/sensitivity/sensitivity_bar_Nu_f.png",
        "图3-12": ROOT / "七参数_MLP_CNN流场重建/analysis_results/sensitivity/sensitivity_bar_eta.png",
        "图3-13": ROOT / "七参数_MLP_CNN流场重建/analysis_results/sensitivity/sensitivity_bar_eta.png",
        "图3-14": ROOT / "七参数_MLP_CNN流场重建/analysis_results/sensitivity/local_perturbation_eta.png",
        "图4-1": ROOT / "大论文初稿/figures/fig2_mlp_cnn_architecture.svg",
        "图4-2": generated_training,
        "图4-3": ROOT / "七参数_MLP_CNN流场重建/results/unet_pUt_320x96_full_e50/prediction_scatter.png",
        "图4-4": ROOT / "七参数_MLP_CNN流场重建/results/unet_pUt_320x96_full_e50/case_20040_field_compare.png",
        "图4-5": ROOT / "七参数_MLP_CNN流场重建/results/unet_pUt_320x96_full_e50/case_20189_field_compare.png",
        "图4-6": ROOT / "七参数_MLP_CNN流场重建/results/unet_pUt_320x96_full_e50/case_20340_field_compare.png",
        "图4-7": ROOT / "大论文初稿/figures/fig4_7_de_convergence_schematic.svg",
        "图4-8": ROOT / "七参数_MLP_CNN流场重建/validation_results/mlp_cnn_de_multiloss_e10/comsol/case_1/cfd_solution/velocity_magnitude.png",
        "图4-9": ROOT / "七参数_MLP_CNN流场重建/validation_results/mlp_cnn_de_multiloss_e10/comsol/case_1/cfd_solution/pressure.png",
        "图4-10": ROOT / "七参数_MLP_CNN流场重建/validation_results/mlp_cnn_de_multiloss_e10/comsol/case_1/cfd_solution/temperature.png",
        "图4-11": generated_de,
        "图4-12": ROOT / "七参数_MLP_CNN流场重建/validation_results/mlp_cnn_de_multiloss_e10/comsol/case_1/cfd_solution/velocity_magnitude.png",
        "图4-13": ROOT / "七参数_MLP_CNN流场重建/validation_results/mlp_cnn_de_multiloss_e10/comsol/case_1/cfd_solution/pressure.png",
        "图4-14": ROOT / "七参数_MLP_CNN流场重建/validation_results/mlp_cnn_de_multiloss_e10/comsol/case_1/cfd_solution/temperature.png",
        "图5-1": ROOT / "大论文初稿/figures/fig5_2_3d_model_schematic.png",
        "图5-2": ROOT / "comsol_3d_airfoil_radiator/generated_chip_airfoil_heat_sink/chip_mlp_cnn_de_multiloss_e10/exports/chip_mlp_cnn_de_multiloss_e10_mesh.png",
        "图5-3": ROOT / "comsol_3d_airfoil_radiator/generated_chip_airfoil_heat_sink/chip_mlp_cnn_de_multiloss_e10/exports/chip_mlp_cnn_de_multiloss_e10_temperature.png",
        "图5-4": ROOT / "comsol_3d_airfoil_radiator/generated_chip_airfoil_heat_sink/chip_mlp_cnn_de_multiloss_e10/exports/chip_mlp_cnn_de_multiloss_e10_velocity.png",
        "图5-5": ROOT / "comsol_3d_airfoil_radiator/generated_chip_airfoil_heat_sink/chip_mlp_cnn_de_multiloss_e10/exports/chip_mlp_cnn_de_multiloss_e10_pressure.png",
        "图5-8": generated_3d_metrics,
    }

    figure_outputs: dict[str, str] = {}
    for fig_id, src in figure_sources.items():
        suffix = src.suffix if src.suffix else ".png"
        status, out_path = copy_asset(src, f"{fig_id}_{src.stem}{suffix}")
        if status == "已完成":
            figure_outputs[fig_id] = out_path

    table_defs: dict[str, tuple[list[str], list[list[object]], str]] = {}
    table_defs["表2-1"] = (
        ["指标", "符号", "物理意义", "本文用途"],
        [
            ["努塞尔数", "Nu", "表征空气侧对流换热强度", "评价结构换热能力"],
            ["摩擦因子", "f", "表征流动阻力和压降代价", "评价流动阻力"],
            ["综合性能因子", "$\\eta$", "综合考虑换热增强与阻力变化", "作为差分进化优化目标"],
            ["压降", "$\\Delta p$", "入口与出口平均压力差", "解释阻力来源"],
            ["温升/温度场", "$T$", "反映热量在流固区域内的分布", "用于流热场重建与云图对比"],
        ],
        "D:/Desktop/大论文初稿/完整论文初稿.md 第2章方法定义",
    )
    table_defs["表2-2"] = (
        ["模块", "输入变量", "输出变量", "作用"],
        [
            ["参数编码 MLP", "Ta、Twa、Tb、Ts、Tt、Tad、theta", "高维潜在特征", "将七参数结构映射到可解码特征空间"],
            ["CNN/UNet 解码器", "潜在特征", "p、U、T 多通道场", "重建统一网格上的流热场"],
            ["性能预测头", "共享特征", "Nu、f", "输出标量性能指标"],
            ["后处理计算", "Nu、f 与基准量", "$\\eta$", "形成优化目标"],
        ],
        "D:/Desktop/大论文初稿/完整论文初稿.md 第2章与七参数_MLP_CNN流场重建/results/unet_pUt_320x96_full_e50/metrics.json",
    )
    table_defs["表2-3"] = (
        ["损失项", "约束对象", "物理/数值意义", "当前设置"],
        [
            ["标量性能损失", "Nu、f、eta", "保证代理模型能预测优化目标相关指标", f'alpha={metrics.get("alpha", "")}, beta={metrics.get("beta", "")}'],
            ["场重建损失", "p、U、T", "约束预测云图接近 CFD 导出场", f'field_weights={metrics["field_weights"]}'],
            ["梯度一致性损失", "p、U、T 空间梯度", "减少过度平滑，增强局部边界和尾迹区域一致性", f'grad_weight={metrics["grad_weight"]}'],
            ["边界区域误差", "翼型柱附近局部区域", "强调几何边界附近高梯度流热变化", "在 k 折和消融中统计 boundary_MAE"],
        ],
        "七参数_MLP_CNN流场重建/results/unet_pUt_320x96_full_e50/metrics.json 与 pvt_ablation/ablation_summary.json",
    )
    table_defs["表2-4"] = (
        ["步骤", "操作", "本文设置/含义"],
        [
            ["初始化", "在七参数设计空间内生成候选种群", "各参数受表3-3取值范围约束"],
            ["变异", "由多个个体差分组合生成变异向量", "增强全局搜索能力"],
            ["交叉", "将目标个体与变异个体组合", "形成新候选结构"],
            ["选择", "比较候选结构的 eta 预测值", "保留综合性能更优个体"],
            ["终止", "达到迭代代数或收敛条件", "输出 eta 最大的七参数组合"],
        ],
        "七参数_MLP_CNN流场重建/optimization_results/mlp_cnn_de_multiloss_e10/best_params.json 与 de_history.csv",
    )
    table_defs["表3-1"] = (
        ["参数类别", "参数名称", "符号", "数值", "单位", "说明"],
        [
            ["流体物性", "空气密度", "$\\rho$", "1.2", "kg/m^3", "空气视为不可压缩牛顿流体"],
            ["流体物性", "空气动力黏度", "$\\mu$", "$1.8\\times10^{-5}$", "Pa·s", "用于动量方程"],
            ["流体物性", "空气定压比热容", "$c_p$", "1005", "J/(kg·K)", "用于能量方程"],
            ["流体物性", "空气导热系数", "$k_f$", "0.026", "W/(m·K)", "用于空气侧传热计算"],
            ["固体物性", "固体材料", "—", "铝", "—", "翼型柱及导热基体材料"],
            ["固体物性", "固体密度", "$\\rho_s$", "2700", "kg/m^3", "用于固体区域物性设置"],
            ["固体物性", "固体导热系数", "$k_s$", "238", "W/(m·K)", "用于固体导热计算"],
            ["固体物性", "固体定压比热容", "$c_{ps}$", "900", "J/(kg·K)", "用于固体区域物性设置"],
            ["入口边界", "入口速度", "$u_{in}$", "5", "m/s", "速度入口"],
            ["入口边界", "入口温度", "$T_{in}$", "293.15", "K", "冷却空气入口温度"],
            ["出口边界", "出口压力", "$p_{out}$", "0", "Pa", "压力出口"],
            ["热源条件", "体积热源", "$q_v$", "$5\\times10^7$", "W/m^3", "芯片发热等效热源"],
            ["壁面条件", "固壁", "—", "no slip", "—", "流固界面无滑移"],
        ],
        "D:/Desktop/大论文初稿/完整论文初稿.md 与现有二维模型设置",
    )
    table_defs["表3-2"] = (
        ["维度", "工况", "网格", "网格数", "Nu", "f", "Tavg/K", "Tmax/K", "压降/Pa", "状态"],
        [[r.get("dimension"), r.get("case"), r.get("mesh_level"), r.get("element_count"), r.get("Nu"), r.get("f"), r.get("Tavg"), r.get("Tmax"), r.get("pressure_drop"), r.get("status")] for r in grid_rows],
        "七参数_MLP_CNN流场重建/analysis_results/grid_independence/grid_independence_summary.csv",
    )
    table_defs["表3-5"] = (
        ["项目", "设置"],
        [
            ["样本总数", metrics["sample_count"]],
            ["训练集", metrics["train_count"]],
            ["验证集", metrics["val_count"]],
            ["测试集", metrics["test_count"]],
            ["输入参数维度", metrics["condition_inputs"]],
            ["场变量", "p、U、T"],
            ["统一网格尺寸", "3×96×320"],
            ["归一化对象", "七参数、标量指标、PVT 场变量"],
        ],
        "七参数_MLP_CNN流场重建/results/unet_pUt_320x96_full_e50/metrics.json",
    )
    table_defs["表4-1"] = (
        ["项目", "设置"],
        [["样本数量", metrics["sample_count"]], ["训练/验证/测试", f'{metrics["train_count"]}/{metrics["val_count"]}/{metrics["test_count"]}'], ["模型", metrics["model"]], ["输入", metrics["condition_inputs"]], ["场权重", metrics["field_weights"]], ["梯度一致性权重", metrics["grad_weight"]], ["损失函数", metrics["loss_formula"]], ["设备", metrics["device"]]],
        "七参数_MLP_CNN流场重建/results/unet_pUt_320x96_full_e50/metrics.json",
    )
    table_defs["表4-2"] = (
        ["指标", "结果"],
        [["Nu_R2", f'{metrics["Nu_R2"]:.6f}'], ["Nu_MAE", f'{metrics["Nu_MAE"]:.6f}'], ["f_R2", f'{metrics["f_R2"]:.6f}'], ["f_MAE", f'{metrics["f_MAE"]:.6f}'], ["eta_R2", f'{metrics["eta_R2"]:.6f}'], ["eta_MAE", f'{metrics["eta_MAE"]:.6f}']],
        "七参数_MLP_CNN流场重建/results/unet_pUt_320x96_full_e50/metrics.json",
    )
    table_defs["表4-3"] = (
        ["指标", "结果"],
        [["field_MAE", f'{metrics["field_MAE"]:.6f}'], ["field_RMSE", f'{metrics["field_RMSE"]:.6f}'], ["p_MAE", f'{metrics["p_MAE"]:.6f} Pa'], ["p_RMSE", f'{metrics["p_RMSE"]:.6f}'], ["U_MAE", f'{metrics["U_MAE"]:.6f} m/s'], ["U_RMSE", f'{metrics["U_RMSE"]:.6f}'], ["T_MAE", f'{metrics["T_MAE"]:.6f} K'], ["T_RMSE", f'{metrics["T_RMSE"]:.6f}']],
        "七参数_MLP_CNN流场重建/results/unet_pUt_320x96_full_e50/metrics.json",
    )
    table_defs["表4-4"] = (
        ["指标", "均值", "标准差"],
        [["Nu_R2", f'{kfold["Nu_R2_mean"]:.6f}', f'{kfold["Nu_R2_std"]:.6f}'], ["f_R2", f'{kfold["f_R2_mean"]:.6f}', f'{kfold["f_R2_std"]:.6f}'], ["eta_R2", f'{kfold["eta_R2_mean"]:.6f}', f'{kfold["eta_R2_std"]:.6f}'], ["Nu_MAE", f'{kfold["Nu_MAE_mean"]:.6f}', f'{kfold["Nu_MAE_std"]:.6f}'], ["f_MAE", f'{kfold["f_MAE_mean"]:.6f}', f'{kfold["f_MAE_std"]:.6f}'], ["eta_MAE", f'{kfold["eta_MAE_mean"]:.6f}', f'{kfold["eta_MAE_std"]:.6f}'], ["p_MAE", f'{kfold["p_MAE_mean"]:.6f}', f'{kfold["p_MAE_std"]:.6f}'], ["U_MAE", f'{kfold["U_MAE_mean"]:.6f}', f'{kfold["U_MAE_std"]:.6f}'], ["T_MAE", f'{kfold["T_MAE_mean"]:.6f}', f'{kfold["T_MAE_std"]:.6f}'], ["field_MAE", f'{kfold["field_MAE_mean"]:.6f}', f'{kfold["field_MAE_std"]:.6f}'], ["boundary_MAE", f'{kfold["boundary_MAE_mean"]:.6f}', f'{kfold["boundary_MAE_std"]:.6f}']],
        "七参数_MLP_CNN流场重建/results/pvt_unet_kfold_3_e20/kfold_summary.json",
    )
    table_defs["表4-5"] = (
        ["组别", "模型设置", "目的"],
        [[r["group"], r["description"], "消融对比"] for r in ablation if r["group"] in {"A0", "A1", "A2", "A3", "A4"}],
        "七参数_MLP_CNN流场重建/results/pvt_ablation/ablation_summary.json",
    )
    table_defs["表4-6"] = (
        ["组别", "Nu_R2", "f_R2", "eta_R2", "p_MAE", "U_MAE", "T_MAE", "field_MAE", "boundary_MAE"],
        [[r["group"], f'{r["Nu_R2"]:.6f}', f'{r["f_R2"]:.6f}', f'{r["eta_R2"]:.6f}', "" if r["p_MAE"] is None else f'{r["p_MAE"]:.6f}', "" if r["U_MAE"] is None else f'{r["U_MAE"]:.6f}', "" if r["T_MAE"] is None else f'{r["T_MAE"]:.6f}', "" if r["field_MAE"] is None else f'{r["field_MAE"]:.6f}', "" if r["boundary_MAE"] is None else f'{r["boundary_MAE"]:.6f}'] for r in ablation if r["group"] in {"A0", "A1", "A2", "A3", "A4"}],
        "七参数_MLP_CNN流场重建/results/pvt_ablation/ablation_summary.json",
    )
    table_defs["表4-7"] = (
        ["参数", "数值"],
        [[k, f"{v:.6f}"] for k, v in best["best_params"].items()],
        "七参数_MLP_CNN流场重建/optimization_results/mlp_cnn_de_multiloss_e10/best_params.json",
    )
    table_defs["表4-8"] = (
        ["指标", "数值"],
        [[k, f"{v:.6f}"] for k, v in best["prediction"].items()],
        "七参数_MLP_CNN流场重建/optimization_results/mlp_cnn_de_multiloss_e10/best_params.json",
    )
    table_defs["表4-9"] = (
        ["指标", "MLP-CNN 预测", "CFD 复算", "误差"],
        [["Nu", f'{validation["proxy_prediction"]["Nu_pred"]:.6f}', f'{validation["comsol_result"]["Nu"]:.6f}', f'{validation["error"]["Nu_pred_minus_cfd"]:.6f}'], ["f", f'{validation["proxy_prediction"]["f_pred"]:.6f}', f'{validation["comsol_result"]["f"]:.6f}', f'{validation["error"]["f_pred_minus_cfd"]:.6f}'], ["eta", f'{validation["proxy_prediction"]["eta_pred"]:.6f}', f'{validation["comsol_result"]["eta_cfd"]:.6f}', f'{validation["error"]["eta_pred_minus_cfd"]:.6f}']],
        "七参数_MLP_CNN流场重建/validation_results/mlp_cnn_de_multiloss_e10/final_validation_report.json",
    )
    table_defs["表4-10"] = (
        ["指标", "优化模型 optimized"],
        [["Nu", validation["comsol_result"]["Nu"]], ["f", validation["comsol_result"]["f"]], ["eta", f'{validation["comsol_result"]["eta_cfd"]:.6f}'], ["delta_p/Pa", validation["comsol_result"]["delta_p"]], ["delta_T/K", validation["comsol_result"]["delta_T"]], ["Q_total", validation["comsol_result"]["Q_total"]]],
        "七参数_MLP_CNN流场重建/validation_results/mlp_cnn_de_multiloss_e10/final_validation_report.json",
    )
    table_defs["表4-11"] = (
        ["指标", "旧 1000 组 ANN/MLP baseline 复核", "当前 MLP-CNN-DE optimized 复核", "变化"],
        [
            ["Nu", "45.370713", f'{validation["comsol_result"]["Nu"]:.6f}', "+1.436%"],
            ["f", "0.108307", f'{validation["comsol_result"]["f"]:.6f}', "-1.523%"],
            ["eta", "1.420111", f'{validation["comsol_result"]["eta_cfd"]:.6f}', "+1.956%"],
        ],
        "docs/项目架构.md 与 七参数_MLP_CNN流场重建/validation_results/mlp_cnn_de_multiloss_e10/final_validation_report.json",
    )
    table_defs["表5-1"] = (
        ["参数", "基准模型 baseline", "优化模型 optimized", "单位"],
        [[p, f'{baseline_3d[p]:.6f}', f'{optimized_3d[p]:.6f}', "°" if p == "theta" else "—"] for p in ["Ta", "Twa", "Tb", "Ts", "Tt", "Tad", "theta"]],
        "comsol_3d_airfoil_radiator/generated_chip_airfoil_heat_sink/*_build_notes.json",
    )
    table_defs["表5-2"] = (
        ["参数类别", "参数名称", "符号", "数值", "单位", "说明"],
        [
            ["流体物性", "空气密度", "$\\rho$", "1.2", "kg/m^3", "空气视为不可压缩牛顿流体"],
            ["流体物性", "空气动力黏度", "$\\mu$", "$1.8\\times10^{-5}$", "Pa·s", "用于空气侧流动计算"],
            ["流体物性", "空气定压比热容", "$c_p$", "1005", "J/(kg·K)", "用于空气侧能量方程"],
            ["流体物性", "空气导热系数", "$k_f$", "0.026", "W/(m·K)", "用于空气侧传热计算"],
            ["固体物性", "散热器材料", "—", "铝", "—", "基底和翼型鳍片材料"],
            ["固体物性", "固体导热系数", "$k_s$", "238", "W/(m·K)", "用于固体导热计算"],
            ["入口边界", "入口速度", "$u_{in}$", "5", "m/s", "速度入口"],
            ["入口边界", "入口温度", "$T_{in}$", "293.15", "K", "冷却空气入口温度"],
            ["出口边界", "出口压力", "$p_{out}$", "0", "Pa", "压力出口，相对压力"],
            ["热源条件", "芯片热功率", "$Q$", "1.0", "W", "芯片底部施加总热功率"],
            ["外壁条件", "绝热壁", "—", "adiabatic", "—", "除入口、出口和流固界面外为空气域壁面"],
        ],
        "D:/Desktop/大论文初稿/完整论文初稿.md",
    )
    table_defs["表5-3"] = (
        ["维度", "工况", "网格", "Tavg/K", "Tmax/K", "压降/Pa", "热阻/K/W", "状态"],
        [[r.get("dimension"), r.get("case"), r.get("mesh_level"), r.get("Tavg"), r.get("Tmax"), r.get("pressure_drop"), r.get("thermal_resistance"), r.get("status")] for r in grid_rows if r.get("dimension") == "3D"],
        "七参数_MLP_CNN流场重建/analysis_results/grid_independence/grid_independence_summary.csv",
    )
    table_defs["表5-4"] = (
        ["指标", "baseline", "optimized", "变化"],
        [["Tavg/K", "379.201265", "375.663499", "-3.537766 K"], ["Tmax/K", "380.457118", "376.969653", "-3.487465 K"], ["delta_p/Pa", "0.013555", "0.013028", "-3.883%"], ["Rth/K/W", "86.051265", "82.513499", "-4.111%"], ["Nu3D", "39.729845", "41.433262", "+4.288%"], ["f3D", "2.581841", "2.481599", "-3.883%"], ["eta3D", "1.000000", "1.056732", "+5.6732%"]],
        "comsol_3d_airfoil_radiator/generated_chip_airfoil_heat_sink/results/seven_param_3d_summary.csv",
    )
    table_defs["表5-5"] = (
        ["结构", "Tavg/K", "Tmax/K", "Rth/K/W"],
        [[r["case"], r["t_chip_avg_k"], r["t_chip_max_k"], r["r_th_k_per_w"]] for r in summary_3d],
        "comsol_3d_airfoil_radiator/generated_chip_airfoil_heat_sink/results/seven_param_3d_summary.csv",
    )
    table_defs["表5-6"] = (
        ["结构", "delta_p/Pa", "f3D", "eta3D"],
        [[r["case"], r["delta_p_pa"], r["f_3d"], r["eta_3d"]] for r in summary_3d],
        "comsol_3d_airfoil_radiator/generated_chip_airfoil_heat_sink/results/seven_param_3d_summary.csv",
    )
    table_defs["表3-6"] = (
        ["排名", "参数", "RF permutation importance"],
        [[i + 1, r["parameter"], f'{r["rf_permutation_importance"]:.6f}'] for i, r in enumerate(sensitivity["eta_top_rf_permutation"])],
        "七参数_MLP_CNN流场重建/analysis_results/sensitivity/sensitivity_summary.json",
    )
    table_defs["表3-7"] = (
        ["排名", "参数", "eta_range", "eta_min", "eta_max"],
        [[i + 1, r["parameter"], f'{r["eta_range"]:.6f}', f'{r["eta_min"]:.6f}', f'{r["eta_max"]:.6f}'] for i, r in enumerate(sensitivity["eta_top_local"])],
        "七参数_MLP_CNN流场重建/analysis_results/sensitivity/sensitivity_summary.json",
    )

    for item in items:
        if item["类型"] != "表" or item["编号"] in table_defs:
            continue
        extracted = extract_markdown_table(text, item["编号"])
        if extracted:
            headers, rows = extracted
            table_defs[item["编号"]] = (headers, rows, "D:/Desktop/大论文初稿/完整论文初稿.md")

    table_outputs: dict[str, str] = {}
    for table_id, (headers, rows, source) in table_defs.items():
        out_md = TAB_DIR / f"{table_id}.md"
        write_md_table(out_md, table_id, headers, rows, source)
        table_outputs[table_id] = str(out_md)
        write_csv(TAB_DIR / f"{table_id}.csv", [dict(zip(headers, row)) for row in rows], headers)

    task_rows = []
    replacement_rows = []
    unfinished_rows = []
    for item in items:
        item_id = item["编号"]
        if item["类型"] == "图":
            status = "已完成" if item_id in figure_outputs else "未完成"
            out_path = figure_outputs.get(item_id, "")
            source = str(figure_sources[item_id]) if item_id in figure_sources else ""
            method = "复制已有真实图件" if status == "已完成" else "未找到同编号真实图件"
            insert = f"![{item['原占位文本']}]({Path(out_path).as_posix()})" if out_path else ""
        else:
            status = "已完成" if item_id in table_outputs else "未完成"
            out_path = table_outputs.get(item_id, "")
            source = table_defs[item_id][2] if item_id in table_defs else ""
            method = "由真实 JSON/CSV 生成 Markdown/CSV 表" if status == "已完成" else "论文内已有表或缺少可核验数据源"
            insert = f"见表格文件：`{out_path}`" if out_path else ""
        row = {
            "图表编号": item_id,
            "标题": item["标题"],
            "所在章节": item["章节"],
            "当前状态": status,
            "数据来源": source,
            "生成方式": method,
            "输出文件": out_path,
            "是否可直接写入论文": "是" if status == "已完成" else "否",
        }
        task_rows.append(row)
        replacement_rows.append({
            "图表编号": item_id,
            "原占位文本": item["原占位文本"],
            "建议替换内容": insert,
        })
        if status != "已完成":
            unfinished_rows.append({
                "图表编号": item_id,
                "标题": item["标题"],
                "原因": method,
                "建议": "保留现有正文表格，或补充对应真实数据/导出图后再生成。",
            })

    task_headers = ["图表编号", "标题", "所在章节", "当前状态", "数据来源", "生成方式", "输出文件", "是否可直接写入论文"]
    write_csv(REP_DIR / "图表补全任务总表.csv", task_rows, task_headers)
    (REP_DIR / "图表补全任务总表.md").write_text("# 图表补全任务总表\n\n" + md_table(task_headers, [[r[h] for h in task_headers] for r in task_rows]), encoding="utf-8")

    repl_headers = ["图表编号", "原占位文本", "建议替换内容"]
    write_csv(REP_DIR / "论文图表替换清单.csv", replacement_rows, repl_headers)
    (REP_DIR / "论文图表替换清单.md").write_text("# 论文图表替换清单\n\n" + md_table(repl_headers, [[r[h] for h in repl_headers] for r in replacement_rows]), encoding="utf-8")

    un_headers = ["图表编号", "标题", "原因", "建议"]
    write_csv(REP_DIR / "未完成原因表.csv", unfinished_rows, un_headers)
    (REP_DIR / "未完成原因表.md").write_text("# 未完成原因表\n\n" + md_table(un_headers, [[r[h] for h in un_headers] for r in unfinished_rows]), encoding="utf-8")

    source_index = {
        "thesis": str(THESIS),
        "thesis_sha256_before": thesis_hash,
        "metrics": str(ROOT / "七参数_MLP_CNN流场重建/results/unet_pUt_320x96_full_e50/metrics.json"),
        "kfold": str(ROOT / "七参数_MLP_CNN流场重建/results/pvt_unet_kfold_3_e20/kfold_summary.json"),
        "ablation": str(ROOT / "七参数_MLP_CNN流场重建/results/pvt_ablation/ablation_summary.json"),
        "de_best": str(ROOT / "七参数_MLP_CNN流场重建/optimization_results/mlp_cnn_de_multiloss_e10/best_params.json"),
        "validation": str(ROOT / "七参数_MLP_CNN流场重建/validation_results/mlp_cnn_de_multiloss_e10/final_validation_report.json"),
        "3d_summary": str(ROOT / "comsol_3d_airfoil_radiator/generated_chip_airfoil_heat_sink/results/seven_param_3d_summary.csv"),
    }
    (SRC_DIR / "source_index.json").write_text(json.dumps(source_index, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.copy2(Path(__file__), SCR_DIR / Path(__file__).name)

    out_summary = {
        "thesis_sha256_before": thesis_hash,
        "thesis_sha256_after": sha256(THESIS),
        "figure_count_done": sum(1 for r in task_rows if r["图表编号"].startswith("图") and r["当前状态"] == "已完成"),
        "table_count_done": sum(1 for r in task_rows if r["图表编号"].startswith("表") and r["当前状态"] == "已完成"),
        "unfinished_count": len(unfinished_rows),
    }
    (REP_DIR / "生成摘要.json").write_text(json.dumps(out_summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out_summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
