#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""构建更接近真实热沉外观的三维翼型柱散热器模型。

本脚本是新的建模入口，不替换旧的 `build_airfoil_pillar_heat_sink.py`。
改动重点：
- 几何比例更紧凑：基座略大于翼型柱阵列，芯片热源接近基座投影范围；
- 翼型柱阵列整体居中，不贴边、不穿出通道；
- 入口/出口/芯片/空气/固体选择集在建模后立即检查；
- 仍采用风道内层流共轭传热模型，方便与 COMSOL 官方 heat_sink 案例对照。
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUT_ROOT = ROOT / "generated_realistic_heat_sink"

PARAM_NAMES = ("Ta", "Twa", "Tb", "Ts", "Tt", "Tad", "theta")

CASE_PARAMS = {
    "baseline": {"Ta": 0.0, "Twa": 0.40, "Tb": 0.12, "Ts": 1.10, "Tt": 0.85, "Tad": 0.0, "theta": 0.0},
    # 这组按你当前希望暂用的三维候选参数保存，后续真实三维搜索后再替换。
    "optimal_2d": {"Ta": 0.0473, "Twa": 0.3735, "Tb": 0.0917, "Ts": 1.3541, "Tt": 1.0926, "Tad": 0.3950, "theta": 0.0},
}


def log(message: str) -> None:
    print(f"[INFO] {message}", flush=True)


def airfoil_points(params: dict[str, float], chord: float, x_shift: float, y_shift: float) -> tuple[list[str], list[str]]:
    ta = params["Ta"]
    twa = params["Twa"]
    tb = params["Tb"]
    attack_angle = math.radians(params.get("theta", 0.0))
    cos_a = math.cos(attack_angle)
    sin_a = math.sin(attack_angle)
    # 三维布尔差集和体网格对小边很敏感；31 点能保留翼型外形并显著提高网格鲁棒性。
    point_count = 31

    def camber(s: float) -> tuple[float, float]:
        if abs(ta) < 1e-12:
            return 0.0, 0.0
        if s < twa:
            return ta / twa**2 * (2 * twa * s - s**2), 2 * ta / twa**2 * (twa - s)
        return (
            ta / (1 - twa) ** 2 * ((1 - 2 * twa) + 2 * twa * s - s**2),
            2 * ta / (1 - twa) ** 2 * (twa - s),
        )

    upper: list[tuple[float, float]] = []
    lower: list[tuple[float, float]] = []
    for index in range(point_count):
        s = index / (point_count - 1)
        yt = tb / 0.2 * (
            0.2969 * math.sqrt(s)
            - 0.1260 * s
            - 0.3516 * s**2
            + 0.2843 * s**3
            - 0.1036 * s**4
        )
        yc, dyc = camber(s)
        camber_angle = math.atan(dyc)
        xu = (s - yt * math.sin(camber_angle)) * chord
        yu = (yc + yt * math.cos(camber_angle)) * chord
        xl = (s + yt * math.sin(camber_angle)) * chord
        yl = (yc - yt * math.cos(camber_angle)) * chord

        # theta 为翼型整体相对来流方向的倾斜角，沿用二维七参数脚本定义：绕弦长中点旋转。
        xu_rot = 0.5 * chord + (xu - 0.5 * chord) * cos_a - yu * sin_a
        yu_rot = (xu - 0.5 * chord) * sin_a + yu * cos_a
        xl_rot = 0.5 * chord + (xl - 0.5 * chord) * cos_a - yl * sin_a
        yl_rot = (xl - 0.5 * chord) * sin_a + yl * cos_a
        upper.append((xu_rot + x_shift, yu_rot + y_shift))
        lower.append((xl_rot + x_shift, yl_rot + y_shift))

    points = upper + list(reversed(lower[1:-1]))
    return [f"{x:.10g}" for x, _ in points], [f"{y:.10g}" for _, y in points]


def box_selection(comp, jint, name: str, entity_dim: int, bounds: dict[str, str], condition: str = "inside") -> None:
    sel = comp.selection().create(name, "Box")
    sel.set("entitydim", jint(entity_dim))
    sel.set("condition", condition)
    for key, value in bounds.items():
        sel.set(key, value)


def explicit_selection(comp, jint, name: str, entity_dim: int, entities: list[int]) -> None:
    sel = comp.selection().create(name, "Explicit")
    sel.geom("geom1", jint(entity_dim))
    sel.set(entities)


