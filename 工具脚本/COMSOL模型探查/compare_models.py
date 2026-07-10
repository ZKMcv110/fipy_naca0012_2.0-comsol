#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对比 COMSOL 官方案例与项目三维模型
"""

import zipfile
import re
from pathlib import Path

def extract_plate_fin_info():
    """提取 plate_fin_heat_exchanger.mph 的关键信息"""
    
    print("="*80)
    print("COMSOL 官方案例: plate_fin_heat_exchanger.mph")
    print("="*80)
    
    z = zipfile.ZipFile(r'大论文初稿\plate_fin_heat_exchanger.mph')
    content = z.read('dmodel.xml').decode('utf-8', errors='ignore')
    
    # 1. 模型基本信息
    print("\n【1. 模型基本信息】")
    model_name = re.search(r'name="([^"]+)"', content)
    if model_name:
        print(f"  模型名称: {model_name.group(1)}")
    
    comsol_ver = re.search(r'<comsolVersion[^>]*>([^<]+)</comsolVersion>', content)
    if comsol_ver:
        print(f"  COMSOL版本: {comsol_ver.group(1)}")
    
    model_title = re.search(r'<modelTitle[^>]*>([^<]+)</modelTitle>', content)
    if model_title:
        print(f"  模型标题: {model_title.group(1)}")
    
    # 2. 全局参数
    print("\n【2. 关键几何参数】")
    params = re.findall(r'<expressions[^>]*name="([^"]+)"[^>]*expr="([^"]*)"[^>]*descr="([^"]*)"', content)
    
    geom_params = {
        'L_he': '换热器长度',
        'W_he': '换热器宽度', 
        'H_he': '换热器高度',
        'Nu': '排数',
        'hplate': '油板高度',
        'hfin': '翅片高度',
        'dist_sep': '翅片间距',
        'Nb_sep': '每排翅片数',
        'fin_th': '翅片厚度',
        'r0': '进出口半径',
        'w_casing': '外壳厚度'
    }
    
    for name, expr, descr in params:
        if name in geom_params:
            print(f"  {geom_params[name]:15s}: {expr:20s} ({descr})")
    
    print("\n【3. 操作参数】")
    op_params = {
        'Th': '热油入口温度',
        'Tc': '冷空气入口温度',
        'V0': '油入口流量',
        'u0': '油入口速度',
        'uacfm': '空气入口流量(cfm)',
        'ua_v': '空气入口速度',
        'ua': '初始空气速度',
        'Re_oil': '油入口雷诺数'
    }
    
    for name, expr, descr in params:
        if name in op_params:
            print(f"  {op_params[name]:15s}: {expr:20s} ({descr})")
    
    # 3. 材料
    print("\n【4. 材料】")
    # 查找材料定义区域
    mat_section = re.search(r'<MaterialList.*?</MaterialList>', content, re.DOTALL)
    if mat_section:
        mat_text = mat_section.group(0)
        materials = re.findall(r'<material[^>]*tag="([^"]+)"[^>]*label="([^"]*)"', mat_text)
        for tag, label in materials:
            print(f"  - {tag}: {label if label else '(未命名)'}")
    
    # 4. 物理场
    print("\n【5. 物理场接口】")
    phys_section = re.search(r'<PhysicsList.*?</PhysicsList>', content, re.DOTALL)
    if phys_section:
        phys_text = phys_section.group(0)
        physics = re.findall(r'<physics[^>]*tag="([^"]+)"[^>]*interface="([^"]+)"', phys_text)
        for tag, interface in physics:
            print(f"  - {tag}: {interface}")
    
    # 5. 研究步骤
    print("\n【6. 研究步骤】")
    study_section = re.search(r'<StudyList.*?</StudyList>', content, re.DOTALL)
    if study_section:
        study_text = study_section.group(0)
        studies = re.findall(r'<studyStep[^>]*type="([^"]+)"[^>]*label="([^"]*)"', study_text)
        for stype, label in studies:
            print(f"  - {stype}: {label if label else '(未命名)'}")
    
    # 6. 维度信息
    print("\n【7. 模型维度】")
    dim_pattern = r'dim="(\d+)"'
    dims = re.findall(dim_pattern, content)
    dim_counts = {}
    for d in dims:
        dim_counts[d] = dim_counts.get(d, 0) + 1
    
    for dim, count in sorted(dim_counts.items()):
        dim_name = {0: '点', 1: '边', 2: '面', 3: '体'}.get(int(dim), f'{dim}维')
        print(f"  {dim_name} ({dim}D): {count:4d} 处引用")
    
    has_3d = '3' in dim_counts
    print(f"\n  => 模型类型: {'三维 (3D)' if has_3d else '二维 (2D)'}")


def compare_with_project():
    """与项目现有三维模型对比"""
    
    print("\n\n" + "="*80)
    print("对比分析: 官方案例 vs 项目三维翼型管散热器")
    print("="*80)
    
    print("""
