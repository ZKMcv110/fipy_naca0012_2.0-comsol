#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import mph
import argparse
import traceback
import jpype

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
        
        model.parameter('chord', '0.01[m]') 
        model.parameter('u_in', '5[m/s]')
        model.parameter('Q_heat', '5e7[W/m^3]')
        model.parameter('T_amb', '293.15[K]')

        func = pymodel.func()
        func.create("yt", "Analytic").set("expr", "Tb/0.2 * (0.2969*sqrt(s) - 0.1260*s - 0.3516*s^2 + 0.2843*s^3 - 0.1036*s^4)").set("args", ["s"])
        func.create("yc", "Analytic").set("expr", "(s<Twa) * (Ta/Twa^2 * (2*Twa*s - s^2)) + (s>=Twa) * (Ta/(1-Twa)^2 * ((1-2*Twa) + 2*Twa*s - s^2))").set("args", ["s"])
        func.create("dyc", "Analytic").set("expr", "(s<Twa) * (2*Ta/Twa^2 * (Twa-s)) + (s>=Twa) * (2*Ta/(1-Twa)^2 * (Twa-s))").set("args", ["s"])
        func.create("theta", "Analytic").set("expr", "atan(dyc(s))").set("args", ["s"])
        func.create("xu", "Analytic").set("expr", "(s - yt(s)*sin(theta(s))) * chord").set("args", ["s"])
        func.create("yu", "Analytic").set("expr", "(yc(s) + yt(s)*cos(theta(s))) * chord").set("args", ["s"])
        func.create("xl", "Analytic").set("expr", "(s + yt(s)*sin(theta(s))) * chord").set("args", ["s"])
        func.create("yl", "Analytic").set("expr", "(yc(s) - yt(s)*cos(theta(s))) * chord").set("args", ["s"])

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
        rect_h_expr = "(3 * Tt + 10) * chord"
        
        rect = geom1.feature().create('rect1', 'Rectangle')
        rect.set('size', JStringArray([rect_w_expr, rect_h_expr]))
        rect.set('pos', JDoubleArray([-0.05, -0.05]))
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
        mesh1.feature('size').set('hauto', jint(4)) 
        mesh1.run()

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

        def purify_export_image(export_node):
            for attr in ['axes', 'legend', 'title', 'showlegend', 'showaxes', 'colorlegend']:
                try: export_node.set(attr, "off")
                except: pass
                try: export_node.set(attr, False)
                except: pass

        # --- 出图部分 ---
        try:
            pg_vel = res.create("pg_vel", "PlotGroup2D")
            pg_vel.set("data", "my_dset") 
            try: pg_vel.set("showlegend", False)
            except: pass
            surf_vel = pg_vel.create("surf_vel", "Surface")
            surf_vel.set("expr", "spf.U")
            exp_vel = res.export().create("exp_vel", "Image2D")
            exp_vel.set("plotgroup", "pg_vel")
            exp_vel.set("target", "file")  
            exp_vel.set("filename", f"{outdir}/velocity_magnitude.png")
            exp_vel.set("resolution", "150")
            purify_export_image(exp_vel)
            exp_vel.run()
        except Exception as e: print(f"[WARN] 速度场导出失败: {e}")

        try:
            pg_p = res.create("pg_p", "PlotGroup2D")
            pg_p.set("data", "my_dset")
            try: pg_p.set("showlegend", False)
            except: pass
            surf_p = pg_p.create("surf_p", "Surface")
            surf_p.set("expr", "p")
            exp_p = res.export().create("exp_p", "Image2D")
            exp_p.set("plotgroup", "pg_p")
            exp_p.set("target", "file")  
            exp_p.set("filename", f"{outdir}/pressure.png")
            exp_p.set("resolution", "150")
            purify_export_image(exp_p)
            exp_p.run()
        except Exception as e: print(f"[WARN] 压力场导出失败: {e}")

        try:
            pg_T = res.create("pg_T", "PlotGroup2D")
            pg_T.set("data", "my_dset")
            try: pg_T.set("showlegend", False)
            except: pass
            surf_T = pg_T.create("surf_T", "Surface")
            surf_T.set("expr", "T")
            exp_T = res.export().create("exp_T", "Image2D")
            exp_T.set("plotgroup", "pg_T")
            exp_T.set("target", "file")  
            exp_T.set("filename", f"{outdir}/temperature.png")
            exp_T.set("resolution", "150")
            purify_export_image(exp_T)
            exp_T.run()
        except Exception as e: print(f"[WARN] 温度场导出失败: {e}")

        # --- 🌟 提取【所有】物理量原始源数据 ---
        try:
            eg = res.numerical().create("eg_perf", "EvalGlobal")
            
            # 压力
            eg.set("expr", "aveop_in(p)")
            p_in = eg.computeResult()[0][0]
            eg.set("expr", "aveop_out(p)")
            p_out = eg.computeResult()[0][0]
            
            # 温度
            eg.set("expr", "aveop_wings(T)")
            T_wing_avg = eg.computeResult()[0][0]
            eg.set("expr", "aveop_in(T)")
            T_in_val = eg.computeResult()[0][0]
            eg.set("expr", "aveop_out(T)")
            T_out_val = eg.computeResult()[0][0]

            # 速度
            eg.set("expr", "aveop_in(spf.U)")
            v_in_val = eg.computeResult()[0][0]
            eg.set("expr", "aveop_out(spf.U)")
            v_out_val = eg.computeResult()[0][0]
            
            # 面积/体积
            eg.set("expr", "intop_wings(1)")
            vol_total = eg.computeResult()[0][0]
            
            # 计算衍生的目标标签: Nu 和 f
            delta_p = abs(p_in - p_out)
            rho = 1.2
            u_in_set = 5.0
            k_air = 0.026
            Q_vol_val = 5e7
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
        print(f"CFD_RESULT_DATA: Nu={nu_val:.6f}, f={f_val:.6f}, T_in={T_in_val:.6f}, T_out={T_out_val:.6f}, v_in={v_in_val:.6f}, v_out={v_out_val:.6f}, p_in={p_in:.6f}, p_out={p_out:.6f}, T_wing={T_wing_avg:.6f}, vol={vol_total:.9f}")
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
    parser.add_argument('--outdir', type=str, required=True)
    
    args = parser.parse_args()
    create_and_solve_thermal_model(args, args.outdir)