def require_selection(comp, name: str, expected: str) -> list[int]:
    entities = [int(item) for item in comp.selection(name).entities()]
    if expected == "one" and len(entities) != 1:
        raise RuntimeError(f"{name} 选择异常，应为 1 个实体，实际为 {entities}")
    if expected == "nonempty" and not entities:
        raise RuntimeError(f"{name} 选择异常，未选中任何实体")
    return entities


def first_scalar(value) -> float:
    while hasattr(value, "__len__") and not isinstance(value, (str, bytes)):
        if len(value) == 0:
            return float("nan")
        value = value[0]
    return float(value)


def create_basic_plots(java_model, solid_domains: list[int], chip_domains: list[int]) -> None:
    """只创建模型内置图组，方便打开 mph 后直接查看。"""
    result = java_model.result()

    pg_preview = result.create("pg_geometry_preview", "PlotGroup3D")
    pg_preview.label("外观检查-铝制翼型柱散热器")
    pg_preview.set("titletype", "none")
    solid_preview = pg_preview.feature().create("solid_preview", "Surface")
    solid_preview.set("expr", "1")
    try_set(solid_preview, "coloring", "uniform")
    try_set(solid_preview, "color", "custom")
    try_set(solid_preview, "customcolor", [0.95, 0.68, 0.22])
    solid_preview.feature().create("sel1", "Selection")
    solid_preview.feature("sel1").selection().geom("geom1", 3)
    solid_preview.feature("sel1").selection().set(solid_domains)
    chip_preview = pg_preview.feature().create("chip_preview", "Surface")
    chip_preview.set("expr", "1")
    try_set(chip_preview, "coloring", "uniform")
    try_set(chip_preview, "color", "custom")
    try_set(chip_preview, "customcolor", [0.1, 0.25, 0.95])
    chip_preview.feature().create("sel1", "Selection")
    chip_preview.feature("sel1").selection().geom("geom1", 3)
    chip_preview.feature("sel1").selection().set(chip_domains)

    pg_temp = result.create("pg_clean_temp", "PlotGroup3D")
    pg_temp.label("温度场-固体表面与中截面")
    pg_temp.set("titletype", "none")
    surf = pg_temp.feature().create("solid_temp", "Surface")
    surf.set("expr", "T")
    surf.set("colortable", "ThermalLight")
    surf.feature().create("sel1", "Selection")
    surf.feature("sel1").selection().geom("geom1", 3)
    surf.feature("sel1").selection().set(solid_domains + chip_domains)
    sl = pg_temp.feature().create("air_slice", "Slice")
    sl.set("expr", "T")
    sl.set("quickplane", "xy")
    sl.set("quickzmethod", "coord")
    sl.set("quickz", "base_h + pillar_h/2")
    sl.set("colortable", "ThermalLight")

    pg_vel = result.create("pg_clean_vel", "PlotGroup3D")
    pg_vel.label("速度场-中截面稀疏矢量")
    pg_vel.set("titletype", "none")
    slv = pg_vel.feature().create("vel_slice", "Slice")
    slv.set("expr", "spf.U")
    slv.set("quickplane", "xy")
    slv.set("quickzmethod", "coord")
    slv.set("quickz", "base_h + pillar_h/2")
    slv.set("colortable", "RainbowLight")
    arrows = pg_vel.feature().create("vel_arrow", "ArrowVolume")
    arrows.set("expr", ["u", "v", "w"])
    arrows.set("xnumber", "20")
    arrows.set("ynumber", "8")
    arrows.set("znumber", "1")
    arrows.set("arrowzmethod", "coord")
    arrows.set("zcoord", "base_h + pillar_h/2")
    arrows.set("scale", "0.65")

    pg_mesh = result.create("pg_mesh_check", "PlotGroup3D")
    pg_mesh.label("Mesh check")
    mesh_plot = pg_mesh.feature().create("meshplot", "Mesh")
    try_set(mesh_plot, "wireframecolor", "black")


def try_set(target, key: str, value: str) -> bool:
    try:
        target.set(key, value)
        return True
    except Exception:
        return False


