#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""通过解析 XML 提取 COMSOL MPH 文件的关键信息"""

import xml.etree.ElementTree as ET
from pathlib import Path
import re

def extract_mph_info(mph_path: str):
    """从 MPH 文件中提取关键信息"""
    
    print(f"[INFO] 正在解析: {mph_path}")
    
    # MPH 文件是 ZIP 压缩的 XML，但我们可以尝试直接读取其中的文本内容
    try:
        with open(mph_path, 'rb') as f:
            content = f.read()
            
        # 查找关键的 XML 标签
        text_content = content.decode('utf-8', errors='ignore')
        
        print("\n" + "="*60)
        print("模型基本信息")
        print("="*60)
        
        # 提取模型名称
        model_match = re.search(r'<MODEL[^>]*label="([^"]+)"', text_content)
        if model_match:
            print(f"模型标签: {model_match.group(1)}")
        
        # 提取参数
        print("\n" + "="*60)
        print("全局参数 (Parameters)")
        print("="*60)
        param_pattern = r'<PARAMETER[^>]*name="([^"]+)"[^>]*expr="([^"]*)"'
        params = re.findall(param_pattern, text_content)
        for name, expr in params[:20]:  # 只显示前20个
            print(f"  {name} = {expr}")
        if len(params) > 20:
            print(f"  ... 共 {len(params)} 个参数")
        
        # 提取材料
        print("\n" + "="*60)
        print("材料 (Materials)")
        print("="*60)
        mat_pattern = r'<MATERIAL[^>]*label="([^"]*)"[^>]*tag="([^"]*)"'
        materials = re.findall(mat_pattern, text_content)
        for label, tag in materials:
            print(f"  - {tag}: {label if label else '(未命名)'}")
        
        # 提取物理场
        print("\n" + "="*60)
        print("物理场接口 (Physics Interfaces)")
        print("="*60)
        phys_pattern = r'<PHYSICS[^>]*interface="([^"]+)"[^>]*label="([^"]*)"'
        physics = re.findall(phys_pattern, text_content)
        for interface, label in physics:
            print(f"  - {interface}: {label if label else '(未命名)'}")
        
        # 提取几何特征类型
        print("\n" + "="*60)
        print("几何特征 (Geometry Features)")
        print("="*60)
        geom_pattern = r'<GEOMFEATURE[^>]*type="([^"]+)"[^>]*label="([^"]*)"'
        geoms = re.findall(geom_pattern, text_content)
        for gtype, label in geoms:
            print(f"  - {gtype}: {label if label else '(未命名)'}")
        
        # 提取研究步骤
        print("\n" + "="*60)
        print("研究步骤 (Study Steps)")
        print("="*60)
        study_pattern = r'<STUDYSTEP[^>]*type="([^"]+)"[^>]*label="([^"]*)"'
        studies = re.findall(study_pattern, text_content)
        for stype, label in studies:
            print(f"  - {stype}: {label if label else '(未命名)'}")
        
        # 提取边界条件类型
        print("\n" + "="*60)
        print("边界条件类型 (Boundary Conditions)")
        print("="*60)
        bc_pattern = r'<BC[^>]*type="([^"]+)"[^>]*label="([^"]*)"'
        bcs = re.findall(bc_pattern, text_content)
        bc_types = set([bc[0] for bc in bcs])
        for bc_type in sorted(bc_types):
            count = sum(1 for bc in bcs if bc[0] == bc_type)
            print(f"  - {bc_type}: {count} 个")
        
        # 统计域数量
        print("\n" + "="*60)
        print("域选择统计")
        print("="*60)
        domain_pattern = r'<SELECTION[^>]*entitydim="3"[^>]*/>'
        domains = re.findall(domain_pattern, text_content)
        print(f"  三维域选择数量: {len(domains)}")
        
        boundary_pattern = r'<SELECTION[^>]*entitydim="2"[^>]*/>'
        boundaries = re.findall(boundary_pattern, text_content)
        print(f"  二维边界选择数量: {len(boundaries)}")
        
    except Exception as e:
        print(f"[ERROR] 解析失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    mph_path = r"f:\pyProject\fipy_naca0012_2.0\大论文初稿\plate_fin_heat_exchanger.mph"
    extract_mph_info(mph_path)
