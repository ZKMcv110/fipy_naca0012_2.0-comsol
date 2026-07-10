#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""详细分析 COMSOL 官方案例 plate_fin_heat_exchanger.mph"""

import zipfile
import re
from pathlib import Path

def detailed_analysis(mph_path: str):
    """详细分析 MPH 文件"""
    
    print(f"[INFO] 正在详细解析: {mph_path}\n")
    
    try:
        with zipfile.ZipFile(mph_path, 'r') as zip_ref:
            xml_file = 'dmodel.xml'
            
            with zip_ref.open(xml_file) as f:
                content = f.read().decode('utf-8', errors='ignore')
            
            # 1. 提取所有参数
            print("="*60)
            print("1. 全局参数 (Parameters)")
            print("="*60)
            
            param_pattern = r'<parameter\s+name="([^"]+)"\s+expr="([^"]*)"'
            params = re.findall(param_pattern, content)
            for name, expr in params[:40]:
                print(f"  {name:30s} = {expr}")
            if len(params) > 40:
                print(f"  ... 共 {len(params)} 个参数\n")
            
            # 2. 材料信息
            print("\n" + "="*60)
            print("2. 材料 (Materials)")
            print("="*60)
            
            mat_pattern = r'<material\s+tag="([^"]+)"[^>]*label="([^"]*)"'
            materials = re.findall(mat_pattern, content)
            for tag, label in materials:
                print(f"  - {tag}: {label if label else '(未命名)'}")
            
            # 3. 物理场接口
            print("\n" + "="*60)
            print("3. 物理场接口 (Physics Interfaces)")
            print("="*60)
            
            phys_pattern = r'<physics\s+tag="([^"]+)"[^>]*interface="([^"]+)"'
            physics = re.findall(phys_pattern, content)
            for tag, interface in physics:
                print(f"  - {tag}: {interface}")
            
            # 4. 几何特征统计
            print("\n" + "="*60)
            print("4. 几何特征类型统计")
            print("="*60)
            
            geom_type_pattern = r'<feature\s+type="([^"]+)"'
            geom_types = re.findall(geom_type_pattern, content)
            type_counts = {}
            for gtype in geom_types:
                type_counts[gtype] = type_counts.get(gtype, 0) + 1
            
            for gtype, count in sorted(type_counts.items(), key=lambda x: -x[1]):
                print(f"  - {gtype:40s}: {count} 个")
            
            # 5. 研究步骤
            print("\n" + "="*60)
            print("5. 研究步骤 (Study Steps)")
            print("="*60)
            
            study_pattern = r'<studyStep\s+type="([^"]+)"[^>]*label="([^"]*)"'
            studies = re.findall(study_pattern, content)
            for stype, label in studies:
                print(f"  - {stype:30s}: {label if label else '(未命名)'}")
            
            # 6. 关键边界条件
            print("\n" + "="*60)
            print("6. 关键边界条件特征")
            print("="*60)
            
            bc_keywords = ['Inlet', 'Outlet', 'Wall', 'Symmetry', 'Temperature', 
                          'HeatSource', 'Pressure', 'Velocity', 'ThermalInsulation',
                          'ConvectiveOutflow', 'InitialValues', 'NoSlip']
            
            for keyword in bc_keywords:
                pattern = rf'<feature\s+[^>]*type="[^"]*{keyword}[^"]*"[^>]*/>'
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    print(f"\n  [{keyword}] 找到 {len(matches)} 个:")
                    for m in matches[:3]:
                        # 提取 label
                        label_match = re.search(r'label="([^"]*)"', m)
                        if label_match:
                            print(f"    - {label_match.group(1)}")
            
            # 7. 模型维度确认
            print("\n" + "="*60)
            print("7. 模型维度信息")
            print("="*60)
            
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
            
            # 8. 保存部分XML内容供进一步分析
            print("\n" + "="*60)
            print("8. XML 结构摘要")
            print("="*60)
            
            # 查找主要节点
            main_tags = re.findall(r'<([A-Z]+)\s[^>]*>', content)
            tag_counts = {}
            for tag in main_tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
            
            print("  主要 XML 标签统计:")
            for tag, count in sorted(tag_counts.items(), key=lambda x: -x[1])[:15]:
                print(f"    - {tag:30s}: {count}")
            
    except Exception as e:
        print(f"[ERROR] 解析失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    mph_path = r"f:\pyProject\fipy_naca0012_2.0\大论文初稿\plate_fin_heat_exchanger.mph"
    detailed_analysis(mph_path)