┌─────────────────────┬──────────────────────────┬──────────────────────────┐
│     对比项          │  官方案例                │  项目模型                │
│                     │  (plate_fin)             │  (airfoil_pillar)        │
├─────────────────────┼──────────────────────────┼──────────────────────────┤
│ 应用场景            │ 平板翅片换热器           │ 翼型柱阵列散热器         │
│                     │ (油-空气换热)            │ (强制风冷芯片散热)       │
├─────────────────────┼──────────────────────────┼──────────────────────────┤
│ 几何结构            │ 多层平行平板翅片         │ NACA翼型柱3×8阵列        │
│                     │ 周期性排列               │ 交错/基准两种构型        │
├─────────────────────┼──────────────────────────┼──────────────────────────┤
│ 计算域尺寸          │ L_he=Nb_sep*dist_sep     │ 70mm × 30mm × 15mm      │
│                     │ W_he=77mm                │ (长×宽×高)              │
│                     │ H_he=Nu*h_row            │                          │
│                     │ ≈225mm × 77mm × 96mm     │                          │
├─────────────────────┼──────────────────────────┼──────────────────────────┤
│ 热源设置            │ 底部油道加热             │ 芯片域体积热源           │
│                     │ Th=70°C                  │ P0=1W (总功率)          │
│                     │ Tc=20°C                  │ qv=1e7 W/m³             │
├─────────────────────┼──────────────────────────┼──────────────────────────┤
│ 流体介质            │ 双流体: Engine Oil + Air │ 单流体: Air              │
│                     │ 油侧 + 空气侧            │ 仅空气强制对流           │
├─────────────────────┼──────────────────────────┼──────────────────────────┤
│ 流速/流量           │ 油: V0=1 gal/min         │ u_in=5 m/s (或5 cm/s)   │
│                     │ 空气: uacfm=100 cfm      │ 充分发展入口             │
├─────────────────────┼──────────────────────────┼──────────────────────────┤
│ 物理场              │ 层流 + 传热              │ 层流 + 传热              │
│                     │ Nonisothermal Flow       │ Nonisothermal Flow       │
├─────────────────────┼──────────────────────────┼──────────────────────────┤
│ 边界条件            │ 入口: 速度+温度          │ 入口: 速度+温度          │
│                     │ 出口: 压力出口           │ 出口: 压力出口           │
│                     │ 对称边界                 │ 上下/前后对称            │
├─────────────────────┼──────────────────────────┼──────────────────────────┤
│ 材料                │ Aluminum, Engine Oil,    │ Aluminum, Air            │
│                     │ Air, Casing              │                          │
├─────────────────────┼──────────────────────────┼──────────────────────────┤
│ 求解类型            │ Stationary (稳态)        │ Stationary (稳态)        │
├─────────────────────┼──────────────────────────┼──────────────────────────┤
│ 后处理指标          │ 换热量、压降、效率       │ T_chip,max, R_th, Δp, η  │
└─────────────────────┴──────────────────────────┴──────────────────────────┘
""")
    
    print("\n【关键差异总结】")
    print("""
1. 应用目标不同:
   - 官方案例: 传统板式换热器设计，关注油-空气间的热交换效率
   - 项目模型: 电子芯片强制风冷散热，关注芯片温度和系统热阻

2. 几何复杂度:
   - 官方案例: 规则平行板结构，参数化程度高（翅片数、间距、高度）
   - 项目模型: NACA翼型曲面，需要解析函数生成，具有空气动力学优化空间

3. 流动特征:
   - 官方案例: 双通道流动（油道+空气道），两侧都有对流换热
   - 项目模型: 单侧空气强制对流，固体导热为主

4. 参数化策略:
   - 官方案例: 基于工程经验公式的几何参数（翅片数、间距等）
   - 项目模型: 基于翼型拓扑参数（Ta, Twa, Tb, Ts, Tt, Tad）

5. 可借鉴之处:
   ✓ 官方案例的多重网格策略（mesh1-mesh4）可用于网格无关性验证
   ✓ 官方案例的参数分组管理（par2组）可参考用于参数组织
   ✓ 官方案例的外壳建模思路可用于完善项目模型的边界封闭
   ✗ 官方案例的双流体耦合不适用于当前单流体场景
   ✗ 官方案例的周期性边界条件不完全适用于有限阵列
    """)


if __name__ == "__main__":
    extract_plate_fin_info()
    compare_with_project()
