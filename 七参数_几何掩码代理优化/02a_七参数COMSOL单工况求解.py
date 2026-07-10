#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import mph
import argparse
import traceback
import jpype
import math
import csv

# ---------------------- 核心建模、求解与数据提取 ----------------------
def create_and_solve_thermal_model(args, outdir):
    outdir = os.path.abspath(outdir).replace('\\', '/')
    os.makedirs(outdir, exist_ok=True)

    print("[INFO] [Worker] 启动 COMSOL 客户端...")
    client = mph.start()
    
    try:
        model = client.create('NACA_Single_Case')
        pymodel = model.java 
        jint = jpype.java.lang.Integer
        JDoubleArray = jpype.JArray(jpype.JDouble)
        JStringArray = jpype.JArray(jpype.java.lang.String) 

        model.parameter('Ta',  str(args.Ta))
        model.parameter('Twa', str(args.Twa))
        model.parameter('Tb',  str(args.Tb))
        model.parameter('Tt',  str(args.Tt))
        model.parameter('Ts',  str(args.Ts))
        model.parameter('Tad', str(args.Tad))
        model.parameter('theta_deg', str(args.theta))
        
        model.parameter('chord', '0.01[m]') 
        model.parameter('u_in', '5[m/s]')
        model.parameter('Q_heat', f'{args.Q_heat}[W/m^3]')
        model.parameter('T_amb', '293.15[K]')

        func = pymodel.func()
        func.create("yt", "Analytic").set("expr", "Tb/0.2 * (0.2969*sqrt(s) - 0.1260*s - 0.3516*s^2 + 0.2843*s^3 - 0.1036*s^4)").set("args", ["s"])
        func.create("yc", "Analytic").set("expr", "(s<Twa) * (Ta/Twa^2 * (2*Twa*s - s^2)) + (s>=Twa) * (Ta/(1-Twa)^2 * ((1-2*Twa) + 2*Twa*s - s^2))").set("args", ["s"])
        func.create("dyc", "Analytic").set("expr", "(s<Twa) * (2*Ta/Twa^2 * (Twa-s)) + (s>=Twa) * (2*Ta/(1-Twa)^2 * (Twa-s))").set("args", ["s"])
        func.create("camber_angle", "Analytic").set("expr", "atan(dyc(s))").set("args", ["s"])
        func.create("xu0", "Analytic").set("expr", "(s - yt(s)*sin(camber_angle(s))) * chord").set("args", ["s"])
        func.create("yu0", "Analytic").set("expr", "(yc(s) + yt(s)*cos(camber_angle(s))) * chord").set("args", ["s"])
        func.create("xl0", "Analytic").set("expr", "(s + yt(s)*sin(camber_angle(s))) * chord").set("args", ["s"])
        func.create("yl0", "Analytic").set("expr", "(yc(s) - yt(s)*cos(camber_angle(s))) * chord").set("args", ["s"])
        # theta_deg 表示翼型整体相对来流方向的倾斜角，绕本翼型弦长中点旋转。
        func.create("xu", "Analytic").set("expr", "0.5*chord + (xu0(s)-0.5*chord)*cos(theta_deg*pi/180) - yu0(s)*sin(theta_deg*pi/180)").set("args", ["s"])
        func.create("yu", "Analytic").set("expr", "(xu0(s)-0.5*chord)*sin(theta_deg*pi/180) + yu0(s)*cos(theta_deg*pi/180)").set("args", ["s"])
        func.create("xl", "Analytic").set("expr", "0.5*chord + (xl0(s)-0.5*chord)*cos(theta_deg*pi/180) - yl0(s)*sin(theta_deg*pi/180)").set("args", ["s"])
        func.create("yl", "Analytic").set("expr", "(xl0(s)-0.5*chord)*sin(theta_deg*pi/180) + yl0(s)*cos(theta_deg*pi/180)").set("args", ["s"])

        comp1 = pymodel.component().create('comp1', True)
        geom1 = comp1.geom().create('geom1', 2)
        
        y_factors = [-1, 0, 1] 
        for j in range(3):
            for i in range(8):
                tag = f'_{j}_{i}'
                geom1.feature().create("up"+tag, "ParametricCurve").set("parmax", "1").set("coord", ["xu(s)", "yu(s)"])
                geom1.feature().create("dn"+tag, "ParametricCurve").set("parmax", "1").set("coord", ["xl(s)", "yl(s)"])
                
                csol_name = "csol"+tag
                csol = geom1.feature().create(csol_name, "ConvertToSolid")
                csol.selection("input").set(JStringArray(["up"+tag, "dn"+tag]))
                csol.set("repairtol", 1e-5)
                
                x_stagger_term = f"({1 if j%2!=0 else 0} * Tad * chord)"
                x_expr = f"{i} * (1+Ts) * chord + {x_stagger_term}"
                y_expr = f"{y_factors[j]} * Tt * chord"
                
                mov_feat = geom1.feature().create("mov"+tag, "Move")
                mov_feat.selection("input").set(JStringArray([csol_name]))
                mov_feat.set("displ", JStringArray([x_expr, y_expr]))

        rect_w_expr = "(8 * (1+Ts) + Tad + 15) * chord"
        # Channel height is only slightly larger than the airfoil-tube array.
        # Row centers are at -Tt*c, 0, +Tt*c; Ta and Tb cover camber/thickness,
        # and 0.35*c leaves a small clearance to the upper/lower boundaries.
        rect_h_expr = "2 * (Tt + Ta + Tb + 0.35 + 0.6*abs(sin(theta_deg*pi/180))) * chord"
        
        rect = geom1.feature().create('rect1', 'Rectangle')
        rect.set('size', JStringArray([rect_w_expr, rect_h_expr]))
        # Keep the airfoil array centered in the y direction. The previous
        # fixed lower-left corner [-0.05, -0.05] made the bottom clearance much
        # smaller than the top clearance when Tt changed.
        rect.set('pos', JStringArray(["-5 * chord", "-1 * (Tt + Ta + Tb + 0.35 + 0.6*abs(sin(theta_deg*pi/180))) * chord"]))
        geom1.run('fin')

        sel_in = comp1.selection().create('sel_inlet', 'Box')
        sel_in.set('entitydim', jint(1))
        sel_in.set('xmin', -0.05 - 0.001); sel_in.set('xmax', -0.05 + 0.001)
        
        # 使用 Python 原生计算代替 eval，防止变量作用域报错
        rect_w_val = (8 * (1 + args.Ts) + args.Tad + 15) * 0.01
        
        sel_out = comp1.selection().create('sel_outlet', 'Box')
        sel_out.set('entitydim', jint(1))
        sel_out.set('xmin', -0.05 + rect_w_val - 0.001)
        sel_out.set('xmax', -0.05 + rect_w_val + 0.001)

        def selection_entities(selection):
            return [int(item) for item in selection.entities(jint(1))]

        def make_wall_box_selection(name, xmin, xmax, ymin, ymax):
            sel = comp1.selection().create(name, 'Box')
            sel.set('entitydim', jint(1))
            sel.set('condition', 'inside')
            sel.set('xmin', xmin)
            sel.set('xmax', xmax)
            sel.set('ymin', ymin)
            sel.set('ymax', ymax)
            return sel

        def export_wall_boundary_catalog():
            rows = []
            chord = 0.01
            theta_margin = 0.6 * abs(math.sin(args.theta * math.pi / 180.0)) * chord
            broad_xmin = -0.002
            broad_xmax = (7 * (1 + args.Ts) + args.Tad + 1.0) * chord + 0.002
            broad_yspan = (args.Tt + abs(args.Ta) + abs(args.Tb) + 0.35) * chord + theta_margin
            broad_sel = make_wall_box_selection('diag_wall_broad_box', broad_xmin, broad_xmax, -broad_yspan, broad_yspan)
            broad_entities = selection_entities(broad_sel)
            rows.append({
                'mode': 'broad_box',
                'tag': 'all',
                'xmin': broad_xmin,
                'xmax': broad_xmax,
                'ymin': -broad_yspan,
                'ymax': broad_yspan,
                'count': len(broad_entities),
                'entities': ' '.join(str(item) for item in broad_entities),
            })

            all_local = set()
            half_x = (0.58 + abs(args.Ta) + abs(args.Tb)) * chord + theta_margin
            half_y = (abs(args.Ta) + abs(args.Tb) + 0.12) * chord + theta_margin
            for j in range(3):
                for i in range(8):
                    tag = f'{j}_{i}'
                    x_stagger = args.Tad * chord if j % 2 else 0.0
                    center_x = i * (1 + args.Ts) * chord + x_stagger + 0.5 * chord
                    center_y = y_factors[j] * args.Tt * chord
                    sel = make_wall_box_selection(
                        f'diag_wall_box_{tag}',
                        center_x - half_x,
                        center_x + half_x,
                        center_y - half_y,
                        center_y + half_y,
                    )
                    entities = selection_entities(sel)
                    all_local.update(entities)
                    rows.append({
                        'mode': 'array_box',
                        'tag': tag,
                        'xmin': center_x - half_x,
                        'xmax': center_x + half_x,
                        'ymin': center_y - half_y,
                        'ymax': center_y + half_y,
                        'count': len(entities),
                        'entities': ' '.join(str(item) for item in entities),
                    })

            rows.append({
                'mode': 'array_boxes_union',
                'tag': 'all',
                'xmin': '',
                'xmax': '',
                'ymin': '',
                'ymax': '',
                'count': len(all_local),
                'entities': ' '.join(str(item) for item in sorted(all_local)),
            })

            catalog_path = os.path.join(outdir, 'wall_boundary_selection_catalog.csv')
            with open(catalog_path, 'w', encoding='utf-8-sig', newline='') as handle:
                fieldnames = ['mode', 'tag', 'xmin', 'xmax', 'ymin', 'ymax', 'count', 'entities']
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            print(f"[INFO] Wall boundary catalog: {catalog_path}")
            print(f"[INFO] Broad wall boundary count: {len(broad_entities)}")
            print(f"[INFO] Array-box union boundary count: {len(all_local)}")
            return catalog_path

        def create_explicit_airfoil_wall_selection():
            # 由每个翼型局部选择合并为显式边界集合，避免边界层属性直接依赖动态 Box。
            chord = 0.01
            theta_margin = 0.6 * abs(math.sin(args.theta * math.pi / 180.0)) * chord
            half_x = (0.58 + abs(args.Ta) + abs(args.Tb)) * chord + theta_margin
            half_y = (abs(args.Ta) + abs(args.Tb) + 0.12) * chord + theta_margin
            all_local = set()
            for j in range(3):
                for i in range(8):
                    tag = f'{j}_{i}'
                    x_stagger = args.Tad * chord if j % 2 else 0.0
                    center_x = i * (1 + args.Ts) * chord + x_stagger + 0.5 * chord
                    center_y = y_factors[j] * args.Tt * chord
                    sel = make_wall_box_selection(
                        f'wall_exp_box_{tag}',
                        center_x - half_x,
                        center_x + half_x,
                        center_y - half_y,
                        center_y + half_y,
                    )
                    all_local.update(selection_entities(sel))
            explicit = comp1.selection().create('sel_airfoil_walls_explicit', 'Explicit')
            explicit.geom('geom1', jint(1))
            explicit.set([jint(item) for item in sorted(all_local)])
            print(f"[INFO] Explicit wall boundary selection count: {len(all_local)}")
            return 'sel_airfoil_walls_explicit'

        if args.export_wall_boundary_catalog:
            export_wall_boundary_catalog()
            if args.stop_after_wall_boundary_catalog:
                model.save(f"{outdir}/wall_boundary_diagnostic.mph")
                print("[INFO] Stop after wall boundary catalog export.")
                return

        wall_selection_name = "sel_airfoil_walls"
        wall_sel = None
        if args.wall_bl_layers > 0:
            # 用几何包围盒选中翼型柱壁面边界。该选择只覆盖阵列附近，避开入口、
            # 出口和上下对称边界，避免边界层误加到外边界上。
            wall_xmin = -0.002
            wall_xmax = (7 * (1 + args.Ts) + args.Tad + 1.0) * 0.01 + 0.002
            wall_yspan = (args.Tt + abs(args.Ta) + abs(args.Tb) + 0.35 + 0.6 * abs(math.sin(args.theta * math.pi / 180.0))) * 0.01
            wall_sel = comp1.selection().create('sel_airfoil_walls', 'Box')
            wall_sel.set('entitydim', jint(1))
            wall_sel.set('condition', 'inside')
            wall_sel.set('xmin', wall_xmin)
            wall_sel.set('xmax', wall_xmax)
            wall_sel.set('ymin', -wall_yspan)
            wall_sel.set('ymax', wall_yspan)
            try:
                wall_entities = list(wall_sel.entities(jint(1)))
                print(f"[INFO] Wall boundary selection count: {len(wall_entities)}")
            except Exception as exc:
                print(f"[WARN] Failed to inspect wall boundary selection: {exc}")
            if args.wall_bl_explicit:
                wall_selection_name = create_explicit_airfoil_wall_selection()

        mat_alum = comp1.material().create('mat_alum', 'Common')
        mat_alum.label('Aluminum')
        wing_ids = [jint(i) for i in range(2, 26)] 
        mat_alum.selection().set(wing_ids) 
        mat_alum.propertyGroup('def').set('density', '2700')
        mat_alum.propertyGroup('def').set('thermalconductivity', '238')
        mat_alum.propertyGroup('def').set('heatcapacity', '900')

        mat_air = comp1.material().create('mat_air', 'Common')
        mat_air.label('Air')
        mat_air.selection().set(jint(1)) 
        mat_air.propertyGroup('def').set('density', '1.2')
        mat_air.propertyGroup('def').set('dynamicviscosity', '1.8e-5')
        mat_air.propertyGroup('def').set('thermalconductivity', '0.026')
        mat_air.propertyGroup('def').set('heatcapacity', '1005')

        ht = comp1.physics().create('ht', 'HeatTransferInSolidsAndFluids', 'geom1')
        ht.selection().all()
        try: ht_fluid = ht.create('fluid1', 'Fluid', jint(2))
        except: ht_fluid = ht.feature('fluid1')
        ht_fluid.selection().set(jint(1))
        
        hs = ht.create('hs1', 'HeatSource', jint(2))
        hs.selection().set(wing_ids)
        hs.set('Q0', 'Q_heat')
        
        ifl = ht.create('ifl1', 'Inflow', jint(1))
        ifl.selection().named('sel_inlet')
        try: ifl.set('Tustr', 'T_amb')
        except: 
            try: ifl.set('T0', 'T_amb')
            except: pass
        
        try: ht.create('ofl1', 'ConvectiveOutflow', jint(1)).selection().named('sel_outlet')
        except: ht.create('ofl1', 'Outflow', jint(1)).selection().named('sel_outlet')

        spf = comp1.physics().create('spf', 'LaminarFlow', 'geom1')
        spf.selection().set(jint(1))
        spf.prop('AdvancedSettingProperty').set('UsePseudoTime', '1')
        spf.feature('init1').set('u', ['u_in', '0', '0'])
        
        inlet = spf.create('inl1', 'InletBoundary', jint(1))
        inlet.selection().named('sel_inlet')
        inlet.set('U0in', 'u_in')
        
        out1 = spf.create('out1', 'OutletBoundary', jint(1))
        out1.selection().named('sel_outlet')
        
        spf.create('sym1', 'Symmetry', jint(1)).selection().set([jint(2), jint(3)])
        comp1.multiphysics().create('nitf1', 'NonIsothermalFlow', jint(2))

        cpl = comp1.cpl()
        
        aveop_in = cpl.create("aveop_in", "Average")
        aveop_in.selection().geom("geom1", 1)
        aveop_in.selection().named("sel_inlet")
        
        aveop_out = cpl.create("aveop_out", "Average")
        aveop_out.selection().geom("geom1", 1)
        aveop_out.selection().named("sel_outlet")
        
        aveop_wings = cpl.create("aveop_wings", "Average")
        aveop_wings.selection().geom("geom1", 2)
        aveop_wings.selection().set(wing_ids)
        
        intop_wings = cpl.create("intop_wings", "Integration")
        intop_wings.selection().geom("geom1", 2)
        intop_wings.selection().set(wing_ids)

        mesh1 = comp1.mesh().create('mesh1', 'geom1')
        mesh1.feature('size').set('hauto', jint(args.mesh_hauto))

        def apply_domain_size(tag, domain_ids, hmax, hmin):
            if not hmax and not hmin:
                return
            size = mesh1.feature().create(tag, "Size")
            size.selection().geom("geom1", 2)
            size.selection().set(domain_ids)
            try: size.set("custom", "on")
            except: pass
            if hmax:
                size.set("hmax", hmax)
            if hmin:
                size.set("hmin", hmin)
            try: size.set("hgrad", str(args.mesh_hgrad))
            except: pass

        # 网格无关性整改：只依赖全局 hauto 会导致翼型附近边界层和尾迹
        # 随档位非一致细化。这里增加域级局部尺寸入口，默认不传时保持旧行为。
        apply_domain_size("size_air", [jint(1)], args.air_hmax, args.air_hmin)
        apply_domain_size("size_solid", wing_ids, args.solid_hmax, args.solid_hmin)
        if args.wall_bl_layers > 0:
            try:
                bl = mesh1.feature().create("bl_airfoil", "BndLayer")
                bl.selection().geom("geom1", 2)
                bl.selection().set([jint(1)])
                try:
                    blp = bl.feature("blp1")
                except Exception:
                    blp = bl.feature().create("blp1", "BndLayerProp")
                blp.selection().named(wall_selection_name)
                blp.set("blnlayers", jint(args.wall_bl_layers))
                blp.set("blhminfact", str(args.wall_bl_hminfact))
            except Exception:
                if args.wall_bl_required:
                    raise
                print("[WARN] 翼型壁面边界层网格创建失败，已继续使用常规网格。")
        try:
            ftri = mesh1.feature().create("ftri1", "FreeTri")
            ftri.selection().geom("geom1", 2)
            ftri.selection().all()
        except Exception:
            pass
        mesh1.run()
        try:
            mesh_elems = int(mesh1.getNumElem())
        except Exception:
            try:
                mesh_elems = int(mesh1.getNumElem("tri"))
            except Exception:
                mesh_elems = -1

        std = pymodel.study().create('std1')
        std.create('stat', 'Stationary')
        std.showAutoSequences('all')
        
        try: pymodel.sol('sol1').feature('s1').set('reltol', '0.01')
        except: pass

        print("[INFO] [Worker] 正在求解...")
        model.solve()
        
        res = pymodel.result()
        try:
            dset = res.dataset().create("my_dset", "Solution")
            dset.set("solution", "sol1")
        except: pass 

        def set_boolean_attr(node, attrs, enabled):
            text_value = "on" if enabled else "off"
            for attr in attrs:
                try: node.set(attr, text_value)
                except: pass
                try: node.set(attr, bool(enabled))
                except: pass

        def configure_plot_legend(plot_group):
            set_boolean_attr(plot_group, ["legend", "showlegend", "showlegends", "colorlegend"], args.paper_legend)
            if args.paper_legend:
                for key, value in [("showlegends", "on"), ("titletype", "none")]:
                    try: plot_group.set(key, value)
                    except: pass

        def configure_export_image(export_node):
            if args.paper_legend:
                set_boolean_attr(export_node, ["axes", "showaxes"], True)
                try: export_node.set("unit", "px")
                except: pass
                try: export_node.set("width", "1100")
                except: pass
                try: export_node.set("height", "520")
                except: pass
            else:
                set_boolean_attr(export_node, ["axes", "showaxes"], False)
            set_boolean_attr(export_node, ["title"], False)
            set_boolean_attr(export_node, ["legend", "showlegend", "colorlegend"], args.paper_legend)

        # --- 出图部分 ---
        try:
            pg_vel = res.create("pg_vel", "PlotGroup2D")
            pg_vel.set("data", "my_dset") 
            configure_plot_legend(pg_vel)
            surf_vel = pg_vel.create("surf_vel", "Surface")
            surf_vel.set("expr", "spf.U")
            try: pg_vel.run()
            except: pass
            exp_vel = res.export().create("exp_vel", "Image2D")
            exp_vel.set("plotgroup", "pg_vel")
            exp_vel.set("target", "file")  
            exp_vel.set("filename", f"{outdir}/velocity_magnitude.png")
            exp_vel.set("resolution", "150")
            configure_export_image(exp_vel)
            exp_vel.run()
        except Exception as e: print(f"[WARN] 速度场导出失败: {e}")

        try:
            pg_p = res.create("pg_p", "PlotGroup2D")
            pg_p.set("data", "my_dset")
            configure_plot_legend(pg_p)
            surf_p = pg_p.create("surf_p", "Surface")
            surf_p.set("expr", "p")
            try: pg_p.run()
            except: pass
            exp_p = res.export().create("exp_p", "Image2D")
            exp_p.set("plotgroup", "pg_p")
            exp_p.set("target", "file")  
            exp_p.set("filename", f"{outdir}/pressure.png")
            exp_p.set("resolution", "150")
            configure_export_image(exp_p)
            exp_p.run()
        except Exception as e: print(f"[WARN] 压力场导出失败: {e}")

        try:
            pg_T = res.create("pg_T", "PlotGroup2D")
            pg_T.set("data", "my_dset")
            configure_plot_legend(pg_T)
            surf_T = pg_T.create("surf_T", "Surface")
            surf_T.set("expr", "T")
            try: pg_T.run()
            except: pass
            exp_T = res.export().create("exp_T", "Image2D")
            exp_T.set("plotgroup", "pg_T")
            exp_T.set("target", "file")  
            exp_T.set("filename", f"{outdir}/temperature.png")
            exp_T.set("resolution", "150")
            configure_export_image(exp_T)
            exp_T.run()
        except Exception as e: print(f"[WARN] 温度场导出失败: {e}")

        # --- 🌟 提取【所有】物理量原始源数据 ---
        try:
            eg = res.numerical().create("eg_perf", "EvalGlobal")

            def first_scalar(value):
                """Return the first numeric value from COMSOL's nested Java arrays."""
                while hasattr(value, "__len__") and not isinstance(value, (str, bytes)):
                    if len(value) == 0:
                        return float("nan")
                    value = value[0]
                return float(value)

            def eval_global(expr):
                eg.set("expr", expr)
                return first_scalar(eg.computeResult())
            
            # 压力
            p_in = eval_global("aveop_in(p)")
            p_out = eval_global("aveop_out(p)")
            
            # 温度
            T_wing_avg = eval_global("aveop_wings(T)")
            T_in_val = eval_global("aveop_in(T)")
            T_out_val = eval_global("aveop_out(T)")

            # 速度
            v_in_val = eval_global("aveop_in(spf.U)")
            v_out_val = eval_global("aveop_out(spf.U)")
            
            # 面积/体积
            vol_total = eval_global("intop_wings(1)")
            
            # 计算衍生的目标标签: Nu 和 f
            delta_p = abs(p_in - p_out)
            rho = 1.2
            u_in_set = 5.0
            k_air = 0.026
            Q_vol_val = args.Q_heat
            chord_val = 0.01
            
            f_val = delta_p / (0.5 * rho * u_in_set**2)
            
            Q_total = Q_vol_val * vol_total
            delta_T = T_wing_avg - T_in_val
            if delta_T > 0:
                h_eff = Q_total / delta_T
                nu_val = (h_eff * chord_val) / k_air
            else:
                nu_val = 0.0

        except Exception as e:
            f_val, nu_val = float('nan'), float('nan')
            T_in_val, T_out_val, T_wing_avg = float('nan'), float('nan'), float('nan')
            v_in_val, v_out_val = float('nan'), float('nan')
            p_in, p_out, vol_total = float('nan'), float('nan'), float('nan')
            print(f"[WARN] 提取物理特征失败: {e}")

        # 将【所有的特征(共10项)】打包打印出来给主控脚本抓取
        print(f"CFD_RESULT_DATA: mesh={mesh_elems}, Nu={nu_val:.6f}, f={f_val:.6f}, T_in={T_in_val:.6f}, T_out={T_out_val:.6f}, v_in={v_in_val:.6f}, v_out={v_out_val:.6f}, p_in={p_in:.6f}, p_out={p_out:.6f}, T_wing={T_wing_avg:.6f}, vol={vol_total:.9f}, Q_total={Q_total:.9f}, delta_T={delta_T:.6f}")
        model.save(f"{outdir}/model.mph")
        
    except Exception as e:
        print(f"[ERROR] [Worker] 运行出错: {e}")
        traceback.print_exc()
        sys.exit(1)
    finally:
        client.disconnect()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--Ta', type=float, required=True)
    parser.add_argument('--Twa', type=float, required=True)
    parser.add_argument('--Tb', type=float, required=True)
    parser.add_argument('--Tt', type=float, required=True)
    parser.add_argument('--Ts', type=float, required=True)
    parser.add_argument('--Tad', type=float, required=True)
    parser.add_argument('--theta', type=float, required=True)
    parser.add_argument('--Q_heat', type=float, default=1e7)
    parser.add_argument('--mesh_hauto', type=int, default=4)
    parser.add_argument('--mesh_hgrad', type=float, default=1.25)
    parser.add_argument('--air_hmax', default='')
    parser.add_argument('--air_hmin', default='')
    parser.add_argument('--solid_hmax', default='')
    parser.add_argument('--solid_hmin', default='')
    parser.add_argument('--wall_bl_layers', type=int, default=0)
    parser.add_argument('--wall_bl_hminfact', type=float, default=3.0)
    parser.add_argument('--wall_bl_required', action='store_true')
    parser.add_argument('--wall_bl_explicit', action='store_true')
    parser.add_argument('--export_wall_boundary_catalog', action='store_true')
    parser.add_argument('--stop_after_wall_boundary_catalog', action='store_true')
    parser.add_argument('--outdir', type=str, required=True)
    parser.add_argument('--paper_legend', action='store_true', help='导出论文云图时保留 COMSOL 原生颜色图例。')
    
    args = parser.parse_args()
    create_and_solve_thermal_model(args, args.outdir)
