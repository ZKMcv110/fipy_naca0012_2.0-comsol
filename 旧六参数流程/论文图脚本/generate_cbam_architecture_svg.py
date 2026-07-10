#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Generate an editable Chinese SVG architecture diagram for the CBAM dual-stream CNN."""

from __future__ import annotations

import base64
import html
import os
from io import BytesIO

from PIL import Image


OUT_DIR = "paper_figures_svg"
OUT_FILE = os.path.join(OUT_DIR, "Fig5_CBAM_DualStream_CNN_Architecture_CN.svg")
CASE_DIR = os.path.join("new_model_runs", "optimal")

W, H = 1600, 1080

BLUE = "#1f5fd0"
BLUE_DARK = "#083b91"
BLUE_LIGHT = "#eef5ff"
BLUE_FILL = "#fbfdff"
GREEN = "#4a8a34"
GREEN_DARK = "#1f6b25"
GREEN_LIGHT = "#f2fbef"
ORANGE = "#f07a22"
ORANGE_DARK = "#d9480f"
ORANGE_LIGHT = "#fff4ea"
RED = "#d92323"
RED_LIGHT = "#fff4f2"
PURPLE = "#7c43bd"
PURPLE_LIGHT = "#f7f0ff"
INK = "#111827"
MUTED = "#5f6b7a"
WHITE = "#ffffff"


T = {
    "input": "输入（多模态）",
    "velocity": "速度场云图",
    "temperature": "温度场云图",
    "pressure": "压力场云图",
    "params6": "6 维几何参数",
    "visual_title": "视觉流：物理场图像编码（CNN主干 + CBAM）",
    "param_title": "参数流：几何参数编码（MLP）",
    "attention": "注意力模块",
    "channel": "通道注意力",
    "spatial": "空间注意力",
    "gap": "全局平均池化",
    "visual_vec": "视觉特征向量",
    "dim": "维度",
    "embed": "参数嵌入",
    "geo_vec": "几何特征向量",
    "concat": "特征拼接",
    "fusion": "融合全连接层",
    "output": "联合回归输出",
    "continuous": "连续值",
    "nu": "努塞尔数",
    "friction": "阻力系数",
    "out_dim": "输出维度：2",
    "in_dim": "输入维度：6",
    "out_ch": "输出通道",
    "relu": "ReLU",
    "dropout": "ReLU + Dropout",
}


PARAM_LINES = [
    "Ta   弯度系数",
    "Twa  最大弯位",
    "Tb   厚度系数",
    "Ts   横向间距",
    "Tt   纵向间距",
    "Tad  交错位移",
]


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def tag(name: str, attrs: dict[str, object] | None = None, content: str | None = None) -> str:
    attrs = attrs or {}
    attr_text = " ".join(f'{k}="{esc(v)}"' for k, v in attrs.items() if v is not None)
    if content is None:
        return f"<{name} {attr_text}/>"
    return f"<{name} {attr_text}>{content}</{name}>"


def text(
    x: float,
    y: float,
    body: str,
    size: int = 22,
    fill: str = INK,
    weight: str = "400",
    anchor: str = "middle",
    style: str = "",
) -> str:
    return (
        f'<text x="{x}" y="{y}" fill="{fill}" font-size="{size}" '
        f'font-weight="{weight}" text-anchor="{anchor}" {style}>{esc(body)}</text>'
    )


def lines(
    x: float,
    y: float,
    rows: list[str],
    size: int = 20,
    fill: str = INK,
    weight: str = "400",
    anchor: str = "middle",
    gap: int = 28,
) -> str:
    return "\n".join(
        text(x, y + i * gap, row, size=size, fill=fill, weight=weight, anchor=anchor)
        for i, row in enumerate(rows)
    )


def rounded(
    x: float,
    y: float,
    w: float,
    h: float,
    stroke: str,
    fill: str = WHITE,
    width: float = 2,
    r: float = 14,
    dash: str | None = None,
) -> str:
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" ry="{r}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="{width}"{dash_attr}/>'
    )


def arrow(x1: float, y1: float, x2: float, y2: float, color: str = BLUE_DARK, width: float = 2.8) -> str:
    return (
        f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
        f'stroke="{color}" stroke-width="{width}" marker-end="url(#arrow)"/>'
    )


def elbow(points: list[tuple[float, float]], color: str = BLUE_DARK, width: float = 2.8) -> str:
    p = " ".join(f"{x},{y}" for x, y in points)
    return f'<polyline points="{p}" fill="none" stroke="{color}" stroke-width="{width}" marker-end="url(#arrow)"/>'


