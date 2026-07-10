/**
 * COMSOL 平板翅片换热器模型 - Java 代码
 * 
 * 基于 plate_fin_heat_exchanger.mph 导出
 * 生成时间: 2026-06-03
 * 
 * 使用方法:
 * 1. 在 COMSOL Desktop 中创建新模型
 * 2. 打开 Model Builder 的 Java 编辑器
 * 3. 复制此代码并运行
 */

public class PlateFinHeatExchanger {
    
    public static void buildModel(Model model) {
        // ========== 1. 设置全局参数 ==========
        model.param().set("L_he", "Nb_sep*dist_sep", "Heat exchanger length");
        model.param().set("W_he", "77[mm]", "Heat exchanger width");
        model.param().set("H_he", "Nu*h_row", "Heat exchanger height");
        model.param().set("h_row", "hplate+2*hfin", "Unit row height");
        model.param().set("Nu", "8", "Number of rows");
        model.param().set("hplate", "2[mm]", "Oil plate height");
        model.param().set("hfin", "10[mm]", "Fin height");
        model.param().set("dist_sep", "5[mm]", "Distance between fins");
        model.param().set("Nb_sep", "45", "Number of fins per row");
        model.param().set("fin_th", "5e-4[m]", "Fins thickness");
        model.param().set("r0", "1[cm]", "Oil inlet & outlet radius");
        model.param().set("w_casing", "3[mm]", "Casing thickness");
        
        // 操作参数
        model.param().set("Th", "70[degC]", "Hot oil inlet temperature");
        model.param().set("Tc", "20[degC]", "Cold air inlet temperature");
        model.param().set("V0", "1[gal/min]", "Oil inlet flowrate");
        model.param().set("u0", "V0/(pi*r0^2)", "Oil inlet velocity");
        model.param().set("uacfm", "100[cfm]", "Air inlet flowrate");
        model.param().set("ua_v", "uacfm/396[cm^2]", "Air inlet velocity");
        model.param().set("Re_oil", "u0*hplate*860[kg/m^3]/0.02[Pa*s]", 
                         "Oil inlet Reynolds number");
        model.param().set("ua", "1[m/s]", "Initial air velocity");
        
        // ========== 2. 创建组件 ==========
        Component comp = model.component().create("comp1", true);
        
        // ========== 3. 构建几何 (geom1) ==========
        GeomSequence geom = comp.geom().create("geom1", 3);
        geom.lengthUnit("m");
        
        // 注意：这里需要根据实际几何重建
        // 原模型有 16 个几何特征，包括：
        // - 外壳 (Casing)
        // - 油道板 (Oil plates)
        // - 翅片阵列 (Fin arrays)
        // - 进出口管道 (Inlet/Outlet pipes)
        
        // 示例：创建外壳
        Block casing = geom.feature().create("casing", "Block");
        casing.set("size", new String[]{"L_he", "W_he", "H_he"});
        casing.set("pos", new String[]{"0", "0", "0"});
        
        // 示例：创建油道板（需要循环创建 Nu 个）
        for (int i = 0; i < Nu; i++) {
            String plateTag = "plate" + i;
            Block plate = geom.feature().create(plateTag, "Block");
            plate.set("size", new String[]{"L_he", "W_he", "hplate"});
            plate.set("pos", new String[]{"0", "0", String.valueOf(i * h_row)});
        }
        
        // 示例：创建翅片（需要循环创建 Nb_sep * Nu 个）
        for (int row = 0; row < Nu; row++) {
            for (int col = 0; col < Nb_sep; col++) {
                String finTag = "fin_r" + row + "_c" + col;
                Block fin = geom.feature().create(finTag, "Block");
                fin.set("size", new String[]{"L_he", "fin_th", "hfin"});
                double xPos = col * dist_sep;
                double zPos = row * h_row + hplate;
                fin.set("pos", new String[]{String.valueOf(xPos), "0", String.valueOf(zPos)});
            }
        }
        
        // 布尔运算：从外壳中减去翅片和油道
        Difference fluidDomain = geom.feature().create("fluid", "Difference");
        fluidDomain.selection("input").set(new String[]{"casing"});
        fluidDomain.selection("input2").set(new String[]{"plate*", "fin*"});
        
        geom.run();
        
        // ========== 4. 定义材料 ==========
        
        // 空气材料
        Material air = comp.material().create("mat1", "Common");
        air.label("Air");
        air.selection().all();  // 应用到流体域
        air.propertyGroup("def").set("thermalexpansioncoefficient", "alpha_p(pA,T)");
        air.propertyGroup("def").set("molarmass", "0.02897[kg/mol]");
        air.propertyGroup("def").set("bulkviscosity", "muB(T)");
        air.propertyGroup("def").set("relpermeability", "1");
        air.propertyGroup("def").set("relpermittivity", "1");
        // ... 其他空气属性
        
        // 发动机油材料
        Material oil = comp.material().create("mat2", "Common");
        oil.label("Engine Oil");
        oil.selection().named("oil_domain");  // 需要创建选择
        oil.propertyGroup("def").set("dynamicviscosity", "eta(T)");
        oil.propertyGroup("def").set("heatcapacity", "Cp(T)");
        oil.propertyGroup("def").set("density", "rho(T)");
        oil.propertyGroup("def").set("thermalconductivity", "k(T)");
        
        // 铝材料
        Material aluminum = comp.material().create("mat3", "Common");
        aluminum.label("Aluminum, Boundary Material");
        aluminum.selection().named("solid_domain");  // 需要创建选择
        aluminum.propertyGroup("def").set("relpermeability", "1");
        aluminum.propertyGroup("def").set("heatcapacity", "900[J/(kg*K)]");
        aluminum.propertyGroup("def").set("thermalconductivity", "238[W/(m*K)]");
        aluminum.propertyGroup("def").set("electricconductivity", "3.774e7[S/m]");
        aluminum.propertyGroup("def").set("relpermittivity", "1");
        
        // 多孔材料
        Material porous = comp.material().create("pmat1", "PorousMaterial");
        porous.label("Porous Material 1");
        porous.propertyGroup("def").set("hydraulicpermeability", "1e-8");
        
        // 外壳材料
        Material casingMat = comp.material().create("mat5", "Common");
        casingMat.label("Casing");
        
        // ========== 5. 添加物理场 ==========
        
        // 传热物理场
        Physics ht = comp.physics().create("ht", "HeatTransferInSolidsAndFluids", "geom1");
        ht.label("Heat Transfer in Solids and Fluids");
        
        // 传热特征（15个）- 需要根据实际情况配置
        // - 初始温度
        // - 入口温度边界
        // - 出口对流边界
        // - 壁面热绝缘
        // - 热源（如果有）
        // - 对称边界
        // 等等...
        
        // 流动物理场（推测）
        Physics spf = comp.physics().create("spf", "LaminarFlow", "geom1");
        spf.label("Laminar Flow");
        
        // 非等温流耦合（推测）
        MultiPhysics nitf = comp.multiphysics().create("nitf1", "NonIsothermalFlow", 3);
        
        // ========== 6. 网格划分 ==========
        Mesh mesh = comp.mesh().create("mesh1", "geom1");
        
        // 自由四面体网格
        FreeTetrahedral freeTet = mesh.feature().create("ftet1", "FreeTet");
        
        // 尺寸设置
        Size size = mesh.feature().create("size1", "Size");
        size.set("hauto", 4);  // 中等网格
        
        // 局部加密（如果需要）
        // SizeBoundaryLayer sbl = mesh.feature().create("sbl1", "BoundaryLayer");
        
        mesh.run();
        
        // ========== 7. 研究配置 ==========
        Study study = model.study().create("std1");
        study.label("Study 1");
        
        // 稳态研究步骤
        Stationary stat = study.create("stat", "Stationary");
        stat.label("Stationary");
        
        // ========== 8. 求解器配置 ==========
        SolverSequence sol = model.sol().create("sol1");
        
        // 稳态求解器
        StationarySolver statSol = sol.create("stat1", "Stationary");
        
        // 直接求解器或迭代求解器
        // PARDISO 或 MUMPS
        
        // ========== 9. 后处理算子 ==========
        
        // 平均算子 - 入口
        Average aveIn = comp.cpl().create("ave_in", "Average");
        aveIn.selection().geom("geom1", 2);
        aveIn.selection().named("inlet_boundary");
        
        // 平均算子 - 出口
        Average aveOut = comp.cpl().create("ave_out", "Average");
        aveOut.selection().geom("geom1", 2);
        aveOut.selection().named("outlet_boundary");
        
        // 积分算子 - 换热量计算
        Integration intHeat = comp.cpl().create("int_heat", "Integration");
        intHeat.selection().geom("geom1", 3);
        intHeat.selection().named("fluid_domain");
        
        System.out.println("模型构建完成！");
    }
    
    public static void main(String[] args) {
        // 启动 COMSOL
        Model model = ModelUtil.create("Model");
        
        // 构建模型
        buildModel(model);
        
        // 保存模型
        model.save("plate_fin_heat_exchanger_rebuilt.mph");
        
        System.out.println("模型已保存！");
    }
}
