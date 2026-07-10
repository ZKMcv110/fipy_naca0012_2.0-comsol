#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""通过解压 MPH 文件提取 COMSOL 模型信息"""

import zipfile
import re
from pathlib import Path

def extract_mph_info(mph_path: str):
    """从 MPH ZIP 文件中提取关键信息"""
    
    print(f"[INFO] 正在解析: {mph_path}")
    
    try:
        # MPH 文件实际上是 ZIP 格式
        with zipfile.ZipFile(mph_path, 'r') as zip_ref:
            # 列出所有文件
            file_list = zip_ref.namelist()
            print(f"\n[INFO] MPH 文件包含 {len(file_list)} 个文件")
            
            # 查找主要的 model.xml 文件
            model_files = [f for f in file_list if 'model.xml' in f or 'model0.xml' in f]
            
            if not model_files:
                print("[WARN] 未找到 model.xml 文件")
                print("文件列表前20项:")
                for f in file_list[:20]:
                    print(f"  - {f}")
                return
            
            # 读取第一个 model.xml
            xml_file = model_files[0]
            print(f"\n[INFO] 读取: {xml_file}")
            
            with zip_ref.open(xml_file) as f:
                content = f.read().decode('utf-8', errors='ignore')
            
            print("\n" + "="*60)
            print("全局参数 (Parameters)")
            print("="*60)
            param_pattern = r'<parameter[^>]*name="([^"]+)"[^>]*expr="([^"]*)"'
            params = re.findall(param_pattern, content, re.IGNORECASE)
            for name, expr in params[:30]:
                print(f"  {name} = {expr}")
            if len(params) > 30:
                print(f"  ... 共 {len(params)} 个参数")
            
            # 提取材料
            print("\n" + "="*60)
            print("材料 (Materials)")
            print("="*60)
            mat_pattern = r'<material[^>]*label="([^"]*)"[^>]*tag="([^"]*)"'
            materials = re.findall(mat_pattern, content, re.IGNORECASE)
            for label, tag in materials:
                print(f"  - {tag}: {label if label else '(未命名)'}")
            
            # 提取物理场接口
            print("\n" + "="*60)
            print("物理场接口 (Physics Interfaces)")
            print("="*60)
            phys_pattern = r'<physics[^>]*interface="([^"]+)"[^>]*label="([^"]*)"'
            physics = re.findall(phys_pattern, content, re.IGNORECASE)
            for interface, label in physics:
                print(f"  - {interface}: {label if label else '(未命名)'}")
            
            # 提取几何特征类型
            print("\n" + "="*60)
            print("几何特征 (Geometry Features)")
            print("="*60)
            geom_pattern = r'<feature[^>]*type="([^"]+)"[^>]*label="([^"]*)"'
            geoms = re.findall(geom_pattern, content, re.IGNORECASE)
            geom_types = {}
            for gtype, label in geoms:
                key = f"{gtype}"
                if key not in geom_types:
                    geom_types[key] = []
                geom_types[key].append(label if label else '(未命名)')
            
            for gtype, labels in sorted(geom_types.items()):
                print(f"  - {gtype}: {len(labels)} 个")
                for label in labels[:3]:
                    print(f"      • {label}")
                if len(labels) > 3:
                    print(f"      ... 等 {len(labels)} 个")
            
            # 提取研究步骤
            print("\n" + "="*60)
            print("研究步骤 (Study Steps)")
            print("="*60)
            study_pattern = r'<studyStep[^>]*type="([^"]+)"[^>]*label="([^"]*)"'
            studies = re.findall(study_pattern, content, re.IGNORECASE)
            for stype, label in studies:
                print(f"  - {stype}: {label if label else '(未命名)'}")
            
            # 提取边界条件类型
            print("\n" + "="*60)
            print("边界条件类型 (Boundary Conditions)")
            print("="*60)
            bc_pattern = r'<feature[^>]*type="([^"]+)"[^>]*/>'
            all_features = re.findall(bc_pattern, content, re.IGNORECASE)
            
            # 常见的边界条件和物理场特征类型
            bc_keywords = ['Inlet', 'Outlet', 'Wall', 'Symmetry', 'Temperature', 
                          'HeatSource', 'Pressure', 'Velocity', 'ThermalInsulation',
                          'ConvectiveOutflow', 'InitialValues']
            
            bc_counts = {}
            for feat_type in all_features:
                for keyword in bc_keywords:
                    if keyword.lower() in feat_type.lower():
                        bc_counts[feat_type] = bc_counts.get(feat_type, 0) + 1
                        break
            
            for bc_type, count in sorted(bc_counts.items(), key=lambda x: -x[1]):
                print(f"  - {bc_type}: {count} 个")
            
            # 统计维度信息
            print("\n" + "="*60)
            print("维度信息")
            print("="*60)
            dim_pattern = r'dim="(\d+)"'
            dims = re.findall(dim_pattern, content)
            dim_counts = {}
            for d in dims:
                dim_counts[d] = dim_counts.get(d, 0) + 1
            
            for dim, count in sorted(dim_counts.items()):
                dim_name = {0: '点', 1: '边', 2: '面', 3: '体'}.get(int(dim), f'{dim}维')
                print(f"  {dim_name} ({dim}D): {count} 处引用")
            
            # 检查是否为三维模型
            has_3d = '3' in dim_counts
            print(f"\n  模型维度: {'三维 (3D)' if has_3d else '二维 (2D) 或其他'}")
            
    except Exception as e:
        print(f"[ERROR] 解析失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    mph_path = r"f:\pyProject\fipy_naca0012_2.0\大论文初稿\plate_fin_heat_exchanger.mph"
    extract_mph_info(mph_path)