def data_uri(path: str, max_size: tuple[int, int] = (172, 112)) -> str | None:
    if not os.path.exists(path):
        return None
    img = Image.open(path).convert("RGB")
    img.thumbnail(max_size, Image.LANCZOS)
    canvas = Image.new("RGB", max_size, "white")
    canvas.paste(img, ((max_size[0] - img.width) // 2, (max_size[1] - img.height) // 2))
    buf = BytesIO()
    canvas.save(buf, format="JPEG", quality=88)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def image_box(x: float, y: float, label: str, file_name: str) -> str:
    uri = data_uri(os.path.join(CASE_DIR, file_name))
    out = [text(x + 86, y, label, size=21, fill=INK, weight="700")]
    if uri:
        out.append(tag("image", {"x": x, "y": y + 18, "width": 172, "height": 112, "href": uri}))
    else:
        out.append(rounded(x, y + 18, 172, 112, stroke=BLUE, fill=BLUE_LIGHT, width=1, r=4))
        out.append(text(x + 86, y + 80, file_name, size=13, fill=MUTED))
    return "\n".join(out)


def cube_stack(x: float, y: float, scale: float = 1.0, color: str = "#8fc4f8") -> str:
    w, h, d = 54 * scale, 94 * scale, 32 * scale
    out: list[str] = []
    for i, opacity in enumerate([1.0, 0.88, 0.76]):
        dx, dy = i * 36 * scale, i * 26 * scale
        out.append(
            f'<polygon points="{x+dx},{y+dy} {x+dx+w},{y+dy} {x+dx+w+d},{y+dy-d} {x+dx+d},{y+dy-d}" '
            f'fill="{color}" opacity="{opacity}" stroke="#174577" stroke-width="2"/>'
        )
        out.append(
            f'<polygon points="{x+dx+w},{y+dy} {x+dx+w+d},{y+dy-d} {x+dx+w+d},{y+dy+h-d} {x+dx+w},{y+dy+h}" '
            f'fill="#4f8cc8" opacity="{opacity}" stroke="#174577" stroke-width="2"/>'
        )
        out.append(
            f'<rect x="{x+dx}" y="{y+dy}" width="{w}" height="{h}" '
            f'fill="{color}" opacity="{opacity}" stroke="#174577" stroke-width="2"/>'
        )
    return "\n".join(out)


def dot_vector(x: float, y: float, color: str, w: float = 54, h: float = 150, n: int = 5) -> str:
    out = [rounded(x, y, w, h, stroke=color, fill=WHITE, width=2, r=22)]
    for i in range(n):
        cy = y + 24 + i * ((h - 48) / max(1, n - 1))
        radius = 7 if i in (0, 1, n - 1) else 3
        out.append(f'<circle cx="{x+w/2}" cy="{cy}" r="{radius}" fill="{color}"/>')
    return "\n".join(out)


def small_bars(x: float, y: float) -> str:
    heights = [42, 28, 24, 36, 18, 25]
    out: list[str] = []
    for i, h in enumerate(heights):
        out.append(
            f'<rect x="{x+i*21}" y="{y+48-h}" width="13" height="{h}" '
            f'fill="#ff755c" stroke="#9c1d16" stroke-width="1"/>'
        )
    return "\n".join(out)


def small_grid(x: float, y: float, color: str = "#b37ae8") -> str:
    out: list[str] = []
    for r in range(4):
        for c in range(4):
            alpha = 0.95 if (r + c) % 3 == 0 else 0.55
            out.append(
                f'<rect x="{x+c*17}" y="{y+r*17}" width="14" height="14" '
                f'fill="{color}" opacity="{alpha}" stroke="#5a238c" stroke-width="1"/>'
            )
    return "\n".join(out)


def feature_row(x: float, y: float, color: str, n: int = 6) -> str:
    out = [rounded(x, y, 132, 34, stroke=color, fill=WHITE, width=2, r=10)]
    for i in range(n):
        out.append(f'<circle cx="{x+20+i*19}" cy="{y+17}" r="7" fill="{color}"/>')
    out.append(text(x + 118, y + 22, "...", size=22, fill=INK, weight="700"))
    return "\n".join(out)


def conv_block(x: float, y: float, title: str, channels: int, color: str) -> str:
    return "\n".join(
        [
            rounded(x, y, 158, 380, stroke=BLUE, fill=WHITE, width=2, r=14),
            text(x + 79, y + 36, title, size=21, fill=INK, weight="700"),
            cube_stack(x + 35, y + 118, scale=0.84, color=color),
            lines(x + 79, y + 255, ["卷积 + BN", "+ ReLU + 池化"], size=19, fill=INK, weight="500", gap=27),
            text(x + 79, y + 350, f"{T['out_ch']}： {channels}", size=18, fill=INK),
        ]
    )


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    svg: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
        "<defs>",
        '<marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto" markerUnits="strokeWidth">',
        '<path d="M1.5,1.5 L7,4 L1.5,6.5 z" fill="#083b91"/>',
        "</marker>",
        '<filter id="shadow" x="-8%" y="-8%" width="116%" height="116%">',
        '<feDropShadow dx="0" dy="2" stdDeviation="3" flood-color="#9aa8bd" flood-opacity="0.25"/>',
        "</filter>",
        "<style><![CDATA[",
        'text{font-family:"Microsoft YaHei","SimHei","Noto Sans CJK SC",Arial,sans-serif;}',
        ".panel{filter:url(#shadow)}",
        "]]></style>",
        "</defs>",
        f'<rect width="{W}" height="{H}" fill="{WHITE}"/>',
    ]

    # Left multimodal input panel
    svg.append(tag("g", {"class": "panel"}, rounded(24, 34, 228, 990, stroke=BLUE, fill=BLUE_FILL, width=2, r=18)))
    svg.append(text(138, 80, T["input"], size=27, fill=BLUE_DARK, weight="700"))
    svg.append(rounded(36, 106, 204, 565, stroke=BLUE, fill=WHITE, width=2, r=12))
    svg.append(image_box(52, 148, T["velocity"], "velocity_magnitude.png"))
    svg.append(image_box(52, 318, T["temperature"], "temperature.png"))
    svg.append(image_box(52, 488, T["pressure"], "pressure.png"))
    svg.append(text(138, 642, "...", size=34, fill=INK, weight="700"))
    svg.append(rounded(36, 704, 204, 240, stroke=GREEN, fill=GREEN_LIGHT, width=2, r=12))
    svg.append(text(138, 748, T["params6"], size=25, fill=GREEN_DARK, weight="700"))
    svg.append(lines(63, 790, ["• " + s for s in PARAM_LINES], size=18, fill=INK, anchor="start", gap=26))

    # Visual stream panel
    svg.append(rounded(285, 34, 1290, 560, stroke=BLUE, fill=BLUE_FILL, width=2, r=18))
    svg.append(f'<rect x="285" y="34" width="1290" height="64" fill="{BLUE_LIGHT}" stroke="{BLUE}" stroke-width="2"/>')
    svg.append(text(930, 76, T["visual_title"], size=29, fill=BLUE_DARK, weight="700"))
    svg.append(
        text(
            930,
            562,
            "物理场图像特征：尾流速度亏损 + 热尾迹扩展 + 压力梯度/局部压降扰动",
            size=21,
            fill=BLUE_DARK,
            weight="700",
        )
    )
    svg.append(arrow(252, 330, 304, 330))

    block_specs = [
        (320, "卷积块 1", 32, "#b9dcff"),
        (505, "卷积块 2", 64, "#8fc4f8"),
        (690, "卷积块 3", 128, "#2f75bd"),
        (1070, "卷积块 4", 256, "#1c5da7"),
    ]
    for x, title, channels, color in block_specs:
        svg.append(conv_block(x, 135, title, channels, color))
    svg.append(arrow(478, 330, 505, 330, color=INK))
    svg.append(arrow(663, 330, 690, 330, color=INK))
    svg.append(arrow(848, 330, 878, 330, color=INK))

    # CBAM module
    svg.append(rounded(878, 114, 170, 430, stroke=RED, fill=WHITE, width=2, r=14, dash="8 5"))
    svg.append(text(963, 154, "CBAM", size=29, fill=RED, weight="700"))
    svg.append(text(963, 189, T["attention"], size=23, fill=RED, weight="700"))

    # Channel Attention box
    svg.append(rounded(889, 216, 148, 136, stroke=RED, fill=RED_LIGHT, width=2, r=10))
    svg.append(lines(963, 248, [T["channel"], "(Channel Attention)"], size=15, fill=INK, weight="600", gap=23))
    svg.append(small_bars(908, 296))
    svg.append(text(963, 380, "×", size=25, fill=INK, weight="700"))

    # Spatial Attention box
    svg.append(rounded(889, 395, 148, 145, stroke=RED, fill=RED_LIGHT, width=2, r=10))
    svg.append(lines(963, 425, [T["spatial"], "(Spatial Attention)"], size=14, fill=INK, weight="600", gap=22))
    svg.append(small_grid(925, 472))
    svg.append(arrow(1048, 330, 1070, 330, color=INK))

    # GAP and visual vector
    svg.append(arrow(1228, 330, 1264, 330))
    svg.append(rounded(1264, 221, 136, 248, stroke=BLUE, fill=WHITE, width=2, r=14))
    svg.append(lines(1332, 272, [T["gap"], "(GAP)"], size=21, fill=INK, weight="700", gap=31))
    svg.append(small_grid(1300, 330, color="#d9e6ff"))
    svg.append(text(1332, 442, "...", size=32, fill=INK, weight="700"))
    svg.append(arrow(1400, 330, 1470, 330))
    svg.append(dot_vector(1470, 286, BLUE_DARK, w=66, h=208, n=6))
    svg.append(lines(1503, 250, [T["visual_vec"], "d_v"], size=21, fill=INK, weight="700", gap=31))
    svg.append(text(1503, 526, f"{T['dim']}： D_v", size=19, fill=INK))

    # Parameter stream panel
    svg.append(rounded(285, 660, 630, 280, stroke=GREEN, fill="#fbfffb", width=2, r=18))
    svg.append(f'<rect x="285" y="660" width="630" height="55" fill="{GREEN_LIGHT}" stroke="{GREEN}" stroke-width="2"/>')
    svg.append(text(600, 696, T["param_title"], size=27, fill=GREEN_DARK, weight="700"))
    svg.append(arrow(252, 805, 304, 805, color=GREEN, width=3))
    scalar_specs = [
        (315, [T["embed"]], T["in_dim"]),
        (465, ["全连接 1", "（128）"], T["relu"]),
        (615, ["全连接 2", "（128）"], T["relu"]),
        (765, [T["geo_vec"], "d_g"], f"{T['dim']}： D_g"),
    ]
    for x, title_rows, foot in scalar_specs:
        svg.append(rounded(x, 740, 110, 160, stroke=GREEN, fill=WHITE, width=2, r=12))
        svg.append(lines(x + 55, 775, title_rows, size=18, fill=INK, weight="700", gap=24))
        svg.append(dot_vector(x + 37, 815, GREEN, w=38, h=86, n=4))
        svg.append(text(x + 55, 928, foot, size=18, fill=INK))
    svg.append(arrow(425, 815, 465, 815, color=GREEN))
    svg.append(arrow(575, 815, 615, 815, color=GREEN))
    svg.append(arrow(725, 815, 765, 815, color=GREEN))

    # Fusion stage
    svg.append(elbow([(1332, 469), (1332, 630), (1030, 630), (1030, 720)], color=BLUE_DARK, width=2.6))
    svg.append(elbow([(875, 815), (910, 815), (910, 885), (945, 885)], color=GREEN, width=2.6))
    svg.append(rounded(945, 720, 170, 240, stroke=ORANGE, fill=WHITE, width=2, r=14))
    svg.append(lines(1030, 770, [T["concat"], "（拼接）"], size=21, fill=INK, weight="700", gap=30))
    svg.append(feature_row(964, 814, BLUE_DARK, n=6))
    svg.append(feature_row(964, 868, GREEN, n=6))
    svg.append(text(1030, 930, f"{T['dim']}： D_v + D_g", size=18, fill=INK))
    svg.append(arrow(1115, 820, 1165, 820, color=INK))

    svg.append(rounded(1165, 675, 205, 345, stroke=ORANGE, fill=ORANGE_LIGHT, width=2, r=14))
    svg.append(text(1268, 715, T["fusion"], size=24, fill=ORANGE_DARK, weight="700"))
    for i, (y0, title_rows) in enumerate([
        (740, ["融合全连接 1", "（256）"]),
        (875, ["融合全连接 2", "（128）"]),
    ]):
        svg.append(rounded(1192, y0, 150, 105, stroke=ORANGE, fill=WHITE, width=2, r=10))
        svg.append(lines(1267, y0 + 28, title_rows, size=18, fill=INK, weight="500", gap=23))
        svg.append(feature_row(1201, y0 + 62, ORANGE, n=6))
        if i == 0:
            svg.append(text(1268, 865, T["dropout"], size=16, fill=INK))
    svg.append(text(1268, 1000, T["dropout"], size=16, fill=INK))

    # Joint regression output
    svg.append(rounded(1415, 675, 160, 345, stroke=PURPLE, fill=PURPLE_LIGHT, width=2, r=14))
    svg.append(lines(1495, 720, [T["output"], f"({T['continuous']})"], size=21, fill="#5c2a9d", weight="700", gap=30))
    svg.append(f'<circle cx="1495" cy="805" r="52" fill="#f7fbff" stroke="{BLUE}" stroke-width="2"/>')
    svg.append(lines(1495, 794, ["Nu", f"({T['nu']})"], size=21, fill=BLUE_DARK, weight="700", gap=27))
    svg.append(f'<circle cx="1495" cy="930" r="52" fill="#fffafa" stroke="{RED}" stroke-width="2"/>')
    svg.append(lines(1495, 919, ["f", f"({T['friction']})"], size=21, fill=RED, weight="700", gap=27))
    svg.append(text(1495, 1008, T["out_dim"], size=19, fill=INK))
    svg.append(arrow(1370, 805, 1442, 805, color=INK))
    svg.append(arrow(1370, 930, 1442, 930, color=INK))

    svg.append("</svg>")

    with open(OUT_FILE, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(svg))
    print(f"Saved {OUT_FILE}")


if __name__ == "__main__":
    main()