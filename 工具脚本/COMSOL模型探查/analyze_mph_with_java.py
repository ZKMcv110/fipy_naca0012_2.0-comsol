#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
通过 COMSOL Java API 读取 plate_fin_heat_exchanger.mph 的详细配置
"""

import jpype
import mph

def analyze_with_java_api(mph_path: str):
    """使用 Java API 深度分析 MPH 文件"""
    
    print("="*80)
    print("使用 COMSOL Java API 分析模型")
    print("="*80)
    
    # 启动 COMSOL
    print("\n[INFO] 启动 COMSOL...")
    client = mph.start()
    
    try:
        # 加载模型
        print(f"[INFO] 加载模型: {mph_path}")
        model = client.load(mph_path)
        java_model = model.java
        
        # ========== 1. 模型基本信息 ==========
        print("\n" + "="*80)
        print("【1. 模型基本信息】")
        print("="*80)
        print(f"模型标签: {java_model.tag()}")
        print(f"模型名称: {java_model.name()}")
        
        # ========== 2. 参数信息 ==========
        print("\n" + "="*80)
        print("【2. 全局参数 (Parameters)】")
        print("="*80)
        
        param_obj = java_model.param()
        # 尝试不同的方法获取参数名
        try:
            param_names = list(param_obj.names())
        except AttributeError:
            # 如果 names() 不存在，尝试其他方式
            try:
                param_dict = dict(param_obj)
                param_names = list(param_dict.keys())
            except:
                # 最后尝试：从 XML 中提取（回退方案）
                print("  [WARN] 无法通过 Java API 获取参数，使用 XML 解析")
                import zipfile, re
                z = zipfile.ZipFile(mph_path)
                content = z.read('dmodel.xml').decode('utf-8', errors='ignore')
                params_xml = re.findall(r'<expressions[^>]*name="([^"]+)"[^>]*expr="([^"]*)"', content)
                param_names = [p[0] for p in params_xml]
                param_exprs = {p[0]: p[1] for p in params_xml}
        
        print(f"参数总数: {len(param_names)}")
        print("\n前30个参数:")
        for i, name in enumerate(param_names[:30]):
            try:
                expr = param_obj.getString(name)
                descr = param_obj.getDescription(name)
            except:
                # 如果 Java API 失败，使用 XML 提取的结果
                expr = param_exprs.get(name, 'N/A')
                descr = ''
            print(f"  [{i+1:2d}] {name:25s} = {expr:30s}")
            if descr:
                print(f"       描述: {descr}")
        
        if len(param_names) > 30:
            print(f"\n  ... 共 {len(param_names)} 个参数")
        
        # ========== 3. 组件和几何 ==========
        print("\n" + "="*80)
        print("【3. 组件与几何 (Components & Geometry)】")
        print("="*80)
        
        comp_tags = list(java_model.component().tags())
        print(f"组件数量: {len(comp_tags)}")
        for comp_tag in comp_tags:
            print(f"\n  组件: {comp_tag}")
            comp = java_model.component(comp_tag)
            
            # 几何序列
            geom_tags = list(comp.geom().tags())
            if geom_tags:
                print(f"    几何序列: {geom_tags}")
                for gtag in geom_tags:
                    try:
                        geom_seq = comp.geom(gtag)
                        # GeomSequence 没有 dim() 方法，需要从 feature 中推断
                        print(f"      - {gtag}")
                        
                        # 几何特征
                        features = geom_seq.feature()
                        feat_tags = list(features.tags())
                        print(f"        几何特征数: {len(feat_tags)}")
                        for ftag in feat_tags[:15]:  # 显示前15个
                            try:
                                feat = features.get(ftag)
                                ftype = feat.type()
                                flabel = feat.label()
                                print(f"          • {ftag}: type={ftype}, label={flabel}")
                            except Exception as e:
                                print(f"          • {ftag}: (读取失败: {e})")
                        if len(feat_tags) > 15:
                            print(f"          ... 等 {len(feat_tags)} 个特征")
                    except Exception as e:
                        print(f"      - {gtag}: (读取失败: {e})")
        
        # ========== 4. 材料 ==========
        print("\n" + "="*80)
        print("【4. 材料 (Materials)】")
        print("="*80)
        
        for comp_tag in comp_tags[:1]:  # 只分析第一个组件
            comp = java_model.component(comp_tag)
            mat_tags = list(comp.material().tags())
            print(f"材料数量: {len(mat_tags)}")
            
            for mtag in mat_tags:
                mat = comp.material(mtag)
                label = mat.label()
                print(f"\n  材料: {mtag}")
                print(f"    标签: {label if label else '(未命名)'}")
                
                # 材料属性
                try:
                    prop_group = mat.propertyGroup("def")
                    props = list(prop_group.properties())
                    print(f"    属性数量: {len(props)}")
                    for prop in props[:5]:  # 只显示前5个
                        val = prop_group.getString(prop)
                        print(f"      - {prop}: {val}")
                    if len(props) > 5:
                        print(f"      ... 等 {len(props)} 个属性")
                except Exception as e:
                    print(f"    属性读取失败: {e}")
        
        # ========== 5. 物理场 ==========
        print("\n" + "="*80)
        print("【5. 物理场接口 (Physics Interfaces)】")
        print("="*80)
        
        for comp_tag in comp_tags[:1]:
            comp = java_model.component(comp_tag)
            phys_tags = list(comp.physics().tags())
            print(f"物理场数量: {len(phys_tags)}")
            
            for ptag in phys_tags:
                phys = comp.physics(ptag)
                interface_type = phys.getType()
                label = phys.label()
                print(f"\n  物理场: {ptag}")
                print(f"    类型: {interface_type}")
                print(f"    标签: {label if label else '(未命名)'}")
                
                # 物理场特征（边界条件、初始条件等）
                features = phys.feature()  # 注意：是 feature() 不是 features()
                feat_tags = list(features.tags())
                print(f"    特征数量: {len(feat_tags)}")
                
                # 按类型分类统计
                type_counts = {}
                for ftag in feat_tags:
                    feat = features.get(ftag)
                    ftype = feat.type()
                    type_counts[ftype] = type_counts.get(ftype, 0) + 1
                
                for ftype, count in sorted(type_counts.items(), key=lambda x: -x[1]):
                    print(f"      - {ftype}: {count} 个")
                
                # 显示关键边界条件详情
                bc_keywords = ['Inlet', 'Outlet', 'Wall', 'Temperature', 'HeatSource']
                for ftag in feat_tags:
                    feat = features.get(ftag)
                    ftype = feat.type()
                    if any(kw in ftype for kw in bc_keywords):
                        flabel = feat.label()
                        print(f"        • {ftag}: {ftype} ({flabel})")
                        
                        # 尝试获取选择域
                        try:
                            sel = feat.selection()
                            if sel.all():
                                print(f"          选择: 全部实体")
                            else:
                                print(f"          选择: 部分实体")
                        except:
                            pass
        
        # ========== 6. 网格 ==========
        print("\n" + "="*80)
        print("【6. 网格 (Mesh)】")
        print("="*80)
        
        for comp_tag in comp_tags[:1]:
            comp = java_model.component(comp_tag)
            mesh_tags = list(comp.mesh().tags())
            print(f"网格序列数量: {len(mesh_tags)}")
            
            for mtag in mesh_tags:
                mesh = comp.mesh(mtag)
                print(f"\n  网格: {mtag}")
                print(f"    类型: {mesh.getType()}")
                
                # 网格统计
                try:
                    stats = mesh.getStat()
                    print(f"    单元数: {stats.get('nelem', 'N/A')}")
                    print(f"    自由度数: {stats.get('ndof', 'N/A')}")
                except Exception as e:
                    print(f"    统计信息: 未生成或不可用 ({e})")
        
        # ========== 7. 研究 ==========
        print("\n" + "="*80)
        print("【7. 研究 (Studies)】")
        print("="*80)
        
        study_tags = list(java_model.study().tags())
        print(f"研究数量: {len(study_tags)}")
        
        for stag in study_tags:
            study = java_model.study(stag)
            label = study.label()
            print(f"\n  研究: {stag}")
            print(f"    标签: {label if label else '(未命名)'}")
            
            # 研究步骤
            steps = study.feature()
            step_tags = list(steps.tags())
            print(f"    步骤数量: {len(step_tags)}")
            
            for step_tag in step_tags:
                step = steps.get(step_tag)
                stype = step.getType()
                slabel = step.label()
                print(f"      - {step_tag}: {stype} ({slabel})")
        
        # ========== 8. 求解器配置 ==========
        print("\n" + "="*80)
        print("【8. 求解器配置 (Solver)】")
        print("="*80)
        
        sol_tags = list(java_model.sol().tags())
        print(f"求解器序列数量: {len(sol_tags)}")
        
        for sol_tag in sol_tags:
            sol = java_model.sol(sol_tag)
            print(f"\n  求解器: {sol_tag}")
            print(f"    类型: {sol.getType()}")
            
            # 求解器步骤
            features = sol.features()
            feat_tags = list(features.tags())
            print(f"    步骤数量: {len(feat_tags)}")
            for ftag in feat_tags[:10]:
                feat = features.get(ftag)
                print(f"      - {ftag}: {feat.getType()}")
            if len(feat_tags) > 10:
                print(f"      ... 等 {len(feat_tags)} 个步骤")
        
        print("\n✅ Java API 分析完成")
        
    except Exception as e:
        print(f"\n[ERROR] 错误: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 断开连接
        try:
            client.disconnect()
            print("\n[INFO] COMSOL 连接已关闭")
        except:
            pass


if __name__ == "__main__":
    mph_path = r"f:\pyProject\fipy_naca0012_2.0\大论文初稿\plate_fin_heat_exchanger.mph"
    analyze_with_java_api(mph_path)
