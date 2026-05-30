#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Prepare thesis figures and replace figure/table placeholders in the draft."""

import json
import re
import shutil
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score


ROOT = Path(__file__).resolve().parent
THESIS_DIR = ROOT / "大论文初稿"
FIGURE_DIR = THESIS_DIR / "figures"
THESIS_PATH = THESIS_DIR / "完整论文初稿.md"
PAPER_SVG_DIR = ROOT / "paper_figures_svg"
SMALL_PAPER_DIR = THESIS_DIR / "小论文图片"
RESULT_DIR = ROOT / "ai_cnn_model_results"
LABELS_PATH = ROOT / "consol_cfddata" / "labels.csv"

PARAM_COLS = ["Ta", "Twa", "Tb", "Ts", "Tt", "Tad"]


def ensure_dirs():
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)


def copy_asset(source, target_name):
    target = FIGURE_DIR / target_name
    shutil.copyfile(source, target)
    return target.name


def convert_image(source, target_name):
    target = FIGURE_DIR / target_name
    img = Image.open(source)
    img.save(target)
    return target.name


def fit_image_to_box(image, box_size):
    box_w, box_h = box_size
    img = image.copy()
    img.thumbnail((box_w, box_h), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (box_w, box_h), "white")
    x = (box_w - img.width) // 2
    y = (box_h - img.height) // 2
    canvas.paste(img, (x, y))
    return canvas


def make_side_by_side_comparison(left_path, right_path, output_name, left_label, right_label):
    output_path = FIGURE_DIR / output_name
    left = fit_image_to_box(Image.open(left_path).convert("RGB"), (900, 550))
    right = fit_image_to_box(Image.open(right_path).convert("RGB"), (900, 550))
    canvas = Image.new("RGB", (1880, 640), "white")
    canvas.paste(left, (30, 58))
    canvas.paste(right, (950, 58))

    from PIL import ImageDraw, ImageFont

    draw = ImageDraw.Draw(canvas)
    font_path = Path("C:/Windows/Fonts/msyh.ttc")
    font = ImageFont.truetype(str(font_path), 28) if font_path.exists() else ImageFont.load_default()
    draw.text((30, 18), left_label, fill=(31, 41, 55), font=font)
    draw.text((950, 18), right_label, fill=(31, 41, 55), font=font)
    canvas.save(output_path)
    return output_path.name


