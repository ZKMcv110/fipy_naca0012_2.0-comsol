#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""分析 COMSOL 官方案例 plate_fin_heat_exchanger.mph 的结构和参数"""

import json
from pathlib import Path

def analyze_mph_structure(mph_path: str):
    """读取 MPH 文件的基本结构信息"""
    try:
        import mph
        import jpype
        
        print(f"[INFO] 正在打开模型: {mph_path}")
        client = mph.start()
        
        try:
            model = client.load(mph_path)
            pymodel = model.java
            
            # 基本信息
            print("\n" + "="*60)
            print("模型基本信息")
            print("="*60)
            print(f"模型名称: {model}")
            
            # 组件信息
            print("\n" + "="*60)
            print("组件 (Components)")
            print("="*60)
            comp_tags = list(pymodel.component().tags())
            for tag in comp_tags:
                print(f"  - {tag}")
            
            if comp_tags:
                comp = pymodel.component(comp_tags[0])
                
                # 几何信息
                print("\n" + "="*60)
                print("几何 (Geometry)")
                print("="*60)
                try:
                    geom_list = comp.geom()
                    gtag = list(geom_list.tags())[0]
                    print(f"  几何节点: {gtag}")
                    geom_feat = geom_list.get(gtag)
                    print(f"    维度: {geom_feat.dim()}")
                    print(f"    长度单位: {geom_feat.lengthUnit()}")
                    
                    # 列出所有几何特征
                    features = geom_feat.feature()
                    print(f"    几何特征数量: {features.size()}")
                    for ftag in features.tags():
                        feat = features.get(ftag)
                        print(f"      - {ftag}: {feat.type()}")
                except Exception as e:
                    print(f"  几何信息获取失败: {e}")
                    import traceback
                    traceback.print_exc()
                
                # 材料信息
                print("\n" + "="*60)
                print("材料 (Materials)")
                print("="*60)
                try:
                    mat_list = comp.material()
                    for mtag in mat_list.tags():
                        mat = mat_list.get(mtag)
                        print(f"  - {mtag}: {mat.label()}")
                        try:
                            props = mat.propertyGroup("def")
                            prop_names = list(props.properties())
                            for pname in prop_names:
                                val = props.getString(pname, 0)
                                print(f"      {pname} = {val}")
                        except Exception as e:
                            print(f"      属性读取失败: {e}")
                except Exception as e:
                    print(f"  材料信息获取失败: {e}")
                    import traceback
                    traceback.print_exc()
                
                # 物理场信息
                print("\n" + "="*60)
                print("物理场 (Physics)")
                print("="*60)
                try:
                    phys_list = comp.physics()
                    for ptag in phys_list.tags():
                        phys = phys_list.get(ptag)
                        print(f"  - {ptag}: {phys.type()}")
                        print(f"    标签: {phys.label()}")
                        
                        # 列出物理场特征
                        features = phys.features()
                        print(f"    特征数量: {features.size()}")
                        for ftag in features.tags():
                            feat = features.get(ftag)
                            print(f"      - {ftag}: {feat.type()} ({feat.label()})")
                            
                            # 尝试获取选择域
                            try:
                                sel = feat.selection()
                                if sel.all():
                                    print(f"          选择: 全部")
                                else:
                                    print(f"          选择: 部分实体")
                            except:
                                pass
                except Exception as e:
                    print(f"  物理场信息获取失败: {e}")
                    import traceback
                    traceback.print_exc()
                
                # 网格信息
                print("\n" + "="*60)
                print("网格 (Mesh)")
                print("="*60)
                try:
                    mesh_list = comp.mesh()
                    for mtag in mesh_list.tags():
                        mesh = mesh_list.get(mtag)
                        print(f"  - {mtag}: {mesh.type()}")
                        try:
                            stats = mesh.getStat()
                            print(f"    单元数: {stats.get('nelem', 'N/A')}")
                            print(f"    自由度数: {stats.get('ndof', 'N/A')}")
                        except:
                            print(f"    网格统计信息不可用（可能未生成）")
                except Exception as e:
                    print(f"  网格信息获取失败: {e}")
                    import traceback
                    traceback.print_exc()
                
                # 研究信息
                print("\n" + "="*60)
                print("研究 (Studies)")
                print("="*60)
                try:
                    study_list = pymodel.study()
                    for stag in study_list.tags():
                        study = study_list.get(stag)
                        print(f"  - {stag}: {study.label()}")
                        steps = study.features()
                        for step_tag in steps.tags():
                            step = steps.get(step_tag)
                            print(f"    - {step_tag}: {step.type()} ({step.label()})")
                except Exception as e:
                    print(f"  研究信息获取失败: {e}")
                    import traceback
                    traceback.print_exc()
                
                # 参数信息
                print("\n" + "="*60)
                print("全局参数 (Parameters)")
                print("="*60)
                try:
                    params = pymodel.param()
                    param_dict = dict(params)
                    for pname, pval in param_dict.items():
                        print(f"  {pname} = {pval}")
                except Exception as e:
                    print(f"  参数信息获取失败: {e}")
                    import traceback
                    traceback.print_exc()
                    
        finally:
            client.disconnect()
            
    except Exception as e:
        print(f"[ERROR] 分析失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    mph_path = r"f:\pyProject\fipy_naca0012_2.0\大论文初稿\plate_fin_heat_exchanger.mph"
    analyze_mph_structure(mph_path)