def configure_quality_mesh(mesh, mesh_hauto: int) -> dict[str, object]:
    applied: list[str] = []
    failed: list[str] = []
    mesh.feature("size").set("hauto", str(mesh_hauto))

    try:
        free_tet = mesh.feature().create("ftet1", "FreeTet")
        free_tet.selection().geom("geom1", 3)
        free_tet.selection().all()
        applied.append("ftet1:all_domains")
    except Exception as exc:
        failed.append(f"ftet1:{exc}")

    def add_size(tag: str, selection_name: str, hmax: str, hmin: str) -> None:
        try:
            size = mesh.feature().create(tag, "Size")
            size.selection().named(selection_name)
            try_set(size, "custom", "on")
            size.set("hmax", hmax)
            size.set("hmin", hmin)
            try_set(size, "hgrad", "1.25")
            try_set(size, "hcurve", "0.25")
            applied.append(f"{tag}:{selection_name}")
        except Exception as exc:
            failed.append(f"{tag}:{exc}")

    if mesh_hauto <= 6:
        add_size("size_air", "sel_air", "2.0[mm]", "0.25[mm]")
        add_size("size_solid", "sel_solid", "0.55[mm]", "0.08[mm]")
        add_size("size_chip", "sel_chip", "0.35[mm]", "0.06[mm]")
    else:
        add_size("size_air", "sel_air", "5.0[mm]", "0.8[mm]")
        add_size("size_solid", "sel_solid", "1.2[mm]", "0.18[mm]")
        add_size("size_chip", "sel_chip", "1.0[mm]", "0.18[mm]")
        applied.append("coarse_validation_mesh:light_local_refinement")
    return {"global_hauto": mesh_hauto, "applied": applied, "failed": failed}


def configure_stationary_solver(java_model) -> dict[str, object]:
    applied: list[str] = []
    failed: list[str] = []
    try:
        sol = java_model.sol("sol1")
    except Exception as exc:
        return {"mode": "auto_sequence_missing", "applied": applied, "failed": [str(exc)]}

    for tag, settings in {
        "st1": {"studystep": "stat"},
        "v1": {"control": "stat"},
        "s1": {"control": "stat", "stol": "1e-4"},
    }.items():
        try:
            feature = sol.feature(tag)
            for key, value in settings.items():
                if try_set(feature, key, value):
                    applied.append(f"{tag}.{key}={value}")
                else:
                    failed.append(f"{tag}.{key}")
        except Exception as exc:
            failed.append(f"{tag}:{exc}")

    return {
        "mode": "stationary_auto_sequence_with_explicit_tolerance",
        "nonlinear_tolerance": "1e-4",
        "max_iterations": "COMSOL default",
        "applied": applied,
        "failed": failed,
    }