def write_svg(target_name, body, width=1000, height=560):
    target = FIGURE_DIR / target_name
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<style>
text {{ font-family: "Microsoft YaHei", Arial, sans-serif; fill: #1f2937; }}
.title {{ font-size: 28px; font-weight: 700; }}
.label {{ font-size: 19px; font-weight: 600; }}
.small {{ font-size: 15px; }}
.box {{ fill: #f8fafc; stroke: #2563eb; stroke-width: 2; rx: 12; }}
.green {{ stroke: #16a34a; }}
.orange {{ stroke: #f97316; }}
.red {{ stroke: #dc2626; }}
.line {{ stroke: #334155; stroke-width: 2; fill: none; }}
.arrow {{ stroke: #2563eb; stroke-width: 3; fill: none; marker-end: url(#arrow); }}
</style>
<defs>
<marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">
<path d="M 0 0 L 10 5 L 0 10 z" fill="#2563eb"/>
</marker>
</defs>
<rect width="100%" height="100%" fill="#ffffff"/>
{body}
</svg>
"""
    target.write_text(svg, encoding="utf-8")
    return target.name


def flow_svg(target_name, steps, title):
    step_w = 138
    gap = 18
    x0 = (1000 - (len(steps) * step_w + (len(steps) - 1) * gap)) / 2
    y = 205
    body = [
        '<rect x="38" y="52" width="924" height="420" rx="20" fill="#f8fafc" stroke="#dbeafe" stroke-width="1.5"/>',
        '<path d="M70,118 L930,118" stroke="#dbeafe" stroke-width="2"/>',
        '<text x="84" y="93" class="small" fill="#475569">workflow</text>',
    ]
    for idx, step in enumerate(steps):
        x = x0 + idx * (step_w + gap)
        fill = "#eff6ff" if idx not in (0, len(steps) - 1) else "#ecfeff"
        stroke = "#2563eb" if idx not in (0, len(steps) - 1) else "#0891b2"
        body.append(f'<rect x="{x:.1f}" y="{y}" width="{step_w}" height="118" rx="14" fill="{fill}" stroke="{stroke}" stroke-width="1.8"/>')
        body.append(f'<circle cx="{x + 22:.1f}" cy="{y + 24}" r="13" fill="{stroke}"/>')
        body.append(f'<text x="{x + 22:.1f}" y="{y + 30}" text-anchor="middle" fill="#ffffff" font-size="14" font-weight="700">{idx + 1}</text>')
        lines = step.split("\\n")
        for line_id, line in enumerate(lines):
            body.append(
                f'<text x="{x + step_w / 2:.1f}" y="{y + 62 + line_id * 24}" '
                f'text-anchor="middle" class="small" font-weight="600">{line}</text>'
            )
        if idx < len(steps) - 1:
            x1 = x + step_w + 4
            x2 = x + step_w + gap - 4
            body.append(f'<path d="M{x1:.1f},{y + 59} L{x2:.1f},{y + 59}" class="arrow"/>')
    body.append(f'<text x="500" y="405" text-anchor="middle" class="small" fill="#64748b">{title}</text>')
    return write_svg(target_name, "\n".join(body))


def technical_route_svg():
    """绘制论文技术路线图；中文标注较多，采用SVG保证文字和箭头可编辑。"""
    def box(x, y, w, h, text, fill="#f8fafc", stroke="#2563eb", font_size=18):
        parts = text.split("\\n")
        elems = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{fill}" stroke="{stroke}" stroke-width="1.8"/>']
        start_y = y + h / 2 - (len(parts) - 1) * 12 + 6
        for idx, part in enumerate(parts):
            elems.append(
                f'<text x="{x + w / 2}" y="{start_y + idx * 24:.1f}" text-anchor="middle" '
                f'font-size="{font_size}" font-weight="600">{part}</text>'
            )
        return elems

    def arrow(x1, y1, x2, y2, color="#2563eb"):
        return f'<path d="M{x1},{y1} L{x2},{y2}" stroke="{color}" stroke-width="2.4" fill="none" marker-end="url(#arrow)"/>'

    body = [
        '<rect x="34" y="34" width="1132" height="632" rx="18" fill="#ffffff" stroke="#cbd5e1" stroke-width="1.4"/>',
        '<rect x="58" y="76" width="1084" height="154" rx="14" fill="#f8fafc" stroke="#dbeafe" stroke-width="1.2"/>',
        '<rect x="58" y="274" width="1084" height="178" rx="14" fill="#f8fafc" stroke="#dbeafe" stroke-width="1.2"/>',
        '<rect x="58" y="496" width="1084" height="122" rx="14" fill="#f8fafc" stroke="#dbeafe" stroke-width="1.2"/>',
        '<text x="82" y="112" font-size="17" font-weight="700" fill="#1d4ed8">数值建模与样本构建</text>',
        '<text x="82" y="310" font-size="17" font-weight="700" fill="#1d4ed8">多模态预测与参数优化</text>',
        '<text x="82" y="532" font-size="17" font-weight="700" fill="#1d4ed8">独立复核与三维验证</text>',
    ]

    top = [
        (88, 132, 158, 66, "研究对象\\n3×8翼型管阵列"),
        (286, 132, 158, 66, "六维变量\\nTa,Twa,Tb\\nTs,Tt,Tad", "#f8fafc", "#2563eb", 16),
        (484, 132, 158, 66, "COMSOL\\n批量稳态计算"),
        (682, 132, 174, 66, "多模态样本库\\n参数+三场图+标签", "#f8fafc", "#2563eb", 17),
        (896, 132, 174, 66, "数据预处理\\n划分与归一化"),
    ]
    for item in top:
        body.extend(box(*item))
    for x1, x2 in [(246, 286), (444, 484), (642, 682), (856, 896)]:
        body.append(arrow(x1, 165, x2, 165))

    mid_boxes = [
        (132, 340, 164, 72, "几何参数分支\\nMLP特征编码", "#ecfeff", "#0891b2"),
        (378, 315, 184, 72, "视觉分支\\nCNN + CBAM", "#eff6ff", "#2563eb"),
        (378, 397, 184, 42, "速度/温度/压力\\n空间特征", "#eff6ff", "#2563eb", 16),
        (648, 340, 164, 72, "特征拼接融合\\n回归Nu与f", "#f8fafc", "#2563eb"),
        (898, 340, 164, 72, "差分进化搜索\\n最大化η", "#fff7ed", "#f97316"),
    ]
    for item in mid_boxes:
        body.extend(box(*item))
    body.append('<path d="M983,198 L983,300 L980,340" stroke="#64748b" stroke-width="2.2" fill="none" marker-end="url(#arrow)"/>')
    body.append(arrow(296, 376, 648, 376))
    body.append(arrow(562, 351, 648, 351))
    body.append(arrow(562, 418, 648, 400))
    body.append(arrow(812, 376, 898, 376, "#f97316"))

    bottom = [
        (132, 552, 176, 50, "最优候选结构"),
        (390, 552, 176, 50, "二维CFD独立复核", "#fff7ed", "#f97316"),
        (648, 552, 176, 50, "流场机理分析"),
        (906, 552, 176, 50, "三维代表性模型验证", "#ecfeff", "#0891b2"),
    ]
    for item in bottom:
        body.extend(box(*item))
    body.append('<path d="M980,412 L980,488 L220,488 L220,552" stroke="#f97316" stroke-width="2.4" fill="none" marker-end="url(#arrow)"/>')
    for x1, x2 in [(308, 390), (566, 648), (824, 906)]:
        body.append(arrow(x1, 577, x2, 577))

    body.extend([
        '<text x="600" y="250" text-anchor="middle" font-size="15" fill="#64748b">样本标签：Nu、f、压降、换热指标；图像输入：速度场、温度场、压力场</text>',
        '<text x="600" y="474" text-anchor="middle" font-size="15" fill="#64748b">模型验证：测试集预测性能 + 五折交叉验证 + 纯几何MLP对比</text>',
        '<text x="600" y="640" text-anchor="middle" font-size="15" fill="#64748b">最终结论以独立CFD复核和三维代表性模型结果为依据</text>',
    ])
    return write_svg("fig1_2_technical_route.svg", "\n".join(body), width=1200, height=700)


def simple_schematic(target_name, title, labels):
    body = [
        '<rect x="42" y="46" width="916" height="420" rx="20" fill="#f8fafc" stroke="#dbeafe" stroke-width="1.5"/>',
        '<rect x="90" y="150" width="820" height="220" rx="8" fill="#ffffff" stroke="#334155" stroke-width="1.8"/>',
    ]
    body.append('<path d="M118,260 L252,260" class="arrow"/>')
    body.append('<text x="118" y="230" class="label" fill="#2563eb">空气入口</text>')
    body.append('<path d="M748,260 L885,260" class="arrow"/>')
    body.append('<text x="785" y="230" class="label" fill="#2563eb">空气出口</text>')
    for row in range(3):
        for col in range(8):
            cx = 310 + col * 60 + (row % 2) * 18
            cy = 210 + row * 58
            body.append(f'<ellipse cx="{cx}" cy="{cy}" rx="27" ry="7" fill="#dbeafe" stroke="#1d4ed8" stroke-width="1.3"/>')
    body.append('<rect x="376" y="384" width="248" height="54" rx="10" fill="#fff7ed" stroke="#f97316" stroke-width="1.5"/>')
    for idx, label in enumerate(labels):
        body.append(f'<text x="500" y="{406 + idx * 18}" text-anchor="middle" class="small">{label}</text>')
    body.append(f'<text x="500" y="505" text-anchor="middle" class="small" fill="#64748b">{title}</text>')
    return write_svg(target_name, "\n".join(body))


def field_comparison_schematic(target_name, field_name, palette):
    left_color, mid_color, right_color = palette
    body = [
        '<rect x="42" y="46" width="916" height="420" rx="20" fill="#f8fafc" stroke="#dbeafe" stroke-width="1.5"/>',
        '<text x="275" y="93" text-anchor="middle" class="label">基准结构</text>',
        '<text x="725" y="93" text-anchor="middle" class="label">优化结构</text>',
    ]
    for x0, skew in [(85, 0), (535, 22)]:
        body.append(f'<rect x="{x0}" y="128" width="380" height="210" rx="8" fill="#ffffff" stroke="#334155" stroke-width="1.6"/>')
        for row in range(3):
            for col in range(8):
                cx = x0 + 78 + col * 37 + (row % 2) * skew / 3
                cy = 185 + row * 55
                body.append(f'<ellipse cx="{cx:.1f}" cy="{cy}" rx="17" ry="5" fill="#dbeafe" stroke="#1d4ed8" stroke-width="1"/>')
        for row in range(3):
            y = 178 + row * 55
            body.append(
                f'<path d="M{x0+42},{y} C{x0+125},{y-22} {x0+245},{y+24} {x0+350},{y}" '
                f'stroke="{mid_color}" stroke-width="9" opacity="0.35" fill="none"/>'
            )
            body.append(f'<path d="M{x0+38},{y} L{x0+350},{y}" stroke="#2563eb" stroke-width="2.2" marker-end="url(#arrow)"/>')
    body.append(f'<rect x="170" y="360" width="210" height="38" rx="8" fill="{left_color}" opacity="0.16" stroke="{left_color}"/>')
    body.append(f'<rect x="620" y="360" width="210" height="38" rx="8" fill="{right_color}" opacity="0.16" stroke="{right_color}"/>')
    body.append(f'<text x="275" y="385" text-anchor="middle" class="small">{field_name}分布特征</text>')
    body.append(f'<text x="725" y="385" text-anchor="middle" class="small">交错后局部分布变化</text>')
    body.append(f'<text x="500" y="505" text-anchor="middle" class="small" fill="#64748b">三维{field_name}对比示意，正式定稿替换为COMSOL同色标云图</text>')
    return write_svg(target_name, "\n".join(body))


def mesh_overall_svg():
    body = ['<text x="500" y="58" text-anchor="middle" class="title">二维计算域整体网格划分示意</text>']
    body.append('<rect x="80" y="125" width="840" height="300" fill="#f8fafc" stroke="#334155" stroke-width="2"/>')
    # 整体网格用稀疏三角单元表示，避免与局部加密图重复。
    for x in range(80, 921, 70):
        body.append(f'<path d="M{x},125 L{x + 70},425" stroke="#94a3b8" stroke-width="1"/>')
        body.append(f'<path d="M{x},425 L{x + 70},125" stroke="#cbd5e1" stroke-width="1"/>')
    for y in range(125, 426, 50):
        body.append(f'<path d="M80,{y} L920,{y}" stroke="#cbd5e1" stroke-width="1"/>')
    for row in range(3):
        for col in range(8):
            cx = 260 + col * 68 + (row % 2) * 20
            cy = 210 + row * 58
            body.append(f'<ellipse cx="{cx}" cy="{cy}" rx="28" ry="7" fill="#dbeafe" stroke="#1d4ed8" stroke-width="1.4"/>')
    body.append('<path d="M105,455 L895,455" class="arrow"/>')
    body.append('<text x="500" y="490" text-anchor="middle" class="small">主流方向及整体计算域网格分布</text>')
    return write_svg("fig3_3_mesh.svg", "\n".join(body))


def mesh_local_svg():
    body = ['<text x="500" y="58" text-anchor="middle" class="title">翼型近壁面局部加密示意</text>']
    body.append('<rect x="70" y="110" width="860" height="360" fill="#ffffff" stroke="#334155" stroke-width="2"/>')
    body.append('<path d="M250,285 C330,205 565,235 690,285 C560,350 335,360 250,285 Z" fill="#e0f2fe" stroke="#075985" stroke-width="2"/>')
    for offset in [0, 18, 36, 58, 84]:
        body.append(
            f'<path d="M{250-offset/2},{285} C{330-offset},{205-offset/3} {565+offset},{235-offset/4} {690+offset/2},{285} '
            f'C{560+offset},{350+offset/4} {335-offset},{360+offset/3} {250-offset/2},{285} Z" '
            'fill="none" stroke="#60a5fa" stroke-width="1.2"/>'
        )
    for x in range(115, 890, 38):
        body.append(f'<path d="M{x},130 L{x + 25},455" stroke="#cbd5e1" stroke-width="0.8"/>')
        body.append(f'<path d="M{x},455 L{x + 25},130" stroke="#e2e8f0" stroke-width="0.8"/>')
    body.append('<text x="500" y="505" text-anchor="middle" class="small">前缘、尾缘和窄通道区域采用更密集的近壁面网格</text>')
    return write_svg("fig3_4_local_mesh.svg", "\n".join(body))


def mesh_3d_schematic_svg():
    body = [
        '<rect x="42" y="46" width="916" height="420" rx="20" fill="#f8fafc" stroke="#dbeafe" stroke-width="1.5"/>',
        '<text x="165" y="92" class="label">整体空气域</text>',
        '<text x="680" y="92" class="label">局部加密区域</text>',
    ]
    body.append('<path d="M105,155 L405,115 L485,165 L185,210 Z" fill="#e0f2fe" stroke="#334155" stroke-width="1.5"/>')
    body.append('<path d="M185,210 L485,165 L485,315 L185,360 Z" fill="#f8fafc" stroke="#334155" stroke-width="1.5"/>')
    body.append('<path d="M105,155 L185,210 L185,360 L105,300 Z" fill="#eff6ff" stroke="#334155" stroke-width="1.5"/>')
    for i in range(9):
        x = 120 + i * 38
        body.append(f'<path d="M{x},156 L{x+76},337" stroke="#cbd5e1" stroke-width="1"/>')
    for i in range(5):
        y = 175 + i * 32
        body.append(f'<path d="M126,{y} L455,{y-44}" stroke="#cbd5e1" stroke-width="1"/>')
    body.append('<rect x="610" y="145" width="270" height="185" rx="10" fill="#ffffff" stroke="#334155" stroke-width="1.5"/>')
    for row in range(3):
        for col in range(4):
            cx = 660 + col * 52 + (row % 2) * 14
            cy = 190 + row * 48
            body.append(f'<ellipse cx="{cx}" cy="{cy}" rx="24" ry="7" fill="#dbeafe" stroke="#1d4ed8"/>')
            for r in [14, 24, 35]:
                body.append(f'<ellipse cx="{cx}" cy="{cy}" rx="{r}" ry="{r/3}" fill="none" stroke="#93c5fd" stroke-width="0.9"/>')
    body.append('<path d="M480,235 C535,215 560,205 605,210" class="arrow"/>')
    body.append('<text x="500" y="395" text-anchor="middle" class="small">三维网格采用整体自由四面体网格，并在翼型柱前缘、尾缘和基座上表面附近加密</text>')
    return write_svg("fig5_3_3d_mesh_schematic.svg", "\n".join(body))


def crop_field_comparison():
    """Create independent SVG-wrapped field comparison figures from the combined image."""
    source = PAPER_SVG_DIR / "Fig8_Baseline_Optimal_Field_Comparison.png"
    image = Image.open(source).convert("RGB")
    width, height = image.size
    labels = {
        "4-8": ("fig4_8_velocity_comparison.png", "fig4_8_baseline_optimal_velocity.svg", "速度场对比", (0, 0, width // 3, height)),
        "4-10": (
            "fig4_10_pressure_comparison.png",
            "fig4_10_baseline_optimal_pressure.svg",
            "压力场对比",
            (width // 3, 0, 2 * width // 3, height),
        ),
        "4-9": (
            "fig4_9_temperature_comparison.png",
            "fig4_9_baseline_optimal_temperature.svg",
            "温度场对比",
            (2 * width // 3, 0, width, height),
        ),
    }
    result = {}
    for fig_id, (png_name, svg_name, title, crop_box) in labels.items():
        png_path = FIGURE_DIR / png_name
        image.crop(crop_box).save(png_path)
        body = (
            f'<text x="500" y="45" text-anchor="middle" class="title">{title}</text>\n'
            f'<image href="{png_name}" x="45" y="75" width="910" height="430" preserveAspectRatio="xMidYMid meet"/>\n'
            f'<text x="500" y="535" text-anchor="middle" class="small">由COMSOL后处理云图裁剪生成，基准结构与优化结构保持同一视图来源</text>'
        )
        result[fig_id] = write_svg(svg_name, body, width=1000, height=560)
    return result


def tube_wake_comparison():
    body = ['<text x="500" y="58" text-anchor="middle" class="title">不同管型空气绕流特征对比</text>']
    names = ["圆管", "扁管", "翼型管"]
    for i, name in enumerate(names):
        x = 80 + i * 310
        body.append(f'<rect x="{x}" y="125" width="245" height="300" class="box"/>')
        body.append(f'<text x="{x + 122}" y="170" text-anchor="middle" class="label">{name}</text>')
        body.append(f'<path d="M{x + 25},270 L{x + 82},270" class="arrow"/>')
        if name == "圆管":
            body.append(f'<circle cx="{x + 120}" cy="270" r="34" fill="#dbeafe" stroke="#1d4ed8"/>')
            body.append(f'<path d="M{x + 155},250 C{x + 205},235 {x + 220},305 {x + 160},292" fill="#fee2e2" stroke="#ef4444"/>')
        elif name == "扁管":
            body.append(f'<rect x="{x + 90}" y="248" width="80" height="44" rx="22" fill="#dbeafe" stroke="#1d4ed8"/>')
            body.append(f'<path d="M{x + 172},254 C{x + 215},250 {x + 220},290 {x + 174},288" fill="#ffedd5" stroke="#f97316"/>')
        else:
            body.append(f'<path d="M{x + 80},270 C{x + 110},235 {x + 185},250 {x + 205},270 C{x + 180},286 {x + 110},300 {x + 80},270 Z" fill="#dbeafe" stroke="#1d4ed8"/>')
            body.append(f'<path d="M{x + 205},262 C{x + 230},260 {x + 235},280 {x + 206},278" fill="#dcfce7" stroke="#16a34a"/>')
        body.append(f'<text x="{x + 122}" y="382" text-anchor="middle" class="small">尾迹/回流区相对示意</text>')
    return write_svg("fig2_2_tube_wake_comparison.svg", "\n".join(body))


def generate_handmade_svgs():
    figure_map = {}
    figure_map["1-1"] = simple_schematic(
        "fig1_1_engine_cooling_module.svg",
        "工程车辆冷却模块与管翅式散热器应用示意",
        ["发动机/液压系统产生热量", "散热器芯体进行空气侧换热", "风扇驱动冷却空气通过芯体"],
    )
    figure_map["1-2"] = technical_route_svg()
    figure_map["2-1"] = flow_svg(
        "fig2_1_heat_transfer_path.svg",
        ["等效热源", "翼型管/翅片\\n固体导热", "流固界面\\n对流换热", "空气带热\\n排出"],
        "翼型管翅片散热器换热路径",
    )
    figure_map["2-2"] = tube_wake_comparison()
    figure_map["2-4"] = flow_svg(
        "fig2_4_method_framework.svg",
        ["六维参数", "速度/温度/压力\\n场图像", "多模态\\n特征融合", "Nu、f\\n预测", "优化搜索", "CFD复核"],
        "多模态代理模型与参数化优化总体流程",
    )
    figure_map["3-2"] = simple_schematic(
        "fig3_2_boundary_heat_source.svg",
        "二维计算域边界条件与等效热源设置",
        ["入口速度 uin = 5 m/s", "出口相对压力 pout = 0 Pa", "翼型管固体区设置体积热源 qv"],
    )
    figure_map["3-5"] = flow_svg(
        "fig3_5_cfd_batch_workflow.svg",
        ["参数采样", "几何生成", "网格划分", "COMSOL求解", "场图导出", "标签保存"],
        "参数化工况设计与CFD样本批量生成流程",
    )
    figure_map["3-6"] = flow_svg(
        "fig3_6_multimodal_dataset.svg",
        ["X_i\\n六维参数", "I_i\\n三类场图", "y_i\\nNu、f标签", "训练/验证/测试\\n数据划分"],
        "多模态数据集构成",
    )
    figure_map["4-2"] = flow_svg(
        "fig4_2_branch_structure.svg",
        ["几何参数\\nMLP分支", "场图像\\nCNN分支", "CBAM\\n注意力模块", "特征拼接", "全连接\\n回归输出"],
        "几何参数分支与流场图像分支结构",
    )
    figure_map["5-1"] = simple_schematic(
        "fig5_1_engine_bay_scenario.svg",
        "工程车辆动力舱冷却模块应用场景",
        ["动力舱热源通过散热器排热", "风扇组织入口来流", "三维模型用于代表性验证"],
    )
    figure_map["5-2"] = simple_schematic(
        "fig5_2_3d_model_schematic.svg",
        "三维翼型柱散热器代表性计算模型",
        ["铝基座承接底部芯片热源", "3×8翼型柱阵列位于基座上方", "空气沿通道掠过翼型柱阵列"],
    )
    figure_map["5-3"] = mesh_3d_schematic_svg()
    figure_map["5-6"] = field_comparison_schematic(
        "fig5_6_3d_速度场.svg",
        "速度场",
        ("#2563eb", "#38bdf8", "#0f766e"),
    )
    figure_map["5-7"] = field_comparison_schematic(
        "fig5_7_3d_温度场.svg",
        "温度场",
        ("#f97316", "#fb923c", "#dc2626"),
    )
    figure_map["5-8"] = field_comparison_schematic(
        "fig5_8_3d_压力场.svg",
        "压力场",
        ("#64748b", "#60a5fa", "#1d4ed8"),
    )
    return figure_map


def generate_data_plots():
    figure_map = {}
    df = pd.read_csv(LABELS_PATH)

    for target, fname, ylabel in [
        ("Nu", "fig3_10_nu_response.svg", "Nu"),
        ("f", "fig3_11_f_response.svg", "f"),
    ]:
        fig, axes = plt.subplots(2, 3, figsize=(10, 5.6), constrained_layout=True)
        for ax, col in zip(axes.ravel(), PARAM_COLS):
            tmp = df[[col, target]].dropna().copy()
            tmp["bin"] = pd.qcut(tmp[col], q=6, duplicates="drop")
            grouped = tmp.groupby("bin", observed=True).agg({col: "mean", target: "mean"})
            ax.plot(grouped[col], grouped[target], marker="o", linewidth=1.8)
            ax.set_xlabel(col)
            ax.set_ylabel(ylabel)
            ax.grid(False)
        fig.savefig(FIGURE_DIR / fname, format="svg")
        plt.close(fig)
        figure_map["3-10" if target == "Nu" else "3-11"] = fname

    eta = df["Nu"] / np.cbrt(np.maximum(df["f"], 1e-12))
    eta_df = df[PARAM_COLS].copy()
    eta_df["eta"] = eta
    fig, axes = plt.subplots(2, 3, figsize=(10, 5.6), constrained_layout=True)
    for ax, col in zip(axes.ravel(), PARAM_COLS):
        tmp = eta_df[[col, "eta"]].dropna().copy()
        tmp["bin"] = pd.qcut(tmp[col], q=6, duplicates="drop")
        grouped = tmp.groupby("bin", observed=True).agg({col: "mean", "eta": "mean"})
        ax.plot(grouped[col], grouped["eta"], marker="o", linewidth=1.8, color="#2563eb")
        ax.set_xlabel(col)
        ax.set_ylabel("eta")
        ax.grid(False)
    fig.savefig(FIGURE_DIR / "fig3_12_eta_response.svg", format="svg")
    plt.close(fig)
    figure_map["3-12"] = "fig3_12_eta_response.svg"

    x = df[PARAM_COLS].to_numpy()
    y = np.column_stack([df["Nu"].to_numpy(), df["f"].to_numpy(), eta.to_numpy()])
    labels = ["Nu", "f", "eta"]
    importances = []
    for idx in range(y.shape[1]):
        model = RandomForestRegressor(n_estimators=300, random_state=42, n_jobs=1)
        model.fit(x, y[:, idx])
        importances.append(model.feature_importances_)
    importance_df = pd.DataFrame(importances, index=labels, columns=PARAM_COLS)
    importance_df.to_csv(FIGURE_DIR / "fig3_13_parameter_importance.csv", encoding="utf-8-sig")
    fig, ax = plt.subplots(figsize=(9, 4.8), constrained_layout=True)
    im = ax.imshow(importance_df.to_numpy(), cmap="Blues", aspect="auto")
    ax.set_xticks(range(len(PARAM_COLS)), PARAM_COLS)
    ax.set_yticks(range(len(labels)), labels)
    for i in range(len(labels)):
        for j in range(len(PARAM_COLS)):
            ax.text(j, i, f"{importance_df.iloc[i, j]:.2f}", ha="center", va="center", fontsize=9)
    fig.colorbar(im, ax=ax, label="importance")
    fig.savefig(FIGURE_DIR / "fig3_13_parameter_importance.svg", format="svg")
    plt.close(fig)
    figure_map["3-13"] = "fig3_13_parameter_importance.svg"

    history = pd.read_csv(RESULT_DIR / "cnn_training_history_digitized.csv")
    fig, ax = plt.subplots(figsize=(7.5, 4.5), constrained_layout=True)
    ax.plot(history["epoch"], history["train_loss"], label="train loss", linewidth=2)
    ax.plot(history["epoch"], history["val_loss"], label="validation loss", linewidth=2)
    ax.set_xlabel("epoch")
    ax.set_ylabel("normalized MSE")
    ax.legend()
    ax.grid(False)
    fig.savefig(FIGURE_DIR / "fig4_3_training_loss.svg", format="svg")
    plt.close(fig)
    figure_map["4-3"] = "fig4_3_training_loss.svg"

    pred = pd.read_csv(RESULT_DIR / "multimodal_feature_predictions.csv")
    for target, fname, true_col, pred_col in [
        ("Nu", "fig4_4_nu_prediction.svg", "true_Nu", "pred_Nu"),
        ("f", "fig4_5_f_prediction.svg", "true_f", "pred_f"),
    ]:
        fig, axes = plt.subplots(1, 2, figsize=(9, 4), constrained_layout=True)
        true = pred[true_col].to_numpy()
        predicted = pred[pred_col].to_numpy()
        axes[0].scatter(true, predicted, s=22, alpha=0.78)
        low = min(true.min(), predicted.min())
        high = max(true.max(), predicted.max())
        axes[0].plot([low, high], [low, high], "--", color="#dc2626", linewidth=1.5)
        axes[0].set_xlabel(f"CFD true {target}")
        axes[0].set_ylabel(f"Predicted {target}")
        axes[0].set_title(f"R2={r2_score(true, predicted):.4f}")
        axes[0].grid(False)
        axes[1].hist(predicted - true, bins=14, color="#60a5fa", edgecolor="white")
        axes[1].set_xlabel(f"Error of {target}")
        axes[1].set_ylabel("count")
        axes[1].grid(False)
        fig.savefig(FIGURE_DIR / fname, format="svg")
        plt.close(fig)
        figure_map["4-4" if target == "Nu" else "4-5"] = fname

    comparison = pd.read_csv(RESULT_DIR / "paper_table8_model_comparison.csv")
    fig, ax = plt.subplots(figsize=(8, 4.5), constrained_layout=True)
    rows = []
    labels_bar = []
    for _, row in comparison.iterrows():
        rows.append(float(row["R2"]))
        labels_bar.append(f"{row['model']}-{row['target']}")
    ax.bar(labels_bar, rows, color=["#2563eb", "#60a5fa", "#16a34a", "#86efac"])
    ax.set_ylabel("R2")
    ax.set_ylim(0.9, 1.0)
    ax.tick_params(axis="x", rotation=18)
    ax.grid(False)
    fig.savefig(FIGURE_DIR / "fig4_6_model_comparison.svg", format="svg")
    plt.close(fig)
    figure_map["4-6"] = "fig4_6_model_comparison.svg"

    with open(RESULT_DIR / "feature_fusion_kfold_5" / "feature_fusion_kfold_summary.json", "r", encoding="utf-8") as f:
        kfold_summary = json.load(f)
    fig, ax = plt.subplots(figsize=(7.5, 4.2), constrained_layout=True)
    metrics = ["Nu_R2", "f_R2", "Nu_MAPE_percent", "f_MAPE_percent"]
    means = [kfold_summary[f"{m}_mean"] for m in metrics]
    stds = [kfold_summary[f"{m}_std"] for m in metrics]
    ax.bar(metrics, means, yerr=stds, capsize=4, color=["#2563eb", "#60a5fa", "#f97316", "#fb923c"])
    ax.set_ylabel("mean with std")
    ax.grid(False)
    fig.savefig(FIGURE_DIR / "fig4_6a_feature_kfold.svg", format="svg")
    plt.close(fig)
    figure_map["4-6a"] = "fig4_6a_feature_kfold.svg"

    # 没有保存真实DE逐代历史时，不编造收敛轨迹，只生成流程型示意图。
    figure_map["4-7"] = flow_svg(
        "fig4_7_de_convergence_schematic.svg",
        ["初始种群", "代理模型\\n快速评价", "选择/变异/交叉", "更新当前\\n最优结构", "COMSOL复核"],
        "差分进化优化过程示意",
    )
    return figure_map


def collect_existing_assets():
    figure_map = {}
    figure_map["2-3"] = copy_asset(PAPER_SVG_DIR / "Fig1_Geometry_Schematic.svg", "fig2_3_parameter_definition.svg")
    figure_map["3-1"] = copy_asset(PAPER_SVG_DIR / "Fig2_Computational_Domain_BC.svg", "fig3_1_2d_domain.svg")
    figure_map["3-3"] = mesh_overall_svg()
    figure_map["3-4"] = mesh_local_svg()
    figure_map["4-1"] = copy_asset(
        PAPER_SVG_DIR / "Fig5_CBAM_DualStream_CNN_Architecture_CN.svg",
        "fig4_1_multimodal_architecture.svg",
    )
    figure_map.update(crop_field_comparison())
    figure_map["5-4"] = "fig5_4_3d_metrics.png"

    conversions = {
        "3-7": ("图 4a.tiff", "fig3_7_velocity_field.png"),
        "3-8": ("图 4b.tiff", "fig3_8_temperature_field.png"),
        "3-9": ("图 4c.tiff", "fig3_9_pressure_field.png"),
    }
    for fig_id, (source_name, target_name) in conversions.items():
        source = SMALL_PAPER_DIR / source_name
        if source.exists():
            figure_map[fig_id] = convert_image(source, target_name)
    return figure_map


def collect_chatgpt_images():
    """Use the user's prepared high-quality PNG illustrations for thesis figures."""
    image_map = {
        "1-1": ("ChatGPT Image 2026年5月26日 16_15_00 (1).png", "fig1_1_engine_cooling_module.png"),
        "2-1": ("ChatGPT Image 2026年5月26日 16_15_00 (2).png", "fig2_1_heat_transfer_path.png"),
        "2-2": ("ChatGPT Image 2026年5月26日 16_15_00 (3).png", "fig2_2_tube_wake_comparison.png"),
        "5-1": ("ChatGPT Image 2026年5月26日 16_15_02 (4).png", "fig5_1_engine_bay_scenario.png"),
        "5-2": ("ChatGPT Image 2026年5月26日 16_15_03 (5).png", "fig5_2_3d_model_schematic.png"),
    }
    figure_map = {}
    for fig_id, (source_name, target_name) in image_map.items():
        source = THESIS_DIR / source_name
        if source.exists():
            figure_map[fig_id] = copy_asset(source, target_name)
    return figure_map


def collect_comsol_pillar_figures():
    export_root = ROOT / "comsol_3d_airfoil_radiator" / "generated_pillar_heat_sink" / "plot_exports"
    fields = {
        "5-6": ("velocity", "fig5_6_3d_velocity_comsol.png", "基准结构  速度场", "二维最优三维化结构  速度场"),
        "5-7": ("temperature", "fig5_7_3d_temperature_comsol.png", "基准结构  温度场", "二维最优三维化结构  温度场"),
        "5-8": ("pressure", "fig5_8_3d_pressure_comsol.png", "基准结构  压力场", "二维最优三维化结构  压力场"),
    }
    figure_map = {}
    for fig_id, (field, output_name, left_label, right_label) in fields.items():
        left = export_root / "baseline" / f"baseline_{field}.png"
        right = export_root / "optimal_2d" / f"optimal_2d_{field}.png"
        if left.exists() and right.exists():
            figure_map[fig_id] = make_side_by_side_comparison(left, right, output_name, left_label, right_label)
    return figure_map


def collect_comsol_mesh_figures():
    export_root = ROOT / "comsol_3d_airfoil_radiator" / "generated_pillar_heat_sink" / "mesh_exports"
    mesh_map = {
        "3-3": ("fig3_3_2d_mesh_overall_comsol.png", "fig3_3_mesh_comsol.png"),
        "3-4": ("fig3_4_2d_mesh_local_comsol.png", "fig3_4_local_mesh_comsol.png"),
        "5-3": ("fig5_3_3d_mesh_wireframe_comsol.png", "fig5_3_3d_mesh_comsol.png"),
    }
    figure_map = {}
    for fig_id, (source_name, target_name) in mesh_map.items():
        source = export_root / source_name
        if source.exists():
            figure_map[fig_id] = copy_asset(source, target_name)
    return figure_map


def generic_figure(fig_id, title):
    safe_id = fig_id.replace("-", "_")
    return flow_svg(
        f"fig{safe_id}_generic.svg",
        ["研究对象", "计算/训练", "结果输出"],
        title,
    )


def replace_placeholders(figure_map):
    text = THESIS_PATH.read_text(encoding="utf-8")

    def figure_repl(match):
        fig_id = match.group(1)
        title = match.group(2).strip()
        file_name = figure_map.get(fig_id)
        if not file_name:
            file_name = generic_figure(fig_id, title)
            figure_map[fig_id] = file_name
        return f"![图{fig_id}  {title}](figures/{file_name})"

    def table_repl(match):
        table_id = match.group(1)
        title = match.group(2).strip()
        return f"**表{table_id}  {title}**"

    text = re.sub(r"^【图(\d+-\d+)\s+([^】]+)】$", figure_repl, text, flags=re.M)
    text = re.sub(r"^【表(\d+-\d+)\s+([^】]+)】$", table_repl, text, flags=re.M)
    # 已经替换过占位符的草稿再次运行时，需要同步更新图件路径。
    for fig_id, file_name in figure_map.items():
        text = re.sub(
            rf"(!\[图{re.escape(fig_id)}(?=\s)[^\]]*\]\()figures/[^)]+(\))",
            rf"\1figures/{file_name}\2",
            text,
        )

    kfold_section = build_kfold_section()
    marker = (
        "| 纯几何MLP | f        | 0.9459 | 0.001024 | 2.570% |\n\n"
        "## 4.5 优化工况与差分进化参数化优化设置"
    )
    if "### 4.4.5 五折交叉验证稳定性分析" not in text and marker in text:
        text = text.replace(
            marker,
            "| 纯几何MLP | f        | 0.9459 | 0.001024 | 2.570% |\n\n"
            + kfold_section
            + "\n## 4.5 优化工况与差分进化参数化优化设置",
        )

    THESIS_PATH.write_text(text, encoding="utf-8")


def build_kfold_section():
    summary_path = RESULT_DIR / "feature_fusion_kfold_5" / "feature_fusion_kfold_summary.json"
    with open(summary_path, "r", encoding="utf-8") as f:
        summary = json.load(f)
    rows = [
        ("Nu", "R²", summary["Nu_R2_mean"], summary["Nu_R2_std"], 4),
        ("Nu", "RMSE", summary["Nu_RMSE_mean"], summary["Nu_RMSE_std"], 4),
        ("Nu", "MAE", summary["Nu_MAE_mean"], summary["Nu_MAE_std"], 4),
        ("Nu", "MAPE/%", summary["Nu_MAPE_percent_mean"], summary["Nu_MAPE_percent_std"], 4),
        ("f", "R²", summary["f_R2_mean"], summary["f_R2_std"], 4),
        ("f", "RMSE", summary["f_RMSE_mean"], summary["f_RMSE_std"], 6),
        ("f", "MAE", summary["f_MAE_mean"], summary["f_MAE_std"], 6),
        ("f", "MAPE/%", summary["f_MAPE_percent_mean"], summary["f_MAPE_percent_std"], 4),
    ]
    table_lines = [
        "| 预测对象 | 指标 | 五折平均值 | 标准差 |",
        "| -------- | ---- | ---------- | ------ |",
    ]
    for target, metric, mean, std, digits in rows:
        table_lines.append(f"| {target} | {metric} | {mean:.{digits}f} | {std:.{digits}f} |")

    return (
        "### 4.4.5 五折交叉验证稳定性分析\n\n"
        "为进一步检验多模态特征融合模型在不同数据划分下的稳定性，本文基于500组CFD样本进行五折交叉验证。"
        "每次将其中4折作为训练集、1折作为验证集，记录Nu和f的预测指标，并统计五折平均值及标准差。"
        "该验证不改变前文固定测试集结果，而用于补充说明模型对样本划分的敏感性。\n\n"
        "![图4-6a  多模态特征融合模型五折交叉验证结果](figures/fig4_6a_feature_kfold.svg)\n\n"
        "**表4-4（续）  多模态特征融合模型五折交叉验证结果**\n\n"
        + "\n".join(table_lines)
        + "\n\n"
        "由表4-4（续）可知，五折交叉验证中Nu预测R²平均值为"
        f"{summary['Nu_R2_mean']:.4f}，f预测R²平均值为{summary['f_R2_mean']:.4f}；"
        f"Nu和f的MAPE平均值分别为{summary['Nu_MAPE_percent_mean']:.4f}%和"
        f"{summary['f_MAPE_percent_mean']:.4f}%。结果表明，在不同训练/验证划分下，"
        "多模态特征融合模型仍保持较稳定的预测能力。\n\n"
    )


def main():
    ensure_dirs()
    figure_map = {}
    figure_map.update(generate_handmade_svgs())
    figure_map.update(collect_chatgpt_images())
    figure_map.update(collect_existing_assets())
    figure_map.update(generate_data_plots())
    figure_map.update(collect_comsol_mesh_figures())
    figure_map.update(collect_comsol_pillar_figures())
    replace_placeholders(figure_map)
    print(f"[INFO] Prepared {len(figure_map)} figure references in {FIGURE_DIR}")
    print(f"[INFO] Updated thesis: {THESIS_PATH}")


if __name__ == "__main__":
    main()