def build_case(
    case_name: str,
    mesh_hauto: int,
    solve: bool,
    skip_mesh: bool,
    params_override: dict[str, float] | None = None,
) -> Path:
    import jpype
    import mph

    params = dict(params_override or CASE_PARAMS[case_name])
    out_dir = OUT_ROOT / case_name
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{case_name}_realistic_airfoil_heat_sink.mph"

    log(f"启动 COMSOL: {case_name}")
    client = mph.start()
    try:
        model = client.create(f"RealisticAirfoilHeatSink_{case_name}")
        java = model.java
        jint = jpype.java.lang.Integer
        JStringArray = jpype.JArray(jpype.java.lang.String)
        JIntArray = jpype.JArray(jpype.JInt)

        # 风道和热沉尺寸。单位全部写入 COMSOL 参数，方便手动检查。
        model.parameter("L_channel", "60[mm]")
        model.parameter("W_channel", "28[mm]")
        model.parameter("H_channel", "16[mm]")
        model.parameter("base_l", "36[mm]")
        model.parameter("base_w", "22[mm]")
        model.parameter("base_h", "2.5[mm]")
        model.parameter("L_chip", "18[mm]")
        model.parameter("W_chip", "16[mm]")
        model.parameter("H_chip", "2[mm]")
        model.parameter("chord", "1.8[mm]")
        model.parameter("pillar_h", "7[mm]")
        model.parameter("row_pitch_ref", "5.2[mm]")
        model.parameter("U0", "0.5[m/s]")
        model.parameter("T_in", "293.15[K]")
        model.parameter("P0", "1[W]")
        model.parameter("array_len", "7*(1+Ts)*chord + Tad*chord + chord")
        for key, value in params.items():
            model.parameter(key, str(value))

        log("构建几何参数与翼型柱阵列")
        comp = java.component().create("comp1", True)
        geom = comp.geom().create("geom1", 3)
        geom.lengthUnit("m")

        air = geom.feature().create("air_blk", "Block")
        air.set("size", JStringArray(["L_channel", "W_channel", "H_channel"]))
        air.set("pos", JStringArray(["-L_channel/2", "-W_channel/2", "0"]))

        base = geom.feature().create("base_blk", "Block")
        base.set("size", JStringArray(["base_l", "base_w", "base_h"]))
        base.set("pos", JStringArray(["-base_l/2", "-base_w/2", "0"]))

        chip = geom.feature().create("chip_blk", "Block")
        chip.set("size", JStringArray(["L_chip", "W_chip", "H_chip"]))
        chip.set("pos", JStringArray(["-L_chip/2", "-W_chip/2", "-H_chip"]))

        wp = geom.feature().create("wp_airfoils", "WorkPlane")
        wp.set("quickplane", "xy")
        wp.set("quickz", "base_h")
        wp_geom = wp.geom()

        chord = 0.0018
        row_pitch = params["Tt"] * 0.0052
        array_len = 7 * (1 + params["Ts"]) * chord + params["Tad"] * chord + chord
        x_origin = -array_len / 2
        y_offsets = [-row_pitch, 0.0, row_pitch]
        for row, y_shift in enumerate(y_offsets):
            for col in range(8):
                x_stagger = params["Tad"] * chord if row % 2 == 1 else 0.0
                x_shift = x_origin + col * (1 + params["Ts"]) * chord + x_stagger
                xs, ys = airfoil_points(params, chord, x_shift, y_shift)
                poly = wp_geom.feature().create(f"foil_{row}_{col}", "Polygon")
                poly.set("source", "vectors")
                poly.set("type", "solid")
                poly.set("x", JStringArray(xs))
                poly.set("y", JStringArray(ys))

        ext = geom.feature().create("pillar_ext", "Extrude")
        ext.selection("input").set(JStringArray(["wp_airfoils"]))
        ext.set("distance", "pillar_h")

        air_fluid = geom.feature().create("air_fluid", "Difference")
        air_fluid.selection("input").set(JStringArray(["air_blk"]))
        air_fluid.selection("input2").set(JStringArray(["base_blk", "pillar_ext"]))
        try_set(air_fluid, "keepsubtract", "on")
        try_set(air_fluid, "selresult", "on")
        try_set(air_fluid, "selresultshow", "all")

        log("生成几何")
        geom.run()
        domain_count = int(geom.getNDomains())
        if domain_count < 4:
            raise RuntimeError(f"几何域数量异常: {domain_count}")

        log(f"几何域数量: {domain_count}")
        tol = "2e-6[m]"
        box_selection(comp, jint, "sel_chip", 3, {
            "xmin": "-L_chip/2-" + tol, "xmax": "L_chip/2+" + tol,
            "ymin": "-W_chip/2-" + tol, "ymax": "W_chip/2+" + tol,
            "zmin": "-H_chip-" + tol, "zmax": "0+" + tol,
        })
        chip_domains = require_selection(comp, "sel_chip", "one")
        # 布尔差集后空气域编号不固定；用柱顶上方空气层相交选择来识别真正流体域。
        box_selection(comp, jint, "sel_air", 3, {
            "xmin": "-L_channel/2-" + tol, "xmax": "L_channel/2+" + tol,
            "ymin": "-W_channel/2-" + tol, "ymax": "W_channel/2+" + tol,
            "zmin": "base_h + pillar_h + 0.5[mm]", "zmax": "H_channel+" + tol,
        }, condition="intersects")
        air_domains = require_selection(comp, "sel_air", "nonempty")
        log(f"空气域选择: {air_domains}")
        log(f"芯片域选择: {chip_domains}")
        solid_domains = [
            idx for idx in range(1, domain_count + 1)
            if idx not in set(air_domains + chip_domains)
        ]
        log(f"固体域选择: {solid_domains}")
        explicit_selection(comp, jint, "sel_aluminum", 3, solid_domains)
        explicit_selection(comp, jint, "sel_solid", 3, solid_domains + chip_domains)

        box_selection(comp, jint, "sel_inlet", 2, {
            "xmin": "-L_channel/2-" + tol, "xmax": "-L_channel/2+" + tol,
            "ymin": "-W_channel/2-" + tol, "ymax": "W_channel/2+" + tol,
            "zmin": "0-" + tol, "zmax": "H_channel+" + tol,
        })
        box_selection(comp, jint, "sel_outlet", 2, {
            "xmin": "L_channel/2-" + tol, "xmax": "L_channel/2+" + tol,
            "ymin": "-W_channel/2-" + tol, "ymax": "W_channel/2+" + tol,
            "zmin": "0-" + tol, "zmax": "H_channel+" + tol,
        })
        inlet_boundaries = require_selection(comp, "sel_inlet", "nonempty")
        outlet_boundaries = require_selection(comp, "sel_outlet", "nonempty")

        log("配置材料、传热、流动和非等温耦合")
        comp.material().create("mat_air", "Common")
        comp.material("mat_air").label("Air")
        comp.material("mat_air").materialType("nonSolid")
        comp.material("mat_air").selection().named("sel_air")
        comp.material("mat_air").propertyGroup("def").set("density", "1.2")
        comp.material("mat_air").propertyGroup("def").set("dynamicviscosity", "1.8e-5")
        comp.material("mat_air").propertyGroup("def").set("heatcapacity", "1005")
        comp.material("mat_air").propertyGroup("def").set("thermalconductivity", "0.026")
        comp.material("mat_air").propertyGroup("def").set("ratioofspecificheat", "1.4")
        comp.material("mat_air").propertyGroup("def").set("molarmass", "0.02897[kg/mol]")

        comp.material().create("mat_al", "Common")
        comp.material("mat_al").label("Aluminum 6063")
        try_set(comp.material("mat_al"), "family", "aluminum")
        comp.material("mat_al").materialType("solid")
        comp.material("mat_al").selection().named("sel_aluminum")
        comp.material("mat_al").propertyGroup("def").set("density", "2700")
        comp.material("mat_al").propertyGroup("def").set("heatcapacity", "900")
        comp.material("mat_al").propertyGroup("def").set("thermalconductivity", "201")

        comp.material().create("mat_chip", "Common")
        comp.material("mat_chip").label("Chip equivalent solid")
        try_set(comp.material("mat_chip"), "family", "custom")
        comp.material("mat_chip").materialType("solid")
        comp.material("mat_chip").selection().named("sel_chip")
        comp.material("mat_chip").propertyGroup("def").set("density", "2200")
        comp.material("mat_chip").propertyGroup("def").set("heatcapacity", "730")
        comp.material("mat_chip").propertyGroup("def").set("thermalconductivity", "1.4")

        ht = comp.physics().create("ht", "HeatTransferInSolidsAndFluids", "geom1")
        ht.prop("ShapeProperty").set("order_temperature", "1")
        ht.selection().all()
        ht.feature("fluid1").selection().named("sel_air")
        inflow_heat = ht.create("ifl1", "Inflow", jint(2))
        inflow_heat.selection().set(JIntArray(inlet_boundaries))
        inflow_heat.set("Tustr", "T_in")
        inflow_heat.set("pustr", "1[atm]")
        ht.create("ofl1", "ConvectiveOutflow", jint(2)).selection().set(JIntArray(outlet_boundaries))
        heat = ht.create("hs1", "HeatSource", jint(3))
        heat.selection().named("sel_chip")
        heat.set("heatSourceType", "HeatRate")
        heat.set("P0", "P0")

        spf = comp.physics().create("spf", "LaminarFlow", "geom1")
        spf.selection().named("sel_air")
        # 稳态验证先关闭伪时间步，避免 spf.aveop 在复杂三维空气域选择上生成未网格化平均算子。
        spf.prop("AdvancedSettingProperty").set("UsePseudoTime", "0")
        try:
            spf.feature("init1").set("u", ["U0", "0", "0"])
        except Exception:
            pass
        inlet = spf.create("inl1", "InletBoundary", jint(2))
        inlet.selection().set(JIntArray(inlet_boundaries))
        # 使用普通速度入口，避免 FullyDevelopedFlow 自动入口积分算子在复杂三维选择上初始残差失败。
        inlet.set("U0in", "U0")
        outlet = spf.create("out1", "OutletBoundary", jint(2))
        outlet.selection().set(JIntArray(outlet_boundaries))
        outlet.set("BoundaryCondition", "Pressure")
        outlet.set("p0", "0[Pa]")

        nitf = comp.multiphysics().create("nitf1", "NonIsothermalFlow", jint(3))
        nitf.set("Fluid_physics", "spf")
        nitf.set("Heat_physics", "ht")

        mesh_generated = False
        mesh = comp.mesh().create("mesh1", "geom1")
        mesh_settings = configure_quality_mesh(mesh, mesh_hauto)
        if skip_mesh:
            log("跳过网格生成，仅保存几何与物理场设置")
        else:
            log(f"生成网格: hauto={mesh_hauto}")
            mesh.run()
            mesh_generated = True

        log("创建稳态研究")
        java.study().create("std1")
        java.study("std1").create("stat", "Stationary")
        java.study("std1").feature("stat").setSolveFor("/physics/ht", True)
        java.study("std1").feature("stat").setSolveFor("/physics/spf", True)
        java.study("std1").feature("stat").setSolveFor("/multiphysics/nitf1", True)
        if skip_mesh:
            log("跳过自动求解序列创建")
        else:
            log("创建自动求解序列")
            java.study("std1").createAutoSequences("all")
        solver_settings = configure_stationary_solver(java)
        log("创建模型内置结果图组")
        plot_created = True
        try:
            create_basic_plots(java, solid_domains, chip_domains)
        except Exception as exc:
            plot_created = False
            log(f"结果图组创建失败，已跳过，不影响几何和物理场: {exc}")

        solved = False
        solve_error = None
        if solve:
            log("开始求解")
            try:
                java.sol("sol1").runAll()
                solved = True
            except Exception as exc:
                solve_error = str(exc)
                log(f"求解失败，先保存调试模型: {exc}")

        try:
            log("保存模型")
            model.save(str(out_path))
            saved = out_path
        except Exception:
            saved = out_dir / f"{case_name}_realistic_airfoil_heat_sink_{datetime.now():%Y%m%d_%H%M%S}.mph"
            log(f"默认路径保存失败，改用: {saved}")
            model.save(str(saved))

        notes = {
            "case": case_name,
            "params": params,
            "model_path": str(saved),
            "solved": solved,
            "solve_error": solve_error,
            "mesh_generated": mesh_generated,
            "plot_created": plot_created,
            "mesh_settings": mesh_settings,
            "solver_settings": solver_settings,
            "geometry": {
                "domain_count": domain_count,
                "air_channel": "60 mm x 28 mm x 16 mm",
                "base": "36 mm x 22 mm x 2.5 mm",
                "chip": "18 mm x 16 mm x 2 mm",
                "pillar_array": "3 x 8 airfoil pillars, centered on base; chord 1.8 mm; height 7 mm",
            },
            "boundary_conditions": {
                "inlet": {"selection": inlet_boundaries, "type": "VelocityInlet", "U0": "0.5 m/s", "T": "293.15 K"},
                "outlet": {"selection": outlet_boundaries, "type": "Pressure", "p0": "0 Pa"},
                "heat_source": {"selection": chip_domains, "type": "HeatRate", "P0": "1 W"},
                "other_walls": "COMSOL default no-slip wall / thermal wall treatment in closed channel model",
            },
            "selection_check": {
                "sel_air": air_domains,
                "sel_aluminum": solid_domains,
                "sel_chip": chip_domains,
                "sel_inlet": inlet_boundaries,
                "sel_outlet": outlet_boundaries,
            },
        }
        (out_dir / f"{case_name}_realistic_build_notes.json").write_text(
            json.dumps(notes, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"[INFO] saved: {saved}")
        return saved
    finally:
        try:
            client.disconnect()
        except Exception:
            pass


def main() -> None:
    parser = argparse.ArgumentParser(description="构建真实感更好的三维翼型柱散热器模型。")
    parser.add_argument("--case", choices=list(CASE_PARAMS) + ["custom"], default="baseline")
    parser.add_argument("--case-name", help="自定义工况输出名，仅 --case custom 时使用。")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--mesh-hauto", type=int, default=5)
    parser.add_argument("--skip-mesh", action="store_true", help="只生成几何、材料、物理场和研究，不运行网格。")
    parser.add_argument("--solve", action="store_true")
    for name in PARAM_NAMES:
        parser.add_argument(f"--{name}", type=float)
    args = parser.parse_args()

    if args.all:
        for case_name in CASE_PARAMS:
            command = [sys.executable, str(Path(__file__).resolve()), "--case", case_name, "--mesh-hauto", str(args.mesh_hauto)]
            if args.solve:
                command.append("--solve")
            if args.skip_mesh:
                command.append("--skip-mesh")
            subprocess.run(command, check=True)
        return

    if args.case == "custom":
        missing = [name for name in PARAM_NAMES if getattr(args, name) is None]
        if missing:
            parser.error("--case custom requires: " + ", ".join(f"--{name}" for name in missing))
        params = {name: float(getattr(args, name)) for name in PARAM_NAMES}
        build_case(args.case_name or "custom", args.mesh_hauto, args.solve, args.skip_mesh, params)
        return

    build_case(args.case, args.mesh_hauto, args.solve, args.skip_mesh)


if __name__ == "__main__":
    main()
