/*
 * plate_fin_heat_exchanger.java
 */

import com.comsol.model.*;
import com.comsol.model.util.*;

/** Model exported on Jun 3 2026, 18:23 by COMSOL 6.3.0.290. */
public class plate_fin_heat_exchanger {

  public static Model run() {
    Model model = ModelUtil.create("Model");

    model.modelPath("F:\\\u6d4f\u89c8\u5668\u7f51\u76d8\u4e0b\u8f7d\u4f4d\u7f6e\\IDM");

    model.label("plate_fin_heat_exchanger.mph");

    model.component().create("comp1", true);

    model.component("comp1").geom().create("geom1", 3);

    model.param().label("Parameters 1: Geometry");
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
    model.param().group().create("par2");
    model.param("par2").label("Parameters 2: Physics");
    model.param("par2").set("Th", "70[degC]", "Hot oil inlet temperature");
    model.param("par2").set("Tc", "20[degC]", "Cold air inlet temperature");
    model.param("par2").set("V0", "1[gal/min]", "Oil inlet flowrate");
    model.param("par2").set("u0", "V0/(pi*r0^2)", "Oil inlet velocity");
    model.param("par2").set("uacfm", "100[cfm]", "Air inlet flowrate");
    model.param("par2").set("ua_v", "uacfm/396[cm^2]", "Air inlet velocity");
    model.param("par2").set("Re_oil", "u0*hplate*860[kg/m^3]/0.02[Pa*s]", "Oil inlet Reynolds number");
    model.param("par2").set("ua", "1[m/s]", "Initial air velocity");

    model.component("comp1").geom("geom1").lengthUnit("cm");
    model.component("comp1").geom("geom1").geomRep("cadps");
    model.component("comp1").geom("geom1").selection().create("csel1", "CumulativeSelection");
    model.component("comp1").geom("geom1").selection("csel1").label("Fins");
    model.component("comp1").geom("geom1").selection().create("csel2", "CumulativeSelection");
    model.component("comp1").geom("geom1").selection("csel2").label("Air");
    model.component("comp1").geom("geom1").selection().create("csel3", "CumulativeSelection");
    model.component("comp1").geom("geom1").selection("csel3").label("Oil");
    model.component("comp1").geom("geom1").create("blk1", "Block");
    model.component("comp1").geom("geom1").feature("blk1").set("contributeto", "csel2");
    model.component("comp1").geom("geom1").feature("blk1").set("size", new String[]{"L_he", "W_he", "hfin"});
    model.component("comp1").geom("geom1").create("blk2", "Block");
    model.component("comp1").geom("geom1").feature("blk2").set("contributeto", "csel3");
    model.component("comp1").geom("geom1").feature("blk2").set("pos", new String[]{"0", "0", "hfin"});
    model.component("comp1").geom("geom1").feature("blk2").set("size", new String[]{"L_he", "W_he", "hplate"});
    model.component("comp1").geom("geom1").create("blk3", "Block");
    model.component("comp1").geom("geom1").feature("blk3").set("contributeto", "csel2");
    model.component("comp1").geom("geom1").feature("blk3").set("pos", new String[]{"0", "0", "hplate+hfin"});
    model.component("comp1").geom("geom1").feature("blk3").set("size", new String[]{"L_he", "W_he", "hfin"});
    model.component("comp1").geom("geom1").create("wp1", "WorkPlane");
    model.component("comp1").geom("geom1").feature("wp1").set("planetype", "faceparallel");
    model.component("comp1").geom("geom1").feature("wp1").set("origin", "boxcorner");
    model.component("comp1").geom("geom1").feature("wp1").set("faceparallelaxis", "s2");
    model.component("comp1").geom("geom1").feature("wp1").set("unite", true);
    model.component("comp1").geom("geom1").feature("wp1").selection("face").set("blk1(1)", 3);
    model.component("comp1").geom("geom1").feature("wp1").geom().create("pol1", "Polygon");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol1").set("type", "open");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol1").set("source", "table");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol1")
         .set("table", new double[][]{{0.5, 1}, {0.5, 0}});
    model.component("comp1").geom("geom1").feature("wp1").geom().create("arr1", "Array");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("arr1")
         .set("fullsize", new String[]{"Nb_sep", "2"});
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("arr1")
         .set("displ", new String[]{"dist_sep", "hfin+hplate"});
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("arr1").selection("input").set("pol1");
    model.component("comp1").geom("geom1").create("ext1", "Extrude");
    model.component("comp1").geom("geom1").feature("ext1").set("contributeto", "csel1");
    model.component("comp1").geom("geom1").feature("ext1").set("specify", "vertices");
    model.component("comp1").geom("geom1").feature("ext1").selection("input").set("wp1");
    model.component("comp1").geom("geom1").feature("ext1").selection("vertex").set("blk3(1)", 7);
    model.component("comp1").geom("geom1").create("arr1", "Array");
    model.component("comp1").geom("geom1").feature("arr1").set("fullsize", new String[]{"1", "1", "Nu"});
    model.component("comp1").geom("geom1").feature("arr1").set("displ", new String[]{"0", "0", "h_row"});
    model.component("comp1").geom("geom1").feature("arr1").selection("input").set("blk1", "blk2", "blk3", "ext1");
    model.component("comp1").geom("geom1").create("blk4", "Block");
    model.component("comp1").geom("geom1").feature("blk4").set("contributeto", "csel2");
    model.component("comp1").geom("geom1").feature("blk4").set("pos", new String[]{"0", "W_he", "0"});
    model.component("comp1").geom("geom1").feature("blk4").set("size", new String[]{"L_he", "W_he", "H_he"});
    model.component("comp1").geom("geom1").create("blk5", "Block");
    model.component("comp1").geom("geom1").feature("blk5").set("contributeto", "csel2");
    model.component("comp1").geom("geom1").feature("blk5").set("pos", new String[]{"0", "-W_he", "0"});
    model.component("comp1").geom("geom1").feature("blk5").set("size", new String[]{"L_he", "W_he", "H_he"});
    model.component("comp1").geom("geom1").create("blk6", "Block");
    model.component("comp1").geom("geom1").feature("blk6").set("pos", new double[]{-1.5, 0, 0});
    model.component("comp1").geom("geom1").feature("blk6")
         .set("size", new String[]{"1.5", "W_he", "(hplate+hfin*2)*Nu"});
    model.component("comp1").geom("geom1").create("blk7", "Block");
    model.component("comp1").geom("geom1").feature("blk7").set("pos", new String[]{"L_he", "0", "0"});
    model.component("comp1").geom("geom1").feature("blk7")
         .set("size", new String[]{"1.5", "W_he", "(hplate+hfin*2)*Nu"});
    model.component("comp1").geom("geom1").feature("blk7").set("layername", new String[]{"Couche 1"});
    model.component("comp1").geom("geom1").feature("blk7").setIndex("layer", "(hplate+hfin*2)*Nu/2", 0);
    model.component("comp1").geom("geom1").create("wp2", "WorkPlane");
    model.component("comp1").geom("geom1").feature("wp2").set("planetype", "faceparallel");
    model.component("comp1").geom("geom1").feature("wp2").set("reverse", true);
    model.component("comp1").geom("geom1").feature("wp2").set("origin", "vertexproj");
    model.component("comp1").geom("geom1").feature("wp2").set("unite", true);
    model.component("comp1").geom("geom1").feature("wp2").selection("face").set("blk7(1)", 10);
    model.component("comp1").geom("geom1").feature("wp2").selection("originvertex").set("blk7(1)", 10);
    model.component("comp1").geom("geom1").feature("wp2").geom().create("c1", "Circle");
    model.component("comp1").geom("geom1").feature("wp2").geom().feature("c1")
         .set("pos", new String[]{"W_he/2", "(hplate+hfin*2)*Nu*(1-1/5)"});
    model.component("comp1").geom("geom1").feature("wp2").geom().feature("c1")
         .set("layername", new String[]{"Layer 1"});
    model.component("comp1").geom("geom1").feature("wp2").geom().feature("c1").setIndex("layer", "w_casing", 0);
    model.component("comp1").geom("geom1").feature("wp2").geom().feature("c1").set("r", "r0+w_casing");
    model.component("comp1").geom("geom1").feature("wp2").geom().create("c2", "Circle");
    model.component("comp1").geom("geom1").feature("wp2").geom().feature("c2")
         .set("pos", new String[]{"W_he/2", "(hplate+hfin*2)*Nu*1/5"});
    model.component("comp1").geom("geom1").feature("wp2").geom().feature("c2")
         .set("layername", new String[]{"Layer 1"});
    model.component("comp1").geom("geom1").feature("wp2").geom().feature("c2").setIndex("layer", "w_casing", 0);
    model.component("comp1").geom("geom1").feature("wp2").geom().feature("c2").set("r", "r0+w_casing");
    model.component("comp1").geom("geom1").create("ext2", "Extrude");
    model.component("comp1").geom("geom1").feature("ext2").setIndex("distance", "1.5", 0);
    model.component("comp1").geom("geom1").feature("ext2").set("reverse", true);
    model.component("comp1").geom("geom1").feature("ext2").selection("input").set("wp2");
    model.component("comp1").geom("geom1").create("blk8", "Block");
    model.component("comp1").geom("geom1").feature("blk8")
         .set("pos", new String[]{"-1.5-w_casing", "-w_casing", "-w_casing"});
    model.component("comp1").geom("geom1").feature("blk8")
         .set("size", new String[]{"L_he+2*1.5+2*w_casing", "W_he+2*w_casing", "H_he+2*w_casing"});
    model.component("comp1").geom("geom1").feature("blk8").set("layername", new String[]{"Layer 1"});
    model.component("comp1").geom("geom1").feature("blk8").setIndex("layer", "w_casing", 0);
    model.component("comp1").geom("geom1").feature("blk8").set("layerleft", true);
    model.component("comp1").geom("geom1").feature("blk8").set("layerright", true);
    model.component("comp1").geom("geom1").feature("blk8").set("layerfront", true);
    model.component("comp1").geom("geom1").feature("blk8").set("layerback", true);
    model.component("comp1").geom("geom1").feature("blk8").set("layertop", true);
    model.component("comp1").geom("geom1").create("uni1", "Union");
    model.component("comp1").geom("geom1").feature("uni1").selection("input")
         .set("arr1", "blk4", "blk5", "blk6", "blk7", "blk8", "ext2");
    model.component("comp1").geom("geom1").create("del1", "Delete");
    model.component("comp1").geom("geom1").feature("del1").selection("input").set("uni1(1)", 72, 176);
    model.component("comp1").geom("geom1").nodeGroup().create("grp1");
    model.component("comp1").geom("geom1").nodeGroup("grp1").label("Casing");
    model.component("comp1").geom("geom1").nodeGroup("grp1").placeAfter("ext2");
    model.component("comp1").geom("geom1").nodeGroup("grp1").add("blk8");
    model.component("comp1").geom("geom1").nodeGroup("grp1").add("uni1");
    model.component("comp1").geom("geom1").nodeGroup("grp1").add("del1");
    model.component("comp1").geom("geom1").run();

    model.component("comp1").selection().create("sel1", "Explicit");
    model.component("comp1").selection("sel1").label("Separators");
    model.component("comp1").selection("sel1").geom("geom1", 2);
    model.component("comp1").selection("sel1")
         .set(85, 94, 103, 112, 121, 130, 139, 187, 194, 201, 208, 215, 222, 229, 260, 267, 274, 281, 288, 295, 302, 333, 340, 347, 354, 361, 368, 375, 406, 413, 420, 427, 434, 441, 448, 479, 486, 493, 500, 507, 514, 521, 552, 559, 566, 573, 580, 587, 594, 625, 632, 639, 646, 653, 660, 667, 698, 705, 712, 719, 726, 733, 740, 771, 778, 785, 792, 799, 806, 813, 844, 851, 858, 865, 872, 879, 886, 917, 924, 931, 938, 945, 952, 959, 990, 997, 1004, 1011, 1018, 1025, 1032, 1063, 1070, 1077, 1084, 1091, 1098, 1105, 1136, 1143, 1150, 1157, 1164, 1171, 1178, 1209, 1216, 1223, 1230, 1237, 1244, 1251, 1282, 1289, 1296, 1303, 1310, 1317, 1324, 1355, 1362, 1369, 1376, 1383, 1390, 1397, 1428, 1435, 1442, 1449, 1456, 1463, 1470, 1501, 1508, 1515, 1522, 1529, 1536, 1543, 1574, 1581, 1588, 1595, 1602, 1609, 1616, 1647, 1654, 1661, 1668, 1675, 1682, 1689, 1720, 1727, 1734, 1741, 1748, 1755, 1762, 1793, 1800, 1807, 1814, 1821, 1828, 1835, 1866, 1873, 1880, 1887, 1894, 1901, 1908, 1939, 1946, 1953, 1960, 1967, 1974, 1981, 2012, 2019, 2026, 2033, 2040, 2047, 2054, 2085, 2092, 2099, 2106, 2113, 2120, 2127, 2158, 2165, 2172, 2179, 2186, 2193, 2200, 2231, 2238, 2245, 2252, 2259, 2266, 2273, 2304, 2311, 2318, 2325, 2332, 2339, 2346, 2377, 2384, 2391, 2398, 2405, 2412, 2419, 2450, 2457, 2464, 2471, 2478, 2485, 2492, 2523, 2530, 2537, 2544, 2551, 2558, 2565, 2596, 2603, 2610, 2617, 2624, 2631, 2638, 2669, 2676, 2683, 2690, 2697, 2704, 2711, 2742, 2749, 2756, 2763, 2770, 2777, 2784, 2815, 2822, 2829, 2836, 2843, 2850, 2857, 2888, 2895, 2902, 2909, 2916, 2923, 2930, 2961, 2968, 2975, 2982, 2989, 2996, 3003, 3034, 3041, 3048, 3055, 3062, 3069, 3076, 3107, 3114, 3121, 3128, 3135, 3142, 3149, 3180, 3187, 3194, 3201, 3208, 3215, 3222, 3253, 3260, 3267, 3274, 3281, 3288, 3295, 3326, 3333, 3340, 3347, 3354, 3361, 3368, 3411);
    model.component("comp1").selection("sel1").set("groupcontang", true);
    model.component("comp1").selection().create("sel2", "Explicit");
    model.component("comp1").selection("sel2").label("Oil, Inlet");
    model.component("comp1").selection("sel2").geom("geom1", 2);
    model.component("comp1").selection("sel2").set(3547);
    model.component("comp1").selection().create("sel3", "Explicit");
    model.component("comp1").selection("sel3").label("Oil, Outlet");
    model.component("comp1").selection("sel3").geom("geom1", 2);
    model.component("comp1").selection("sel3").set(3546);
    model.component("comp1").selection().create("uni1", "Union");
    model.component("comp1").selection("uni1").label("Oil, Inlet & Outlet");
    model.component("comp1").selection("uni1").set("entitydim", 2);
    model.component("comp1").selection("uni1").set("input", new String[]{"sel2", "sel3"});
    model.component("comp1").selection().create("sel4", "Explicit");
    model.component("comp1").selection("sel4").label("Oil, All Domains");
    model.component("comp1").selection("sel4").set(14, 21, 24, 27, 30, 33, 36, 39, 42, 750, 751, 763, 764, 776, 777);
    model.component("comp1").selection().create("sel5", "Explicit");
    model.component("comp1").selection("sel5").label("Oil, Non-Porous Domains");
    model.component("comp1").selection("sel5").set(14, 750, 751, 763, 764, 776, 777);
    model.component("comp1").selection().create("dif1", "Difference");
    model.component("comp1").selection("dif1").label("Oil, Porous Domains");
    model.component("comp1").selection("dif1").set("add", new String[]{"sel4"});
    model.component("comp1").selection("dif1").set("subtract", new String[]{"sel5"});
    model.component("comp1").selection().create("uni2", "Union");
    model.component("comp1").selection("uni2").label("Fluid, Non-Porous Domains");
    model.component("comp1").selection("uni2").set("input", new String[]{"geom1_csel2_dom", "sel5"});
    model.component("comp1").selection().create("sel6", "Explicit");
    model.component("comp1").selection("sel6").label("Oil, Walls");
    model.component("comp1").selection("sel6").geom("geom1", 2);
    model.component("comp1").selection("sel6")
         .set(47, 48, 49, 52, 58, 74, 80, 83, 89, 92, 98, 101, 107, 110, 116, 119, 125, 128, 134, 137, 143, 3395, 3396, 3397, 3399, 3400, 3402, 3403, 3405, 3406, 3408, 3409, 3410, 3411, 3413, 3414, 3416, 3417, 3419, 3420, 3422, 3423, 3425, 3427, 3444, 3447, 3452, 3453, 3457, 3458, 3463, 3464, 3466, 3467, 3468, 3471, 3472, 3474, 3476, 3479, 3480, 3482, 3516, 3517, 3519, 3520, 3524, 3527, 3532, 3535);
    model.component("comp1").selection().create("uni3", "Union");
    model.component("comp1").selection("uni3").label("Oil, All Walls");
    model.component("comp1").selection("uni3").set("entitydim", 2);
    model.component("comp1").selection("uni3").set("input", new String[]{"geom1_csel3_bnd", "sel6"});
    model.component("comp1").selection().create("sel7", "Explicit");
    model.component("comp1").selection("sel7").label("Air, Inlet");
    model.component("comp1").selection("sel7").geom("geom1", 2);
    model.component("comp1").selection("sel7").set(68);
    model.component("comp1").selection().create("sel8", "Explicit");
    model.component("comp1").selection("sel8").label("Air, Outlet");
    model.component("comp1").selection("sel8").geom("geom1", 2);
    model.component("comp1").selection("sel8").set(177);
    model.component("comp1").selection().create("sel9", "Explicit");
    model.component("comp1").selection("sel9").label("Air, Walls");
    model.component("comp1").selection("sel9").geom("geom1", 2);
    model.component("comp1").selection("sel9")
         .set(67, 69, 70, 71, 72, 73, 74, 76, 80, 83, 89, 92, 98, 101, 107, 110, 116, 119, 125, 128, 134, 137, 143, 146, 147, 149, 173, 174, 175, 176, 180, 234, 253, 307, 326, 380, 399, 453, 472, 526, 545, 599, 618, 672, 691, 745, 764, 818, 837, 891, 910, 964, 983, 1037, 1056, 1110, 1129, 1183, 1202, 1256, 1275, 1329, 1348, 1402, 1421, 1475, 1494, 1548, 1567, 1621, 1640, 1694, 1713, 1767, 1786, 1840, 1859, 1913, 1932, 1986, 2005, 2059, 2078, 2132, 2151, 2205, 2224, 2278, 2297, 2351, 2370, 2424, 2443, 2497, 2516, 2570, 2589, 2643, 2662, 2716, 2735, 2789, 2808, 2862, 2881, 2935, 2954, 3008, 3027, 3081, 3100, 3154, 3173, 3227, 3246, 3300, 3319, 3373, 3390, 3391, 3395, 3399, 3400, 3402, 3403, 3405, 3406, 3408, 3409, 3413, 3414, 3416, 3417, 3419, 3420, 3422, 3424, 3429);
    model.component("comp1").selection().create("uni4", "Union");
    model.component("comp1").selection("uni4").label("Air, All Walls");
    model.component("comp1").selection("uni4").set("entitydim", 2);
    model.component("comp1").selection("uni4")
         .set("input", new String[]{"sel9", "geom1_csel3_bnd", "sel1", "geom1_csel1_bnd"});
    model.component("comp1").selection().create("sel10", "Explicit");
    model.component("comp1").selection("sel10").label("Interior Fins");
    model.component("comp1").selection("sel10").geom("geom1", 2);
    model.component("comp1").selection("sel10")
         .set(178, 182, 185, 189, 192, 196, 199, 203, 206, 210, 213, 217, 220, 224, 227, 231, 251, 255, 258, 262, 265, 269, 272, 276, 279, 283, 286, 290, 293, 297, 300, 304, 324, 328, 331, 335, 338, 342, 345, 349, 352, 356, 359, 363, 366, 370, 373, 377, 397, 401, 404, 408, 411, 415, 418, 422, 425, 429, 432, 436, 439, 443, 446, 450, 470, 474, 477, 481, 484, 488, 491, 495, 498, 502, 505, 509, 512, 516, 519, 523, 543, 547, 550, 554, 557, 561, 564, 568, 571, 575, 578, 582, 585, 589, 592, 596, 616, 620, 623, 627, 630, 634, 637, 641, 644, 648, 651, 655, 658, 662, 665, 669, 689, 693, 696, 700, 703, 707, 710, 714, 717, 721, 724, 728, 731, 735, 738, 742, 762, 766, 769, 773, 776, 780, 783, 787, 790, 794, 797, 801, 804, 808, 811, 815, 835, 839, 842, 846, 849, 853, 856, 860, 863, 867, 870, 874, 877, 881, 884, 888, 908, 912, 915, 919, 922, 926, 929, 933, 936, 940, 943, 947, 950, 954, 957, 961, 981, 985, 988, 992, 995, 999, 1002, 1006, 1009, 1013, 1016, 1020, 1023, 1027, 1030, 1034, 1054, 1058, 1061, 1065, 1068, 1072, 1075, 1079, 1082, 1086, 1089, 1093, 1096, 1100, 1103, 1107, 1127, 1131, 1134, 1138, 1141, 1145, 1148, 1152, 1155, 1159, 1162, 1166, 1169, 1173, 1176, 1180, 1200, 1204, 1207, 1211, 1214, 1218, 1221, 1225, 1228, 1232, 1235, 1239, 1242, 1246, 1249, 1253, 1273, 1277, 1280, 1284, 1287, 1291, 1294, 1298, 1301, 1305, 1308, 1312, 1315, 1319, 1322, 1326, 1346, 1350, 1353, 1357, 1360, 1364, 1367, 1371, 1374, 1378, 1381, 1385, 1388, 1392, 1395, 1399, 1419, 1423, 1426, 1430, 1433, 1437, 1440, 1444, 1447, 1451, 1454, 1458, 1461, 1465, 1468, 1472, 1492, 1496, 1499, 1503, 1506, 1510, 1513, 1517, 1520, 1524, 1527, 1531, 1534, 1538, 1541, 1545, 1565, 1569, 1572, 1576, 1579, 1583, 1586, 1590, 1593, 1597, 1600, 1604, 1607, 1611, 1614, 1618, 1638, 1642, 1645, 1649, 1652, 1656, 1659, 1663, 1666, 1670, 1673, 1677, 1680, 1684, 1687, 1691, 1711, 1715, 1718, 1722, 1725, 1729, 1732, 1736, 1739, 1743, 1746, 1750, 1753, 1757, 1760, 1764, 1784, 1788, 1791, 1795, 1798, 1802, 1805, 1809, 1812, 1816, 1819, 1823, 1826, 1830, 1833, 1837, 1857, 1861, 1864, 1868, 1871, 1875, 1878, 1882, 1885, 1889, 1892, 1896, 1899, 1903, 1906, 1910, 1930, 1934, 1937, 1941, 1944, 1948, 1951, 1955, 1958, 1962, 1965, 1969, 1972, 1976, 1979, 1983, 2003, 2007, 2010, 2014, 2017, 2021, 2024, 2028, 2031, 2035, 2038, 2042, 2045, 2049, 2052, 2056, 2076, 2080, 2083, 2087, 2090, 2094, 2097, 2101, 2104, 2108, 2111, 2115, 2118, 2122, 2125, 2129, 2149, 2153, 2156, 2160, 2163, 2167, 2170, 2174, 2177, 2181, 2184, 2188, 2191, 2195, 2198, 2202, 2222, 2226, 2229, 2233, 2236, 2240, 2243, 2247, 2250, 2254, 2257, 2261, 2264, 2268, 2271, 2275, 2295, 2299, 2302, 2306, 2309, 2313, 2316, 2320, 2323, 2327, 2330, 2334, 2337, 2341, 2344, 2348, 2368, 2372, 2375, 2379, 2382, 2386, 2389, 2393, 2396, 2400, 2403, 2407, 2410, 2414, 2417, 2421, 2441, 2445, 2448, 2452, 2455, 2459, 2462, 2466, 2469, 2473, 2476, 2480, 2483, 2487, 2490, 2494, 2514, 2518, 2521, 2525, 2528, 2532, 2535, 2539, 2542, 2546, 2549, 2553, 2556, 2560, 2563, 2567, 2587, 2591, 2594, 2598, 2601, 2605, 2608, 2612, 2615, 2619, 2622, 2626, 2629, 2633, 2636, 2640, 2660, 2664, 2667, 2671, 2674, 2678, 2681, 2685, 2688, 2692, 2695, 2699, 2702, 2706, 2709, 2713, 2733, 2737, 2740, 2744, 2747, 2751, 2754, 2758, 2761, 2765, 2768, 2772, 2775, 2779, 2782, 2786, 2806, 2810, 2813, 2817, 2820, 2824, 2827, 2831, 2834, 2838, 2841, 2845, 2848, 2852, 2855, 2859, 2879, 2883, 2886, 2890, 2893, 2897, 2900, 2904, 2907, 2911, 2914, 2918, 2921, 2925, 2928, 2932, 2952, 2956, 2959, 2963, 2966, 2970, 2973, 2977, 2980, 2984, 2987, 2991, 2994, 2998, 3001, 3005, 3025, 3029, 3032, 3036, 3039, 3043, 3046, 3050, 3053, 3057, 3060, 3064, 3067, 3071, 3074, 3078, 3098, 3102, 3105, 3109, 3112, 3116, 3119, 3123, 3126, 3130, 3133, 3137, 3140, 3144, 3147, 3151, 3171, 3175, 3178, 3182, 3185, 3189, 3192, 3196, 3199, 3203, 3206, 3210, 3213, 3217, 3220, 3224, 3244, 3248, 3251, 3255, 3258, 3262, 3265, 3269, 3272, 3276, 3279, 3283, 3286, 3290, 3293, 3297, 3317, 3321, 3324, 3328, 3331, 3335, 3338, 3342, 3345, 3349, 3352, 3356, 3359, 3363, 3366, 3370);
    model.component("comp1").selection().create("sel11", "Explicit");
    model.component("comp1").selection("sel11").label("Aluminum, All Boundaries");
    model.component("comp1").selection("sel11").geom("geom1", 2);
    model.component("comp1").selection("sel11")
         .set(74, 78, 79, 80, 82, 83, 85, 87, 88, 89, 91, 92, 94, 96, 97, 98, 100, 101, 103, 105, 106, 107, 109, 110, 112, 114, 115, 116, 118, 119, 121, 123, 124, 125, 127, 128, 130, 132, 133, 134, 136, 137, 139, 141, 142, 143, 145, 150, 153, 156, 159, 162, 165, 168, 171, 178, 181, 182, 184, 185, 187, 188, 189, 191, 192, 194, 195, 196, 198, 199, 201, 202, 203, 205, 206, 208, 209, 210, 212, 213, 215, 216, 217, 219, 220, 222, 223, 224, 226, 227, 229, 230, 231, 233, 251, 254, 255, 257, 258, 260, 261, 262, 264, 265, 267, 268, 269, 271, 272, 274, 275, 276, 278, 279, 281, 282, 283, 285, 286, 288, 289, 290, 292, 293, 295, 296, 297, 299, 300, 302, 303, 304, 306, 324, 327, 328, 330, 331, 333, 334, 335, 337, 338, 340, 341, 342, 344, 345, 347, 348, 349, 351, 352, 354, 355, 356, 358, 359, 361, 362, 363, 365, 366, 368, 369, 370, 372, 373, 375, 376, 377, 379, 397, 400, 401, 403, 404, 406, 407, 408, 410, 411, 413, 414, 415, 417, 418, 420, 421, 422, 424, 425, 427, 428, 429, 431, 432, 434, 435, 436, 438, 439, 441, 442, 443, 445, 446, 448, 449, 450, 452, 470, 473, 474, 476, 477, 479, 480, 481, 483, 484, 486, 487, 488, 490, 491, 493, 494, 495, 497, 498, 500, 501, 502, 504, 505, 507, 508, 509, 511, 512, 514, 515, 516, 518, 519, 521, 522, 523, 525, 543, 546, 547, 549, 550, 552, 553, 554, 556, 557, 559, 560, 561, 563, 564, 566, 567, 568, 570, 571, 573, 574, 575, 577, 578, 580, 581, 582, 584, 585, 587, 588, 589, 591, 592, 594, 595, 596, 598, 616, 619, 620, 622, 623, 625, 626, 627, 629, 630, 632, 633, 634, 636, 637, 639, 640, 641, 643, 644, 646, 647, 648, 650, 651, 653, 654, 655, 657, 658, 660, 661, 662, 664, 665, 667, 668, 669, 671, 689, 692, 693, 695, 696, 698, 699, 700, 702, 703, 705, 706, 707, 709, 710, 712, 713, 714, 716, 717, 719, 720, 721, 723, 724, 726, 727, 728, 730, 731, 733, 734, 735, 737, 738, 740, 741, 742, 744, 762, 765, 766, 768, 769, 771, 772, 773, 775, 776, 778, 779, 780, 782, 783, 785, 786, 787, 789, 790, 792, 793, 794, 796, 797, 799, 800, 801, 803, 804, 806, 807, 808, 810, 811, 813, 814, 815, 817, 835, 838, 839, 841, 842, 844, 845, 846, 848, 849, 851, 852, 853, 855, 856, 858, 859, 860, 862, 863, 865, 866, 867, 869, 870, 872, 873, 874, 876, 877, 879, 880, 881, 883, 884, 886, 887, 888, 890, 908, 911, 912, 914, 915, 917, 918, 919, 921, 922, 924, 925, 926, 928, 929, 931, 932, 933, 935, 936, 938, 939, 940, 942, 943, 945, 946, 947, 949, 950, 952, 953, 954, 956, 957, 959, 960, 961, 963, 981, 984, 985, 987, 988, 990, 991, 992, 994, 995, 997, 998, 999, 1001, 1002, 1004, 1005, 1006, 1008, 1009, 1011, 1012, 1013, 1015, 1016, 1018, 1019, 1020, 1022, 1023, 1025, 1026, 1027, 1029, 1030, 1032, 1033, 1034, 1036, 1054, 1057, 1058, 1060, 1061, 1063, 1064, 1065, 1067, 1068, 1070, 1071, 1072, 1074, 1075, 1077, 1078, 1079, 1081, 1082, 1084, 1085, 1086, 1088, 1089, 1091, 1092, 1093, 1095, 1096, 1098, 1099, 1100, 1102, 1103, 1105, 1106, 1107, 1109, 1127, 1130, 1131, 1133, 1134, 1136, 1137, 1138, 1140, 1141, 1143, 1144, 1145, 1147, 1148, 1150, 1151, 1152, 1154, 1155, 1157, 1158, 1159, 1161, 1162, 1164, 1165, 1166, 1168, 1169, 1171, 1172, 1173, 1175, 1176, 1178, 1179, 1180, 1182, 1200, 1203, 1204, 1206, 1207, 1209, 1210, 1211, 1213, 1214, 1216, 1217, 1218, 1220, 1221, 1223, 1224, 1225, 1227, 1228, 1230, 1231, 1232, 1234, 1235, 1237, 1238, 1239, 1241, 1242, 1244, 1245, 1246, 1248, 1249, 1251, 1252, 1253, 1255, 1273, 1276, 1277, 1279, 1280, 1282, 1283, 1284, 1286, 1287, 1289, 1290, 1291, 1293, 1294, 1296, 1297, 1298, 1300, 1301, 1303, 1304, 1305, 1307, 1308, 1310, 1311, 1312, 1314, 1315, 1317, 1318, 1319, 1321, 1322, 1324, 1325, 1326, 1328, 1346, 1349, 1350, 1352, 1353, 1355, 1356, 1357, 1359, 1360, 1362, 1363, 1364, 1366, 1367, 1369, 1370, 1371, 1373, 1374, 1376, 1377, 1378, 1380, 1381, 1383, 1384, 1385, 1387, 1388, 1390, 1391, 1392, 1394, 1395, 1397, 1398, 1399, 1401, 1419, 1422, 1423, 1425, 1426, 1428, 1429, 1430, 1432, 1433, 1435, 1436, 1437, 1439, 1440, 1442, 1443, 1444, 1446, 1447, 1449, 1450, 1451, 1453, 1454, 1456, 1457, 1458, 1460, 1461, 1463, 1464, 1465, 1467, 1468, 1470, 1471, 1472, 1474, 1492, 1495, 1496, 1498, 1499, 1501, 1502, 1503, 1505, 1506, 1508, 1509, 1510, 1512, 1513, 1515, 1516, 1517, 1519, 1520, 1522, 1523, 1524, 1526, 1527, 1529, 1530, 1531, 1533, 1534, 1536, 1537, 1538, 1540, 1541, 1543, 1544, 1545, 1547, 1565, 1568, 1569, 1571, 1572, 1574, 1575, 1576, 1578, 1579, 1581, 1582, 1583, 1585, 1586, 1588, 1589, 1590, 1592, 1593, 1595, 1596, 1597, 1599, 1600, 1602, 1603, 1604, 1606, 1607, 1609, 1610, 1611, 1613, 1614, 1616, 1617, 1618, 1620, 1638, 1641, 1642, 1644, 1645, 1647, 1648, 1649, 1651, 1652, 1654, 1655, 1656, 1658, 1659, 1661, 1662, 1663, 1665, 1666, 1668, 1669, 1670, 1672, 1673, 1675, 1676, 1677, 1679, 1680, 1682, 1683, 1684, 1686, 1687, 1689, 1690, 1691, 1693, 1711, 1714, 1715, 1717, 1718, 1720, 1721, 1722, 1724, 1725, 1727, 1728, 1729, 1731, 1732, 1734, 1735, 1736, 1738, 1739, 1741, 1742, 1743, 1745, 1746, 1748, 1749, 1750, 1752, 1753, 1755, 1756, 1757, 1759, 1760, 1762, 1763, 1764, 1766, 1784, 1787, 1788, 1790, 1791, 1793, 1794, 1795, 1797, 1798, 1800, 1801, 1802, 1804, 1805, 1807, 1808, 1809, 1811, 1812, 1814, 1815, 1816, 1818, 1819, 1821, 1822, 1823, 1825, 1826, 1828, 1829, 1830, 1832, 1833, 1835, 1836, 1837, 1839, 1857, 1860, 1861, 1863, 1864, 1866, 1867, 1868, 1870, 1871, 1873, 1874, 1875, 1877, 1878, 1880, 1881, 1882, 1884, 1885, 1887, 1888, 1889, 1891, 1892, 1894, 1895, 1896, 1898, 1899, 1901, 1902, 1903, 1905, 1906, 1908, 1909, 1910, 1912, 1930, 1933, 1934, 1936, 1937, 1939, 1940, 1941, 1943, 1944, 1946, 1947, 1948, 1950, 1951, 1953, 1954, 1955, 1957, 1958, 1960, 1961, 1962, 1964, 1965, 1967, 1968, 1969, 1971, 1972, 1974, 1975, 1976, 1978, 1979, 1981, 1982, 1983, 1985, 2003, 2006, 2007, 2009, 2010, 2012, 2013, 2014, 2016, 2017, 2019, 2020, 2021, 2023, 2024, 2026, 2027, 2028, 2030, 2031, 2033, 2034, 2035, 2037, 2038, 2040, 2041, 2042, 2044, 2045, 2047, 2048, 2049, 2051, 2052, 2054, 2055, 2056, 2058, 2076, 2079, 2080, 2082, 2083, 2085, 2086, 2087, 2089, 2090, 2092, 2093, 2094, 2096, 2097, 2099, 2100, 2101, 2103, 2104, 2106, 2107, 2108, 2110, 2111, 2113, 2114, 2115, 2117, 2118, 2120, 2121, 2122, 2124, 2125, 2127, 2128, 2129, 2131, 2149, 2152, 2153, 2155, 2156, 2158, 2159, 2160, 2162, 2163, 2165, 2166, 2167, 2169, 2170, 2172, 2173, 2174, 2176, 2177, 2179, 2180, 2181, 2183, 2184, 2186, 2187, 2188, 2190, 2191, 2193, 2194, 2195, 2197, 2198, 2200, 2201, 2202, 2204, 2222, 2225, 2226, 2228, 2229, 2231, 2232, 2233, 2235, 2236, 2238, 2239, 2240, 2242, 2243, 2245, 2246, 2247, 2249, 2250, 2252, 2253, 2254, 2256, 2257, 2259, 2260, 2261, 2263, 2264, 2266, 2267, 2268, 2270, 2271, 2273, 2274, 2275, 2277, 2295, 2298, 2299, 2301, 2302, 2304, 2305, 2306, 2308, 2309, 2311, 2312, 2313, 2315, 2316, 2318, 2319, 2320, 2322, 2323, 2325, 2326, 2327, 2329, 2330, 2332, 2333, 2334, 2336, 2337, 2339, 2340, 2341, 2343, 2344, 2346, 2347, 2348, 2350, 2368, 2371, 2372, 2374, 2375, 2377, 2378, 2379, 2381, 2382, 2384, 2385, 2386, 2388, 2389, 2391, 2392, 2393, 2395, 2396, 2398, 2399, 2400, 2402, 2403, 2405, 2406, 2407, 2409, 2410, 2412, 2413, 2414, 2416, 2417, 2419, 2420, 2421, 2423, 2441, 2444, 2445, 2447, 2448, 2450, 2451, 2452, 2454, 2455, 2457, 2458, 2459, 2461, 2462, 2464, 2465, 2466, 2468, 2469, 2471, 2472, 2473, 2475, 2476, 2478, 2479, 2480, 2482, 2483, 2485, 2486, 2487, 2489, 2490, 2492, 2493, 2494, 2496, 2514, 2517, 2518, 2520, 2521, 2523, 2524, 2525, 2527, 2528, 2530, 2531, 2532, 2534, 2535, 2537, 2538, 2539, 2541, 2542, 2544, 2545, 2546, 2548, 2549, 2551, 2552, 2553, 2555, 2556, 2558, 2559, 2560, 2562, 2563, 2565, 2566, 2567, 2569, 2587, 2590, 2591, 2593, 2594, 2596, 2597, 2598, 2600, 2601, 2603, 2604, 2605, 2607, 2608, 2610, 2611, 2612, 2614, 2615, 2617, 2618, 2619, 2621, 2622, 2624, 2625, 2626, 2628, 2629, 2631, 2632, 2633, 2635, 2636, 2638, 2639, 2640, 2642, 2660, 2663, 2664, 2666, 2667, 2669, 2670, 2671, 2673, 2674, 2676, 2677, 2678, 2680, 2681, 2683, 2684, 2685, 2687, 2688, 2690, 2691, 2692, 2694, 2695, 2697, 2698, 2699, 2701, 2702, 2704, 2705, 2706, 2708, 2709, 2711, 2712, 2713, 2715, 2733, 2736, 2737, 2739, 2740, 2742, 2743, 2744, 2746, 2747, 2749, 2750, 2751, 2753, 2754, 2756, 2757, 2758, 2760, 2761, 2763, 2764, 2765, 2767, 2768, 2770, 2771, 2772, 2774, 2775, 2777, 2778, 2779, 2781, 2782, 2784, 2785, 2786, 2788, 2806, 2809, 2810, 2812, 2813, 2815, 2816, 2817, 2819, 2820, 2822, 2823, 2824, 2826, 2827, 2829, 2830, 2831, 2833, 2834, 2836, 2837, 2838, 2840, 2841, 2843, 2844, 2845, 2847, 2848, 2850, 2851, 2852, 2854, 2855, 2857, 2858, 2859, 2861, 2879, 2882, 2883, 2885, 2886, 2888, 2889, 2890, 2892, 2893, 2895, 2896, 2897, 2899, 2900, 2902, 2903, 2904, 2906, 2907, 2909, 2910, 2911, 2913, 2914, 2916, 2917, 2918, 2920, 2921, 2923, 2924, 2925, 2927, 2928, 2930, 2931, 2932, 2934, 2952, 2955, 2956, 2958, 2959, 2961, 2962, 2963, 2965, 2966, 2968, 2969, 2970, 2972, 2973, 2975, 2976, 2977, 2979, 2980, 2982, 2983, 2984, 2986, 2987, 2989, 2990, 2991, 2993, 2994, 2996, 2997, 2998, 3000, 3001, 3003, 3004, 3005, 3007, 3025, 3028, 3029, 3031, 3032, 3034, 3035, 3036, 3038, 3039, 3041, 3042, 3043, 3045, 3046, 3048, 3049, 3050, 3052, 3053, 3055, 3056, 3057, 3059, 3060, 3062, 3063, 3064, 3066, 3067, 3069, 3070, 3071, 3073, 3074, 3076, 3077, 3078, 3080, 3098, 3101, 3102, 3104, 3105, 3107, 3108, 3109, 3111, 3112, 3114, 3115, 3116, 3118, 3119, 3121, 3122, 3123, 3125, 3126, 3128, 3129, 3130, 3132, 3133, 3135, 3136, 3137, 3139, 3140, 3142, 3143, 3144, 3146, 3147, 3149, 3150, 3151, 3153, 3171, 3174, 3175, 3177, 3178, 3180, 3181, 3182, 3184, 3185, 3187, 3188, 3189, 3191, 3192, 3194, 3195, 3196, 3198, 3199, 3201, 3202, 3203, 3205, 3206, 3208, 3209, 3210, 3212, 3213, 3215, 3216, 3217, 3219, 3220, 3222, 3223, 3224, 3226, 3244, 3247, 3248, 3250, 3251, 3253, 3254, 3255, 3257, 3258, 3260, 3261, 3262, 3264, 3265, 3267, 3268, 3269, 3271, 3272, 3274, 3275, 3276, 3278, 3279, 3281, 3282, 3283, 3285, 3286, 3288, 3289, 3290, 3292, 3293, 3295, 3296, 3297, 3299, 3317, 3320, 3321, 3323, 3324, 3326, 3327, 3328, 3330, 3331, 3333, 3334, 3335, 3337, 3338, 3340, 3341, 3342, 3344, 3345, 3347, 3348, 3349, 3351, 3352, 3354, 3355, 3356, 3358, 3359, 3361, 3362, 3363, 3365, 3366, 3368, 3369, 3370, 3372, 3395, 3399, 3400, 3402, 3403, 3405, 3406, 3408, 3409, 3411, 3413, 3414, 3416, 3417, 3419, 3420, 3422);

    return model;
  }

  public static Model run2(Model model) {
    model.component("comp1").selection().create("sel12", "Explicit");
    model.component("comp1").selection("sel12").label("Casing");
    model.component("comp1").selection("sel12")
         .set(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 15, 16, 17, 18, 749, 752, 753, 754, 755, 756, 757, 758, 759, 760, 761, 762, 765, 766, 767, 768, 769, 770, 771, 772, 773, 774, 775, 778, 779, 780, 781);
    model.component("comp1").selection().create("sel13", "Explicit");
    model.component("comp1").selection("sel13").label("All Domains");
    model.component("comp1").selection("sel13")
         .set(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181, 182, 183, 184, 185, 186, 187, 188, 189, 190, 191, 192, 193, 194, 195, 196, 197, 198, 199, 200, 201, 202, 203, 204, 205, 206, 207, 208, 209, 210, 211, 212, 213, 214, 215, 216, 217, 218, 219, 220, 221, 222, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 233, 234, 235, 236, 237, 238, 239, 240, 241, 242, 243, 244, 245, 246, 247, 248, 249, 250, 251, 252, 253, 254, 255, 256, 257, 258, 259, 260, 261, 262, 263, 264, 265, 266, 267, 268, 269, 270, 271, 272, 273, 274, 275, 276, 277, 278, 279, 280, 281, 282, 283, 284, 285, 286, 287, 288, 289, 290, 291, 292, 293, 294, 295, 296, 297, 298, 299, 300, 301, 302, 303, 304, 305, 306, 307, 308, 309, 310, 311, 312, 313, 314, 315, 316, 317, 318, 319, 320, 321, 322, 323, 324, 325, 326, 327, 328, 329, 330, 331, 332, 333, 334, 335, 336, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 360, 361, 362, 363, 364, 365, 366, 367, 368, 369, 370, 371, 372, 373, 374, 375, 376, 377, 378, 379, 380, 381, 382, 383, 384, 385, 386, 387, 388, 389, 390, 391, 392, 393, 394, 395, 396, 397, 398, 399, 400, 401, 402, 403, 404, 405, 406, 407, 408, 409, 410, 411, 412, 413, 414, 415, 416, 417, 418, 419, 420, 421, 422, 423, 424, 425, 426, 427, 428, 429, 430, 431, 432, 433, 434, 435, 436, 437, 438, 439, 440, 441, 442, 443, 444, 445, 446, 447, 448, 449, 450, 451, 452, 453, 454, 455, 456, 457, 458, 459, 460, 461, 462, 463, 464, 465, 466, 467, 468, 469, 470, 471, 472, 473, 474, 475, 476, 477, 478, 479, 480, 481, 482, 483, 484, 485, 486, 487, 488, 489, 490, 491, 492, 493, 494, 495, 496, 497, 498, 499, 500, 501, 502, 503, 504, 505, 506, 507, 508, 509, 510, 511, 512, 513, 514, 515, 516, 517, 518, 519, 520, 521, 522, 523, 524, 525, 526, 527, 528, 529, 530, 531, 532, 533, 534, 535, 536, 537, 538, 539, 540, 541, 542, 543, 544, 545, 546, 547, 548, 549, 550, 551, 552, 553, 554, 555, 556, 557, 558, 559, 560, 561, 562, 563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 573, 574, 575, 576, 577, 578, 579, 580, 581, 582, 583, 584, 585, 586, 587, 588, 589, 590, 591, 592, 593, 594, 595, 596, 597, 598, 599, 600, 601, 602, 603, 604, 605, 606, 607, 608, 609, 610, 611, 612, 613, 614, 615, 616, 617, 618, 619, 620, 621, 622, 623, 624, 625, 626, 627, 628, 629, 630, 631, 632, 633, 634, 635, 636, 637, 638, 639, 640, 641, 642, 643, 644, 645, 646, 647, 648, 649, 650, 651, 652, 653, 654, 655, 656, 657, 658, 659, 660, 661, 662, 663, 664, 665, 666, 667, 668, 669, 670, 671, 672, 673, 674, 675, 676, 677, 678, 679, 680, 681, 682, 683, 684, 685, 686, 687, 688, 689, 690, 691, 692, 693, 694, 695, 696, 697, 698, 699, 700, 701, 702, 703, 704, 705, 706, 707, 708, 709, 710, 711, 712, 713, 714, 715, 716, 717, 718, 719, 720, 721, 722, 723, 724, 725, 726, 727, 728, 729, 730, 731, 732, 733, 734, 735, 736, 737, 738, 739, 740, 741, 742, 743, 744, 745, 746, 747, 748, 749, 750, 751, 752, 753, 754, 755, 756, 757, 758, 759, 760, 761, 762, 763, 764, 765, 766, 767, 768, 769, 770, 771, 772, 773, 774, 775, 776, 777, 778, 779, 780, 781);
    model.component("comp1").selection().create("dif2", "Difference");
    model.component("comp1").selection("dif2").label("Heat Transfer Domains");
    model.component("comp1").selection("dif2").set("add", new String[]{"sel13"});
    model.component("comp1").selection("dif2").set("subtract", new String[]{"sel12"});

    model.component("comp1").physics().create("ht", "HeatTransferInSolidsAndFluids", "geom1");
    model.component("comp1").physics("ht").selection().named("dif2");
    model.component("comp1").physics("ht").feature("init1").set("Tinit", "20[degC]");
    model.component("comp1").physics("ht").feature("fluid1").selection().named("uni2");
    model.component("comp1").physics("ht").create("porous1", "PorousMediumHeatTransferModel", 3);
    model.component("comp1").physics("ht").feature("porous1").selection().named("dif1");
    model.component("comp1").physics("ht").feature("porous1").set("EffectiveConductivity", "WrappedScreen");
    model.component("comp1").physics("ht").create("ifl1", "Inflow", 2);
    model.component("comp1").physics("ht").feature("ifl1").label("Inflow Oil");
    model.component("comp1").physics("ht").feature("ifl1").selection().named("sel2");
    model.component("comp1").physics("ht").feature("ifl1").set("Tustr", "Th");
    model.component("comp1").physics("ht").create("ofl1", "ConvectiveOutflow", 2);
    model.component("comp1").physics("ht").feature("ofl1").label("Outflow Oil");
    model.component("comp1").physics("ht").feature("ofl1").selection().named("sel3");
    model.component("comp1").physics("ht").create("ifl2", "Inflow", 2);
    model.component("comp1").physics("ht").feature("ifl2").label("Inflow Air");
    model.component("comp1").physics("ht").feature("ifl2").selection().named("sel7");
    model.component("comp1").physics("ht").feature("ifl2").set("Tustr", "Tc");
    model.component("comp1").physics("ht").create("ofl2", "ConvectiveOutflow", 2);
    model.component("comp1").physics("ht").feature("ofl2").label("Outflow Air");
    model.component("comp1").physics("ht").feature("ofl2").selection().named("sel8");
    model.component("comp1").physics("ht").create("sls1", "SolidLayeredShell", 2);
    model.component("comp1").physics("ht").feature("sls1").selection().named("sel11");
    model.component("comp1").physics("ht").feature("sls1").set("shelllist", "none");
    model.component("comp1").physics("ht").feature("sls1").set("LayerType", "Conductive");
    model.component("comp1").physics("ht").feature("sls1").set("UserDefThicknessLayerType", "Conductive");
    model.component("comp1").physics("ht").feature("sls1").set("lth", "fin_th");
    model.component("comp1").physics().create("spf", "TurbulentFlowlowRekeps", "geom1");
    model.component("comp1").physics("spf").selection().named("geom1_csel2_dom");
    model.component("comp1").physics("spf").feature("init1").set("u_init", new String[][]{{"0"}, {"ua"}, {"0"}});
    model.component("comp1").physics("spf").create("inl1", "InletBoundary", 2);
    model.component("comp1").physics("spf").feature("inl1").selection().named("sel7");
    model.component("comp1").physics("spf").feature("inl1").set("U0in", "ua_v");
    model.component("comp1").physics("spf").create("out1", "OutletBoundary", 2);
    model.component("comp1").physics("spf").feature("out1").selection().named("sel8");
    model.component("comp1").physics("spf").create("iwbc1", "InteriorWallBC", 2);
    model.component("comp1").physics("spf").feature("iwbc1").selection().named("sel11");
    model.component("comp1").physics().create("fp", "FreeAndPorousMediaFlow", "geom1");
    model.component("comp1").physics("fp").selection().named("sel4");
    model.component("comp1").physics("fp").create("inl1", "InletBoundary", 2);
    model.component("comp1").physics("fp").feature("inl1").selection().named("sel2");
    model.component("comp1").physics("fp").feature("inl1").set("BoundaryCondition", "FullyDevelopedFlow");
    model.component("comp1").physics("fp").feature("inl1").set("FullyDevelopedFlowOption", "V0");
    model.component("comp1").physics("fp").feature("inl1").set("V0fdf", "V0");
    model.component("comp1").physics("fp").create("out1", "OutletBoundary", 2);
    model.component("comp1").physics("fp").feature("out1").selection().named("sel3");
    model.component("comp1").physics("fp").create("porous1", "PorousMedium", 3);
    model.component("comp1").physics("fp").feature("porous1").selection().named("dif1");
    model.component("comp1").physics("fp").create("iwbc1", "InteriorWallBC", 2);
    model.component("comp1").physics("fp").feature("iwbc1").selection().set(3411);

    model.component("comp1").multiphysics().create("nitf1", "NonIsothermalFlow", 3);
    model.component("comp1").multiphysics("nitf1").set("Fluid_physics", "fp");
    model.component("comp1").multiphysics().create("nitf2", "NonIsothermalFlow", 3);

    model.component("comp1").material().create("mat1", "Common");
    model.component("comp1").material("mat1").label("Air");
    model.component("comp1").material("mat1").selection().named("geom1_csel2_dom");
    model.component("comp1").material("mat1").propertyGroup("def").func().create("eta", "Piecewise");
    model.component("comp1").material("mat1").propertyGroup("def").func().create("Cp", "Piecewise");
    model.component("comp1").material("mat1").propertyGroup("def").func().create("rho", "Analytic");
    model.component("comp1").material("mat1").propertyGroup("def").func().create("k", "Piecewise");
    model.component("comp1").material("mat1").propertyGroup("def").func().create("cs", "Analytic");
    model.component("comp1").material("mat1").propertyGroup("def").func().create("an1", "Analytic");
    model.component("comp1").material("mat1").propertyGroup("def").func().create("an2", "Analytic");
    model.component("comp1").material("mat1").propertyGroup().create("RefractiveIndex", "Refractive index");
    model.component("comp1").material("mat1").propertyGroup().create("NonlinearModel", "Nonlinear model");
    model.component("comp1").material("mat1").propertyGroup().create("idealGas", "Ideal gas");
    model.component("comp1").material("mat1").propertyGroup("idealGas").func().create("Cp", "Piecewise");
    model.component("comp1").material("mat1").propertyGroup("def").func("eta").set("arg", "T");
    model.component("comp1").material("mat1").propertyGroup("def").func("eta")
         .set("pieces", new String[][]{{"200.0", "1600.0", "-8.38278E-7+8.35717342E-8*T^1-7.69429583E-11*T^2+4.6437266E-14*T^3-1.06585607E-17*T^4"}});
    model.component("comp1").material("mat1").propertyGroup("def").func("eta").set("argunit", "K");
    model.component("comp1").material("mat1").propertyGroup("def").func("eta").set("fununit", "Pa*s");
    model.component("comp1").material("mat1").propertyGroup("def").func("Cp").set("arg", "T");
    model.component("comp1").material("mat1").propertyGroup("def").func("Cp")
         .set("pieces", new String[][]{{"200.0", "1600.0", "1047.63657-0.372589265*T^1+9.45304214E-4*T^2-6.02409443E-7*T^3+1.2858961E-10*T^4"}});
    model.component("comp1").material("mat1").propertyGroup("def").func("Cp").set("argunit", "K");
    model.component("comp1").material("mat1").propertyGroup("def").func("Cp").set("fununit", "J/(kg*K)");
    model.component("comp1").material("mat1").propertyGroup("def").func("rho")
         .set("expr", "pA*0.02897/R_const[K*mol/J]/T");
    model.component("comp1").material("mat1").propertyGroup("def").func("rho").set("args", new String[]{"pA", "T"});
    model.component("comp1").material("mat1").propertyGroup("def").func("rho").set("fununit", "kg/m^3");
    model.component("comp1").material("mat1").propertyGroup("def").func("rho")
         .set("argunit", new String[]{"Pa", "K"});
    model.component("comp1").material("mat1").propertyGroup("def").func("rho")
         .set("plotargs", new String[][]{{"pA", "101325", "101325"}, {"T", "273.15", "293.15"}});
    model.component("comp1").material("mat1").propertyGroup("def").func("k").set("arg", "T");
    model.component("comp1").material("mat1").propertyGroup("def").func("k")
         .set("pieces", new String[][]{{"200.0", "1600.0", "-0.00227583562+1.15480022E-4*T^1-7.90252856E-8*T^2+4.11702505E-11*T^3-7.43864331E-15*T^4"}});
    model.component("comp1").material("mat1").propertyGroup("def").func("k").set("argunit", "K");
    model.component("comp1").material("mat1").propertyGroup("def").func("k").set("fununit", "W/(m*K)");
    model.component("comp1").material("mat1").propertyGroup("def").func("cs")
         .set("expr", "sqrt(1.4*R_const[K*mol/J]/0.02897*T)");
    model.component("comp1").material("mat1").propertyGroup("def").func("cs").set("args", new String[]{"T"});
    model.component("comp1").material("mat1").propertyGroup("def").func("cs").set("fununit", "m/s");
    model.component("comp1").material("mat1").propertyGroup("def").func("cs").set("argunit", new String[]{"K"});
    model.component("comp1").material("mat1").propertyGroup("def").func("cs")
         .set("plotargs", new String[][]{{"T", "273.15", "373.15"}});
    model.component("comp1").material("mat1").propertyGroup("def").func("an1").set("funcname", "alpha_p");
    model.component("comp1").material("mat1").propertyGroup("def").func("an1")
         .set("expr", "-1/rho(pA,T)*d(rho(pA,T),T)");
    model.component("comp1").material("mat1").propertyGroup("def").func("an1").set("args", new String[]{"pA", "T"});
    model.component("comp1").material("mat1").propertyGroup("def").func("an1").set("fununit", "1/K");
    model.component("comp1").material("mat1").propertyGroup("def").func("an1")
         .set("argunit", new String[]{"Pa", "K"});
    model.component("comp1").material("mat1").propertyGroup("def").func("an1")
         .set("plotargs", new String[][]{{"pA", "101325", "101325"}, {"T", "273.15", "373.15"}});
    model.component("comp1").material("mat1").propertyGroup("def").func("an2").set("funcname", "muB");
    model.component("comp1").material("mat1").propertyGroup("def").func("an2").set("expr", "0.6*eta(T)");
    model.component("comp1").material("mat1").propertyGroup("def").func("an2").set("args", new String[]{"T"});
    model.component("comp1").material("mat1").propertyGroup("def").func("an2").set("fununit", "Pa*s");
    model.component("comp1").material("mat1").propertyGroup("def").func("an2").set("argunit", new String[]{"K"});
    model.component("comp1").material("mat1").propertyGroup("def").func("an2")
         .set("plotargs", new String[][]{{"T", "200", "1600"}});
    model.component("comp1").material("mat1").propertyGroup("def").set("thermalexpansioncoefficient", "");
    model.component("comp1").material("mat1").propertyGroup("def").set("molarmass", "");
    model.component("comp1").material("mat1").propertyGroup("def").set("bulkviscosity", "");
    model.component("comp1").material("mat1").propertyGroup("def")
         .set("thermalexpansioncoefficient", new String[]{"alpha_p(pA,T)", "0", "0", "0", "alpha_p(pA,T)", "0", "0", "0", "alpha_p(pA,T)"});
    model.component("comp1").material("mat1").propertyGroup("def").set("molarmass", "0.02897[kg/mol]");
    model.component("comp1").material("mat1").propertyGroup("def").set("bulkviscosity", "muB(T)");
    model.component("comp1").material("mat1").propertyGroup("def")
         .set("relpermeability", new String[]{"1", "0", "0", "0", "1", "0", "0", "0", "1"});
    model.component("comp1").material("mat1").propertyGroup("def")
         .set("relpermittivity", new String[]{"1", "0", "0", "0", "1", "0", "0", "0", "1"});
    model.component("comp1").material("mat1").propertyGroup("def").set("dynamicviscosity", "eta(T)");
    model.component("comp1").material("mat1").propertyGroup("def").set("ratioofspecificheat", "1.4");
    model.component("comp1").material("mat1").propertyGroup("def")
         .set("electricconductivity", new String[]{"0[S/m]", "0", "0", "0", "0[S/m]", "0", "0", "0", "0[S/m]"});
    model.component("comp1").material("mat1").propertyGroup("def").set("heatcapacity", "Cp(T)");
    model.component("comp1").material("mat1").propertyGroup("def").set("density", "rho(pA,T)");
    model.component("comp1").material("mat1").propertyGroup("def")
         .set("thermalconductivity", new String[]{"k(T)", "0", "0", "0", "k(T)", "0", "0", "0", "k(T)"});
    model.component("comp1").material("mat1").propertyGroup("def").set("soundspeed", "cs(T)");
    model.component("comp1").material("mat1").propertyGroup("def").addInput("temperature");
    model.component("comp1").material("mat1").propertyGroup("def").addInput("pressure");
    model.component("comp1").material("mat1").propertyGroup("RefractiveIndex")
         .set("n", new String[]{"1", "0", "0", "0", "1", "0", "0", "0", "1"});
    model.component("comp1").material("mat1").propertyGroup("NonlinearModel").set("BA", "(def.gamma+1)/2");
    model.component("comp1").material("mat1").propertyGroup("idealGas").func("Cp").label("Piecewise 2");
    model.component("comp1").material("mat1").propertyGroup("idealGas").func("Cp").set("arg", "T");
    model.component("comp1").material("mat1").propertyGroup("idealGas").func("Cp")
         .set("pieces", new String[][]{{"200.0", "1600.0", "1047.63657-0.372589265*T^1+9.45304214E-4*T^2-6.02409443E-7*T^3+1.2858961E-10*T^4"}});
    model.component("comp1").material("mat1").propertyGroup("idealGas").func("Cp").set("argunit", "K");
    model.component("comp1").material("mat1").propertyGroup("idealGas").func("Cp").set("fununit", "J/(kg*K)");
    model.component("comp1").material("mat1").propertyGroup("idealGas").set("Rs", "R_const/Mn");
    model.component("comp1").material("mat1").propertyGroup("idealGas").set("heatcapacity", "Cp(T)");
    model.component("comp1").material("mat1").propertyGroup("idealGas").set("ratioofspecificheat", "1.4");
    model.component("comp1").material("mat1").propertyGroup("idealGas").set("molarmass", "0.02897");
    model.component("comp1").material("mat1").propertyGroup("idealGas").addInput("temperature");
    model.component("comp1").material("mat1").propertyGroup("idealGas").addInput("pressure");
    model.component("comp1").material("mat1").materialType("nonSolid");
    model.component("comp1").material("mat1").set("family", "custom");
    model.component("comp1").material("mat1").set("alpha", 0.2);
    model.component("comp1").material("mat1").set("fresnel", 0);
    model.component("comp1").material().create("mat2", "Common");
    model.component("comp1").material("mat2").label("Engine Oil");
    model.component("comp1").material("mat2").selection().named("sel5");
    model.component("comp1").material("mat2").propertyGroup("def").func().create("eta", "Piecewise");
    model.component("comp1").material("mat2").propertyGroup("def").func().create("Cp", "Piecewise");
    model.component("comp1").material("mat2").propertyGroup("def").func().create("rho", "Piecewise");
    model.component("comp1").material("mat2").propertyGroup("def").func().create("k", "Piecewise");
    model.component("comp1").material("mat2").propertyGroup("def").func("eta").set("arg", "T");
    model.component("comp1").material("mat2").propertyGroup("def").func("eta")
         .set("pieces", new String[][]{{"273.0", "353.0", "42669.28688622-741.1718801282*T^1+5.360521287088*T^2-0.02066027676164*T^3+4.47491538052E-5*T^4-5.164053479202E-8*T^5+2.48033770504E-11*T^6"}, {"353.0", "433.0", "4.94593941-0.0351869631*T^1+8.37935977E-5*T^2-6.67125E-8*T^3"}});
    model.component("comp1").material("mat2").propertyGroup("def").func("eta").set("argunit", "K");
    model.component("comp1").material("mat2").propertyGroup("def").func("eta").set("fununit", "Pa*s");
    model.component("comp1").material("mat2").propertyGroup("def").func("Cp").set("arg", "T");
    model.component("comp1").material("mat2").propertyGroup("def").func("Cp")
         .set("pieces", new String[][]{{"273.0", "433.0", "761.405625+3.47685606*T^1+0.00115530303*T^2"}});
    model.component("comp1").material("mat2").propertyGroup("def").func("Cp").set("argunit", "K");
    model.component("comp1").material("mat2").propertyGroup("def").func("Cp").set("fununit", "J/(kg*K)");
    model.component("comp1").material("mat2").propertyGroup("def").func("rho").set("arg", "T");
    model.component("comp1").material("mat2").propertyGroup("def").func("rho")
         .set("pieces", new String[][]{{"273.0", "433.0", "1068.70404-0.6393421*T^1+7.34307359E-5*T^2"}});
    model.component("comp1").material("mat2").propertyGroup("def").func("rho").set("argunit", "K");
    model.component("comp1").material("mat2").propertyGroup("def").func("rho").set("fununit", "kg/m^3");
    model.component("comp1").material("mat2").propertyGroup("def").func("k").set("arg", "T");
    model.component("comp1").material("mat2").propertyGroup("def").func("k")
         .set("pieces", new String[][]{{"273.0", "433.0", "0.192223542-2.0637987E-4*T^1+1.54220779E-7*T^2"}});
    model.component("comp1").material("mat2").propertyGroup("def").func("k").set("argunit", "K");
    model.component("comp1").material("mat2").propertyGroup("def").func("k").set("fununit", "W/(m*K)");
    model.component("comp1").material("mat2").propertyGroup("def").set("dynamicviscosity", "eta(T)");
    model.component("comp1").material("mat2").propertyGroup("def").set("heatcapacity", "Cp(T)");
    model.component("comp1").material("mat2").propertyGroup("def").set("density", "rho(T)");
    model.component("comp1").material("mat2").propertyGroup("def")
         .set("thermalconductivity", new String[]{"k(T)", "0", "0", "0", "k(T)", "0", "0", "0", "k(T)"});
    model.component("comp1").material("mat2").propertyGroup("def").addInput("temperature");
    model.component("comp1").material("mat2").materialType("nonSolid");
    model.component("comp1").material("mat2").set("family", "custom");
    model.component("comp1").material("mat2")
         .set("customspecular", new double[]{0.9921568632125854, 0.7254902124404907, 0.07450980693101883});
    model.component("comp1").material("mat2")
         .set("customdiffuse", new double[]{0.9490196108818054, 0.3960784375667572, 0.13333334028720856});
    model.component("comp1").material("mat2")
         .set("customambient", new double[]{0.9921568632125854, 0.7254902124404907, 0.07450980693101883});
    model.component("comp1").material().create("mat3", "Common");
    model.component("comp1").material("mat3").label("Aluminum, Boundary Material");
    model.component("comp1").material("mat3").selection().named("sel11");
    model.component("comp1").material("mat3").set("family", "aluminum");
    model.component("comp1").material("mat3").propertyGroup().create("Enu", "Young's modulus and Poisson's ratio");
    model.component("comp1").material("mat3").propertyGroup().create("Murnaghan", "Murnaghan");
    model.component("comp1").material("mat3").propertyGroup().create("Lame", "Lam\u00e9 parameters");
    model.component("comp1").material("mat3").propertyGroup().create("shell", "Shell");
    model.component("comp1").material("mat3").propertyGroup("def")
         .set("relpermeability", new String[]{"1", "0", "0", "0", "1", "0", "0", "0", "1"});
    model.component("comp1").material("mat3").propertyGroup("def").set("heatcapacity", "900[J/(kg*K)]");
    model.component("comp1").material("mat3").propertyGroup("def")
         .set("thermalconductivity", new String[]{"238[W/(m*K)]", "0", "0", "0", "238[W/(m*K)]", "0", "0", "0", "238[W/(m*K)]"});
    model.component("comp1").material("mat3").propertyGroup("def")
         .set("electricconductivity", new String[]{"3.774e7[S/m]", "0", "0", "0", "3.774e7[S/m]", "0", "0", "0", "3.774e7[S/m]"});
    model.component("comp1").material("mat3").propertyGroup("def")
         .set("relpermittivity", new String[]{"1", "0", "0", "0", "1", "0", "0", "0", "1"});
    model.component("comp1").material("mat3").propertyGroup("def")
         .set("thermalexpansioncoefficient", new String[]{"23e-6[1/K]", "0", "0", "0", "23e-6[1/K]", "0", "0", "0", "23e-6[1/K]"});
    model.component("comp1").material("mat3").propertyGroup("def").set("density", "2700[kg/m^3]");
    model.component("comp1").material("mat3").propertyGroup("Enu").set("E", "70e9[Pa]");
    model.component("comp1").material("mat3").propertyGroup("Enu").set("nu", "0.33");
    model.component("comp1").material("mat3").propertyGroup("Murnaghan").set("l", "-2.5e11[Pa]");
    model.component("comp1").material("mat3").propertyGroup("Murnaghan").set("m", "-3.3e11[Pa]");
    model.component("comp1").material("mat3").propertyGroup("Murnaghan").set("n", "-3.5e11[Pa]");
    model.component("comp1").material("mat3").propertyGroup("Lame").set("lambLame", "5.1e10[Pa]");
    model.component("comp1").material("mat3").propertyGroup("Lame").set("muLame", "2.6e10[Pa]");
    model.component("comp1").material("mat3").propertyGroup("shell").set("lth", "fin_th");
    model.material().create("mat4", "Common", "");
    model.material("mat4").label("Aluminum, Domain Material");
    model.material("mat4").set("family", "aluminum");
    model.material("mat4").propertyGroup().create("Enu", "Young's modulus and Poisson's ratio");
    model.material("mat4").propertyGroup().create("Murnaghan", "Murnaghan");
    model.material("mat4").propertyGroup().create("Lame", "Lam\u00e9 parameters");
    model.material("mat4").propertyGroup("def")
         .set("relpermeability", new String[]{"1", "0", "0", "0", "1", "0", "0", "0", "1"});
    model.material("mat4").propertyGroup("def").set("heatcapacity", "900[J/(kg*K)]");
    model.material("mat4").propertyGroup("def")
         .set("thermalconductivity", new String[]{"238[W/(m*K)]", "0", "0", "0", "238[W/(m*K)]", "0", "0", "0", "238[W/(m*K)]"});
    model.material("mat4").propertyGroup("def")
         .set("electricconductivity", new String[]{"3.774e7[S/m]", "0", "0", "0", "3.774e7[S/m]", "0", "0", "0", "3.774e7[S/m]"});
    model.material("mat4").propertyGroup("def")
         .set("relpermittivity", new String[]{"1", "0", "0", "0", "1", "0", "0", "0", "1"});
    model.material("mat4").propertyGroup("def")
         .set("thermalexpansioncoefficient", new String[]{"23e-6[1/K]", "0", "0", "0", "23e-6[1/K]", "0", "0", "0", "23e-6[1/K]"});
    model.material("mat4").propertyGroup("def").set("density", "2700[kg/m^3]");
    model.material("mat4").propertyGroup("Enu").set("E", "70e9[Pa]");
    model.material("mat4").propertyGroup("Enu").set("nu", "0.33");
    model.material("mat4").propertyGroup("Murnaghan").set("l", "-2.5e11[Pa]");
    model.material("mat4").propertyGroup("Murnaghan").set("m", "-3.3e11[Pa]");
    model.material("mat4").propertyGroup("Murnaghan").set("n", "-3.5e11[Pa]");
    model.material("mat4").propertyGroup("Lame").set("lambLame", "5.1e10[Pa]");
    model.material("mat4").propertyGroup("Lame").set("muLame", "2.6e10[Pa]");
    model.component("comp1").material().create("pmat1", "PorousMedia");
    model.component("comp1").material("pmat1").selection().named("dif1");
    model.component("comp1").material("pmat1").set("porosity", "0.8");
    model.component("comp1").material("pmat1").propertyGroup("def")
         .set("hydraulicpermeability", new String[]{"1e-8", "0", "0", "0", "1e-8", "0", "0", "0", "1e-8"});
    model.component("comp1").material("pmat1").feature().create("fluid1", "Fluid", "comp1");
    model.component("comp1").material("pmat1").feature().create("solid1", "Solid", "comp1");
    model.component("comp1").material("pmat1").feature("fluid1").set("link", "mat2");
    model.component("comp1").material("pmat1").feature("solid1").set("link", "mat4");
    model.component("comp1").material("pmat1").feature("solid1").set("vfrac", "0.2");
    model.component("comp1").material("pmat1").set("family", "custom");
    model.component("comp1").material("pmat1")
         .set("customspecular", new double[]{0.9921568632125854, 0.7254902124404907, 0.07450980693101883});
    model.component("comp1").material("pmat1")
         .set("customdiffuse", new double[]{0.9490196108818054, 0.3960784375667572, 0.13333334028720856});
    model.component("comp1").material("pmat1")
         .set("customambient", new double[]{0.9921568632125854, 0.7254902124404907, 0.07450980693101883});
    model.component("comp1").material().create("mat5", "Common");
    model.component("comp1").material("mat5").label("Casing");
    model.component("comp1").material("mat5").selection().named("sel12");
    model.component("comp1").material("mat5").set("family", "custom");
    model.component("comp1").material("mat5").set("alpha", 0.5);

    model.component("comp1").mesh().create("mesh1");
    model.component("comp1").mesh("mesh1").label("Computational Domain Mesh");
    model.component("comp1").mesh("mesh1").autoMeshSize(7);
    model.component("comp1").mesh("mesh1").automatic(false);
    model.component("comp1").mesh("mesh1").feature("size1").set("custom", true);
    model.component("comp1").mesh("mesh1").feature("size1").set("hminactive", true);
    model.component("comp1").mesh("mesh1").feature("size1").set("hmin", 0.22);
    model.component("comp1").mesh("mesh1").feature("size1").set("hnarrowactive", true);
    model.component("comp1").mesh("mesh1").feature("bl1").selection().named("geom1_csel2_dom");
    model.component("comp1").mesh("mesh1").feature("bl1").feature("blp1").selection().named("uni4");
    model.component("comp1").mesh("mesh1").feature("bl1").feature("blp1").set("blnlayers", 5);
    model.component("comp1").mesh("mesh1").feature("bl1").feature("blp1").set("blhminfact", 2.5);
    model.component("comp1").mesh("mesh1").feature("bl1").feature().remove("blp2");
    model.component("comp1").mesh("mesh1").create("bl2", "BndLayer");
    model.component("comp1").mesh("mesh1").feature("bl2").create("blp", "BndLayerProp");
    model.component("comp1").mesh("mesh1").feature("bl2").selection().geom("geom1", 3);
    model.component("comp1").mesh("mesh1").feature("bl2").selection().named("sel4");
    model.component("comp1").mesh("mesh1").feature("bl2").feature("blp").selection().named("uni3");
    model.component("comp1").mesh("mesh1").feature("bl2").feature("blp").set("blnlayers", 3);
    model.component("comp1").mesh("mesh1").feature("bl2").feature("blp").set("blhminfact", 4);
    model.component("comp1").mesh("mesh1").run();
    model.component("comp1").mesh().create("mesh2");
    model.component("comp1").mesh("mesh2").label("Casing Mesh");
    model.component("comp1").mesh("mesh2").create("ftet1", "FreeTet");
    model.component("comp1").mesh("mesh2").feature("ftet1").selection().named("sel12");
    model.component("comp1").mesh("mesh2").run();

    model.study().create("std1");
    model.study("std1").create("wdi", "WallDistanceInitialization");
    model.study("std1").feature("wdi").setEntry("mesh", "geom1", "mesh1");
    model.study("std1").create("stat", "Stationary");
    model.study("std1").feature("stat").setEntry("mesh", "geom1", "mesh1");

    model.sol().create("sol1");
    model.sol("sol1").study("std1");
    model.sol("sol1").createAutoSequence("std1");
    model.sol("sol1").feature("s2").set("stol", "1e-4");
    model.sol("sol1").feature("s2").feature("se1").set("segstabacc", "none");
    model.sol("sol1").runAll();

    model.result().configuration().create("prfu1", "PreferredUnits");
    model.result().configuration("prfu1")
         .setIndex("quantityunits", new String[]{"temperature", "Temperature", "K", "K"}, 0);
    model.result().configuration("prfu1").setIndex("quantityunits", "\u00b0C", 0, 3);
    model.result().configuration("prfu1").apply();

    model.component("comp1").view().create("view7", "geom1");
    model.view().create("view8", 3);
    model.view().create("view9", 3);
    model.view().create("view10", 3);

    model.result().dataset().create("lshl1", "LayeredMaterial");
    model.result().dataset().create("surf1", "Surface");
    model.result().dataset("surf1").label("Exterior Walls (spf)");

    return model;
  }

  public static Model run3(Model model) {
    model.result().dataset("surf1").selection()
         .set(67, 69, 70, 71, 72, 73, 74, 76, 78, 79, 80, 82, 83, 87, 88, 89, 91, 92, 96, 97, 98, 100, 101, 105, 106, 107, 109, 110, 114, 115, 116, 118, 119, 123, 124, 125, 127, 128, 132, 133, 134, 136, 137, 141, 142, 143, 145, 146, 147, 149, 150, 153, 156, 159, 162, 165, 168, 171, 173, 174, 175, 176, 180, 181, 184, 188, 191, 195, 198, 202, 205, 209, 212, 216, 219, 223, 226, 230, 233, 234, 253, 254, 257, 261, 264, 268, 271, 275, 278, 282, 285, 289, 292, 296, 299, 303, 306, 307, 326, 327, 330, 334, 337, 341, 344, 348, 351, 355, 358, 362, 365, 369, 372, 376, 379, 380, 399, 400, 403, 407, 410, 414, 417, 421, 424, 428, 431, 435, 438, 442, 445, 449, 452, 453, 472, 473, 476, 480, 483, 487, 490, 494, 497, 501, 504, 508, 511, 515, 518, 522, 525, 526, 545, 546, 549, 553, 556, 560, 563, 567, 570, 574, 577, 581, 584, 588, 591, 595, 598, 599, 618, 619, 622, 626, 629, 633, 636, 640, 643, 647, 650, 654, 657, 661, 664, 668, 671, 672, 691, 692, 695, 699, 702, 706, 709, 713, 716, 720, 723, 727, 730, 734, 737, 741, 744, 745, 764, 765, 768, 772, 775, 779, 782, 786, 789, 793, 796, 800, 803, 807, 810, 814, 817, 818, 837, 838, 841, 845, 848, 852, 855, 859, 862, 866, 869, 873, 876, 880, 883, 887, 890, 891, 910, 911, 914, 918, 921, 925, 928, 932, 935, 939, 942, 946, 949, 953, 956, 960, 963, 964, 983, 984, 987, 991, 994, 998, 1001, 1005, 1008, 1012, 1015, 1019, 1022, 1026, 1029, 1033, 1036, 1037, 1056, 1057, 1060, 1064, 1067, 1071, 1074, 1078, 1081, 1085, 1088, 1092, 1095, 1099, 1102, 1106, 1109, 1110, 1129, 1130, 1133, 1137, 1140, 1144, 1147, 1151, 1154, 1158, 1161, 1165, 1168, 1172, 1175, 1179, 1182, 1183, 1202, 1203, 1206, 1210, 1213, 1217, 1220, 1224, 1227, 1231, 1234, 1238, 1241, 1245, 1248, 1252, 1255, 1256, 1275, 1276, 1279, 1283, 1286, 1290, 1293, 1297, 1300, 1304, 1307, 1311, 1314, 1318, 1321, 1325, 1328, 1329, 1348, 1349, 1352, 1356, 1359, 1363, 1366, 1370, 1373, 1377, 1380, 1384, 1387, 1391, 1394, 1398, 1401, 1402, 1421, 1422, 1425, 1429, 1432, 1436, 1439, 1443, 1446, 1450, 1453, 1457, 1460, 1464, 1467, 1471, 1474, 1475, 1494, 1495, 1498, 1502, 1505, 1509, 1512, 1516, 1519, 1523, 1526, 1530, 1533, 1537, 1540, 1544, 1547, 1548, 1567, 1568, 1571, 1575, 1578, 1582, 1585, 1589, 1592, 1596, 1599, 1603, 1606, 1610, 1613, 1617, 1620, 1621, 1640, 1641, 1644, 1648, 1651, 1655, 1658, 1662, 1665, 1669, 1672, 1676, 1679, 1683, 1686, 1690, 1693, 1694, 1713, 1714, 1717, 1721, 1724, 1728, 1731, 1735, 1738, 1742, 1745, 1749, 1752, 1756, 1759, 1763, 1766, 1767, 1786, 1787, 1790, 1794, 1797, 1801, 1804, 1808, 1811, 1815, 1818, 1822, 1825, 1829, 1832, 1836, 1839, 1840, 1859, 1860, 1863, 1867, 1870, 1874, 1877, 1881, 1884, 1888, 1891, 1895, 1898, 1902, 1905, 1909, 1912, 1913, 1932, 1933, 1936, 1940, 1943, 1947, 1950, 1954, 1957, 1961, 1964, 1968, 1971, 1975, 1978, 1982, 1985, 1986, 2005, 2006, 2009, 2013, 2016, 2020, 2023, 2027, 2030, 2034, 2037, 2041, 2044, 2048, 2051, 2055, 2058, 2059, 2078, 2079, 2082, 2086, 2089, 2093, 2096, 2100, 2103, 2107, 2110, 2114, 2117, 2121, 2124, 2128, 2131, 2132, 2151, 2152, 2155, 2159, 2162, 2166, 2169, 2173, 2176, 2180, 2183, 2187, 2190, 2194, 2197, 2201, 2204, 2205, 2224, 2225, 2228, 2232, 2235, 2239, 2242, 2246, 2249, 2253, 2256, 2260, 2263, 2267, 2270, 2274, 2277, 2278, 2297, 2298, 2301, 2305, 2308, 2312, 2315, 2319, 2322, 2326, 2329, 2333, 2336, 2340, 2343, 2347, 2350, 2351, 2370, 2371, 2374, 2378, 2381, 2385, 2388, 2392, 2395, 2399, 2402, 2406, 2409, 2413, 2416, 2420, 2423, 2424, 2443, 2444, 2447, 2451, 2454, 2458, 2461, 2465, 2468, 2472, 2475, 2479, 2482, 2486, 2489, 2493, 2496, 2497, 2516, 2517, 2520, 2524, 2527, 2531, 2534, 2538, 2541, 2545, 2548, 2552, 2555, 2559, 2562, 2566, 2569, 2570, 2589, 2590, 2593, 2597, 2600, 2604, 2607, 2611, 2614, 2618, 2621, 2625, 2628, 2632, 2635, 2639, 2642, 2643, 2662, 2663, 2666, 2670, 2673, 2677, 2680, 2684, 2687, 2691, 2694, 2698, 2701, 2705, 2708, 2712, 2715, 2716, 2735, 2736, 2739, 2743, 2746, 2750, 2753, 2757, 2760, 2764, 2767, 2771, 2774, 2778, 2781, 2785, 2788, 2789, 2808, 2809, 2812, 2816, 2819, 2823, 2826, 2830, 2833, 2837, 2840, 2844, 2847, 2851, 2854, 2858, 2861, 2862, 2881, 2882, 2885, 2889, 2892, 2896, 2899, 2903, 2906, 2910, 2913, 2917, 2920, 2924, 2927, 2931, 2934, 2935, 2954, 2955, 2958, 2962, 2965, 2969, 2972, 2976, 2979, 2983, 2986, 2990, 2993, 2997, 3000, 3004, 3007, 3008, 3027, 3028, 3031, 3035, 3038, 3042, 3045, 3049, 3052, 3056, 3059, 3063, 3066, 3070, 3073, 3077, 3080, 3081, 3100, 3101, 3104, 3108, 3111, 3115, 3118, 3122, 3125, 3129, 3132, 3136, 3139, 3143, 3146, 3150, 3153, 3154, 3173, 3174, 3177, 3181, 3184, 3188, 3191, 3195, 3198, 3202, 3205, 3209, 3212, 3216, 3219, 3223, 3226, 3227, 3246, 3247, 3250, 3254, 3257, 3261, 3264, 3268, 3271, 3275, 3278, 3282, 3285, 3289, 3292, 3296, 3299, 3300, 3319, 3320, 3323, 3327, 3330, 3334, 3337, 3341, 3344, 3348, 3351, 3355, 3358, 3362, 3365, 3369, 3372, 3373, 3390, 3391, 3395, 3399, 3400, 3402, 3403, 3405, 3406, 3408, 3409, 3413, 3414, 3416, 3417, 3419, 3420, 3422, 3424, 3429);
    model.result().dataset().create("surf2", "Surface");
    model.result().dataset("surf2").label("Interior Walls (spf)");
    model.result().dataset("surf2").selection()
         .set(85, 94, 103, 112, 121, 130, 139, 178, 182, 185, 187, 189, 192, 194, 196, 199, 201, 203, 206, 208, 210, 213, 215, 217, 220, 222, 224, 227, 229, 231, 251, 255, 258, 260, 262, 265, 267, 269, 272, 274, 276, 279, 281, 283, 286, 288, 290, 293, 295, 297, 300, 302, 304, 324, 328, 331, 333, 335, 338, 340, 342, 345, 347, 349, 352, 354, 356, 359, 361, 363, 366, 368, 370, 373, 375, 377, 397, 401, 404, 406, 408, 411, 413, 415, 418, 420, 422, 425, 427, 429, 432, 434, 436, 439, 441, 443, 446, 448, 450, 470, 474, 477, 479, 481, 484, 486, 488, 491, 493, 495, 498, 500, 502, 505, 507, 509, 512, 514, 516, 519, 521, 523, 543, 547, 550, 552, 554, 557, 559, 561, 564, 566, 568, 571, 573, 575, 578, 580, 582, 585, 587, 589, 592, 594, 596, 616, 620, 623, 625, 627, 630, 632, 634, 637, 639, 641, 644, 646, 648, 651, 653, 655, 658, 660, 662, 665, 667, 669, 689, 693, 696, 698, 700, 703, 705, 707, 710, 712, 714, 717, 719, 721, 724, 726, 728, 731, 733, 735, 738, 740, 742, 762, 766, 769, 771, 773, 776, 778, 780, 783, 785, 787, 790, 792, 794, 797, 799, 801, 804, 806, 808, 811, 813, 815, 835, 839, 842, 844, 846, 849, 851, 853, 856, 858, 860, 863, 865, 867, 870, 872, 874, 877, 879, 881, 884, 886, 888, 908, 912, 915, 917, 919, 922, 924, 926, 929, 931, 933, 936, 938, 940, 943, 945, 947, 950, 952, 954, 957, 959, 961, 981, 985, 988, 990, 992, 995, 997, 999, 1002, 1004, 1006, 1009, 1011, 1013, 1016, 1018, 1020, 1023, 1025, 1027, 1030, 1032, 1034, 1054, 1058, 1061, 1063, 1065, 1068, 1070, 1072, 1075, 1077, 1079, 1082, 1084, 1086, 1089, 1091, 1093, 1096, 1098, 1100, 1103, 1105, 1107, 1127, 1131, 1134, 1136, 1138, 1141, 1143, 1145, 1148, 1150, 1152, 1155, 1157, 1159, 1162, 1164, 1166, 1169, 1171, 1173, 1176, 1178, 1180, 1200, 1204, 1207, 1209, 1211, 1214, 1216, 1218, 1221, 1223, 1225, 1228, 1230, 1232, 1235, 1237, 1239, 1242, 1244, 1246, 1249, 1251, 1253, 1273, 1277, 1280, 1282, 1284, 1287, 1289, 1291, 1294, 1296, 1298, 1301, 1303, 1305, 1308, 1310, 1312, 1315, 1317, 1319, 1322, 1324, 1326, 1346, 1350, 1353, 1355, 1357, 1360, 1362, 1364, 1367, 1369, 1371, 1374, 1376, 1378, 1381, 1383, 1385, 1388, 1390, 1392, 1395, 1397, 1399, 1419, 1423, 1426, 1428, 1430, 1433, 1435, 1437, 1440, 1442, 1444, 1447, 1449, 1451, 1454, 1456, 1458, 1461, 1463, 1465, 1468, 1470, 1472, 1492, 1496, 1499, 1501, 1503, 1506, 1508, 1510, 1513, 1515, 1517, 1520, 1522, 1524, 1527, 1529, 1531, 1534, 1536, 1538, 1541, 1543, 1545, 1565, 1569, 1572, 1574, 1576, 1579, 1581, 1583, 1586, 1588, 1590, 1593, 1595, 1597, 1600, 1602, 1604, 1607, 1609, 1611, 1614, 1616, 1618, 1638, 1642, 1645, 1647, 1649, 1652, 1654, 1656, 1659, 1661, 1663, 1666, 1668, 1670, 1673, 1675, 1677, 1680, 1682, 1684, 1687, 1689, 1691, 1711, 1715, 1718, 1720, 1722, 1725, 1727, 1729, 1732, 1734, 1736, 1739, 1741, 1743, 1746, 1748, 1750, 1753, 1755, 1757, 1760, 1762, 1764, 1784, 1788, 1791, 1793, 1795, 1798, 1800, 1802, 1805, 1807, 1809, 1812, 1814, 1816, 1819, 1821, 1823, 1826, 1828, 1830, 1833, 1835, 1837, 1857, 1861, 1864, 1866, 1868, 1871, 1873, 1875, 1878, 1880, 1882, 1885, 1887, 1889, 1892, 1894, 1896, 1899, 1901, 1903, 1906, 1908, 1910, 1930, 1934, 1937, 1939, 1941, 1944, 1946, 1948, 1951, 1953, 1955, 1958, 1960, 1962, 1965, 1967, 1969, 1972, 1974, 1976, 1979, 1981, 1983, 2003, 2007, 2010, 2012, 2014, 2017, 2019, 2021, 2024, 2026, 2028, 2031, 2033, 2035, 2038, 2040, 2042, 2045, 2047, 2049, 2052, 2054, 2056, 2076, 2080, 2083, 2085, 2087, 2090, 2092, 2094, 2097, 2099, 2101, 2104, 2106, 2108, 2111, 2113, 2115, 2118, 2120, 2122, 2125, 2127, 2129, 2149, 2153, 2156, 2158, 2160, 2163, 2165, 2167, 2170, 2172, 2174, 2177, 2179, 2181, 2184, 2186, 2188, 2191, 2193, 2195, 2198, 2200, 2202, 2222, 2226, 2229, 2231, 2233, 2236, 2238, 2240, 2243, 2245, 2247, 2250, 2252, 2254, 2257, 2259, 2261, 2264, 2266, 2268, 2271, 2273, 2275, 2295, 2299, 2302, 2304, 2306, 2309, 2311, 2313, 2316, 2318, 2320, 2323, 2325, 2327, 2330, 2332, 2334, 2337, 2339, 2341, 2344, 2346, 2348, 2368, 2372, 2375, 2377, 2379, 2382, 2384, 2386, 2389, 2391, 2393, 2396, 2398, 2400, 2403, 2405, 2407, 2410, 2412, 2414, 2417, 2419, 2421, 2441, 2445, 2448, 2450, 2452, 2455, 2457, 2459, 2462, 2464, 2466, 2469, 2471, 2473, 2476, 2478, 2480, 2483, 2485, 2487, 2490, 2492, 2494, 2514, 2518, 2521, 2523, 2525, 2528, 2530, 2532, 2535, 2537, 2539, 2542, 2544, 2546, 2549, 2551, 2553, 2556, 2558, 2560, 2563, 2565, 2567, 2587, 2591, 2594, 2596, 2598, 2601, 2603, 2605, 2608, 2610, 2612, 2615, 2617, 2619, 2622, 2624, 2626, 2629, 2631, 2633, 2636, 2638, 2640, 2660, 2664, 2667, 2669, 2671, 2674, 2676, 2678, 2681, 2683, 2685, 2688, 2690, 2692, 2695, 2697, 2699, 2702, 2704, 2706, 2709, 2711, 2713, 2733, 2737, 2740, 2742, 2744, 2747, 2749, 2751, 2754, 2756, 2758, 2761, 2763, 2765, 2768, 2770, 2772, 2775, 2777, 2779, 2782, 2784, 2786, 2806, 2810, 2813, 2815, 2817, 2820, 2822, 2824, 2827, 2829, 2831, 2834, 2836, 2838, 2841, 2843, 2845, 2848, 2850, 2852, 2855, 2857, 2859, 2879, 2883, 2886, 2888, 2890, 2893, 2895, 2897, 2900, 2902, 2904, 2907, 2909, 2911, 2914, 2916, 2918, 2921, 2923, 2925, 2928, 2930, 2932, 2952, 2956, 2959, 2961, 2963, 2966, 2968, 2970, 2973, 2975, 2977, 2980, 2982, 2984, 2987, 2989, 2991, 2994, 2996, 2998, 3001, 3003, 3005, 3025, 3029, 3032, 3034, 3036, 3039, 3041, 3043, 3046, 3048, 3050, 3053, 3055, 3057, 3060, 3062, 3064, 3067, 3069, 3071, 3074, 3076, 3078, 3098, 3102, 3105, 3107, 3109, 3112, 3114, 3116, 3119, 3121, 3123, 3126, 3128, 3130, 3133, 3135, 3137, 3140, 3142, 3144, 3147, 3149, 3151, 3171, 3175, 3178, 3180, 3182, 3185, 3187, 3189, 3192, 3194, 3196, 3199, 3201, 3203, 3206, 3208, 3210, 3213, 3215, 3217, 3220, 3222, 3224, 3244, 3248, 3251, 3253, 3255, 3258, 3260, 3262, 3265, 3267, 3269, 3272, 3274, 3276, 3279, 3281, 3283, 3286, 3288, 3290, 3293, 3295, 3297, 3317, 3321, 3324, 3326, 3328, 3331, 3333, 3335, 3338, 3340, 3342, 3345, 3347, 3349, 3352, 3354, 3356, 3359, 3361, 3363, 3366, 3368, 3370);
    model.result().dataset().create("surf3", "Surface");
    model.result().dataset("surf3").label("All Walls (fp)");
    model.result().dataset("surf3").selection()
         .set(47, 48, 49, 52, 58, 74, 78, 79, 80, 82, 83, 87, 88, 89, 91, 92, 96, 97, 98, 100, 101, 105, 106, 107, 109, 110, 114, 115, 116, 118, 119, 123, 124, 125, 127, 128, 132, 133, 134, 136, 137, 141, 142, 143, 145, 150, 153, 156, 159, 162, 165, 168, 171, 181, 184, 188, 191, 195, 198, 202, 205, 209, 212, 216, 219, 223, 226, 230, 233, 254, 257, 261, 264, 268, 271, 275, 278, 282, 285, 289, 292, 296, 299, 303, 306, 327, 330, 334, 337, 341, 344, 348, 351, 355, 358, 362, 365, 369, 372, 376, 379, 400, 403, 407, 410, 414, 417, 421, 424, 428, 431, 435, 438, 442, 445, 449, 452, 473, 476, 480, 483, 487, 490, 494, 497, 501, 504, 508, 511, 515, 518, 522, 525, 546, 549, 553, 556, 560, 563, 567, 570, 574, 577, 581, 584, 588, 591, 595, 598, 619, 622, 626, 629, 633, 636, 640, 643, 647, 650, 654, 657, 661, 664, 668, 671, 692, 695, 699, 702, 706, 709, 713, 716, 720, 723, 727, 730, 734, 737, 741, 744, 765, 768, 772, 775, 779, 782, 786, 789, 793, 796, 800, 803, 807, 810, 814, 817, 838, 841, 845, 848, 852, 855, 859, 862, 866, 869, 873, 876, 880, 883, 887, 890, 911, 914, 918, 921, 925, 928, 932, 935, 939, 942, 946, 949, 953, 956, 960, 963, 984, 987, 991, 994, 998, 1001, 1005, 1008, 1012, 1015, 1019, 1022, 1026, 1029, 1033, 1036, 1057, 1060, 1064, 1067, 1071, 1074, 1078, 1081, 1085, 1088, 1092, 1095, 1099, 1102, 1106, 1109, 1130, 1133, 1137, 1140, 1144, 1147, 1151, 1154, 1158, 1161, 1165, 1168, 1172, 1175, 1179, 1182, 1203, 1206, 1210, 1213, 1217, 1220, 1224, 1227, 1231, 1234, 1238, 1241, 1245, 1248, 1252, 1255, 1276, 1279, 1283, 1286, 1290, 1293, 1297, 1300, 1304, 1307, 1311, 1314, 1318, 1321, 1325, 1328, 1349, 1352, 1356, 1359, 1363, 1366, 1370, 1373, 1377, 1380, 1384, 1387, 1391, 1394, 1398, 1401, 1422, 1425, 1429, 1432, 1436, 1439, 1443, 1446, 1450, 1453, 1457, 1460, 1464, 1467, 1471, 1474, 1495, 1498, 1502, 1505, 1509, 1512, 1516, 1519, 1523, 1526, 1530, 1533, 1537, 1540, 1544, 1547, 1568, 1571, 1575, 1578, 1582, 1585, 1589, 1592, 1596, 1599, 1603, 1606, 1610, 1613, 1617, 1620, 1641, 1644, 1648, 1651, 1655, 1658, 1662, 1665, 1669, 1672, 1676, 1679, 1683, 1686, 1690, 1693, 1714, 1717, 1721, 1724, 1728, 1731, 1735, 1738, 1742, 1745, 1749, 1752, 1756, 1759, 1763, 1766, 1787, 1790, 1794, 1797, 1801, 1804, 1808, 1811, 1815, 1818, 1822, 1825, 1829, 1832, 1836, 1839, 1860, 1863, 1867, 1870, 1874, 1877, 1881, 1884, 1888, 1891, 1895, 1898, 1902, 1905, 1909, 1912, 1933, 1936, 1940, 1943, 1947, 1950, 1954, 1957, 1961, 1964, 1968, 1971, 1975, 1978, 1982, 1985, 2006, 2009, 2013, 2016, 2020, 2023, 2027, 2030, 2034, 2037, 2041, 2044, 2048, 2051, 2055, 2058, 2079, 2082, 2086, 2089, 2093, 2096, 2100, 2103, 2107, 2110, 2114, 2117, 2121, 2124, 2128, 2131, 2152, 2155, 2159, 2162, 2166, 2169, 2173, 2176, 2180, 2183, 2187, 2190, 2194, 2197, 2201, 2204, 2225, 2228, 2232, 2235, 2239, 2242, 2246, 2249, 2253, 2256, 2260, 2263, 2267, 2270, 2274, 2277, 2298, 2301, 2305, 2308, 2312, 2315, 2319, 2322, 2326, 2329, 2333, 2336, 2340, 2343, 2347, 2350, 2371, 2374, 2378, 2381, 2385, 2388, 2392, 2395, 2399, 2402, 2406, 2409, 2413, 2416, 2420, 2423, 2444, 2447, 2451, 2454, 2458, 2461, 2465, 2468, 2472, 2475, 2479, 2482, 2486, 2489, 2493, 2496, 2517, 2520, 2524, 2527, 2531, 2534, 2538, 2541, 2545, 2548, 2552, 2555, 2559, 2562, 2566, 2569, 2590, 2593, 2597, 2600, 2604, 2607, 2611, 2614, 2618, 2621, 2625, 2628, 2632, 2635, 2639, 2642, 2663, 2666, 2670, 2673, 2677, 2680, 2684, 2687, 2691, 2694, 2698, 2701, 2705, 2708, 2712, 2715, 2736, 2739, 2743, 2746, 2750, 2753, 2757, 2760, 2764, 2767, 2771, 2774, 2778, 2781, 2785, 2788, 2809, 2812, 2816, 2819, 2823, 2826, 2830, 2833, 2837, 2840, 2844, 2847, 2851, 2854, 2858, 2861, 2882, 2885, 2889, 2892, 2896, 2899, 2903, 2906, 2910, 2913, 2917, 2920, 2924, 2927, 2931, 2934, 2955, 2958, 2962, 2965, 2969, 2972, 2976, 2979, 2983, 2986, 2990, 2993, 2997, 3000, 3004, 3007, 3028, 3031, 3035, 3038, 3042, 3045, 3049, 3052, 3056, 3059, 3063, 3066, 3070, 3073, 3077, 3080, 3101, 3104, 3108, 3111, 3115, 3118, 3122, 3125, 3129, 3132, 3136, 3139, 3143, 3146, 3150, 3153, 3174, 3177, 3181, 3184, 3188, 3191, 3195, 3198, 3202, 3205, 3209, 3212, 3216, 3219, 3223, 3226, 3247, 3250, 3254, 3257, 3261, 3264, 3268, 3271, 3275, 3278, 3282, 3285, 3289, 3292, 3296, 3299, 3320, 3323, 3327, 3330, 3334, 3337, 3341, 3344, 3348, 3351, 3355, 3358, 3362, 3365, 3369, 3372, 3395, 3396, 3397, 3399, 3400, 3402, 3403, 3405, 3406, 3408, 3409, 3410, 3411, 3413, 3414, 3416, 3417, 3419, 3420, 3422, 3423, 3425, 3427, 3444, 3447, 3452, 3453, 3457, 3458, 3463, 3464, 3466, 3467, 3468, 3471, 3472, 3474, 3476, 3479, 3480, 3482, 3516, 3517, 3519, 3520, 3524, 3527, 3532, 3535);
    model.result().dataset().create("surf4", "Surface");
    model.result().dataset("surf4").label("Exterior Walls (fp)");
    model.result().dataset("surf4").selection()
         .set(47, 48, 49, 52, 58, 74, 78, 79, 80, 82, 83, 87, 88, 89, 91, 92, 96, 97, 98, 100, 101, 105, 106, 107, 109, 110, 114, 115, 116, 118, 119, 123, 124, 125, 127, 128, 132, 133, 134, 136, 137, 141, 142, 143, 145, 150, 153, 156, 159, 162, 165, 168, 171, 181, 184, 188, 191, 195, 198, 202, 205, 209, 212, 216, 219, 223, 226, 230, 233, 254, 257, 261, 264, 268, 271, 275, 278, 282, 285, 289, 292, 296, 299, 303, 306, 327, 330, 334, 337, 341, 344, 348, 351, 355, 358, 362, 365, 369, 372, 376, 379, 400, 403, 407, 410, 414, 417, 421, 424, 428, 431, 435, 438, 442, 445, 449, 452, 473, 476, 480, 483, 487, 490, 494, 497, 501, 504, 508, 511, 515, 518, 522, 525, 546, 549, 553, 556, 560, 563, 567, 570, 574, 577, 581, 584, 588, 591, 595, 598, 619, 622, 626, 629, 633, 636, 640, 643, 647, 650, 654, 657, 661, 664, 668, 671, 692, 695, 699, 702, 706, 709, 713, 716, 720, 723, 727, 730, 734, 737, 741, 744, 765, 768, 772, 775, 779, 782, 786, 789, 793, 796, 800, 803, 807, 810, 814, 817, 838, 841, 845, 848, 852, 855, 859, 862, 866, 869, 873, 876, 880, 883, 887, 890, 911, 914, 918, 921, 925, 928, 932, 935, 939, 942, 946, 949, 953, 956, 960, 963, 984, 987, 991, 994, 998, 1001, 1005, 1008, 1012, 1015, 1019, 1022, 1026, 1029, 1033, 1036, 1057, 1060, 1064, 1067, 1071, 1074, 1078, 1081, 1085, 1088, 1092, 1095, 1099, 1102, 1106, 1109, 1130, 1133, 1137, 1140, 1144, 1147, 1151, 1154, 1158, 1161, 1165, 1168, 1172, 1175, 1179, 1182, 1203, 1206, 1210, 1213, 1217, 1220, 1224, 1227, 1231, 1234, 1238, 1241, 1245, 1248, 1252, 1255, 1276, 1279, 1283, 1286, 1290, 1293, 1297, 1300, 1304, 1307, 1311, 1314, 1318, 1321, 1325, 1328, 1349, 1352, 1356, 1359, 1363, 1366, 1370, 1373, 1377, 1380, 1384, 1387, 1391, 1394, 1398, 1401, 1422, 1425, 1429, 1432, 1436, 1439, 1443, 1446, 1450, 1453, 1457, 1460, 1464, 1467, 1471, 1474, 1495, 1498, 1502, 1505, 1509, 1512, 1516, 1519, 1523, 1526, 1530, 1533, 1537, 1540, 1544, 1547, 1568, 1571, 1575, 1578, 1582, 1585, 1589, 1592, 1596, 1599, 1603, 1606, 1610, 1613, 1617, 1620, 1641, 1644, 1648, 1651, 1655, 1658, 1662, 1665, 1669, 1672, 1676, 1679, 1683, 1686, 1690, 1693, 1714, 1717, 1721, 1724, 1728, 1731, 1735, 1738, 1742, 1745, 1749, 1752, 1756, 1759, 1763, 1766, 1787, 1790, 1794, 1797, 1801, 1804, 1808, 1811, 1815, 1818, 1822, 1825, 1829, 1832, 1836, 1839, 1860, 1863, 1867, 1870, 1874, 1877, 1881, 1884, 1888, 1891, 1895, 1898, 1902, 1905, 1909, 1912, 1933, 1936, 1940, 1943, 1947, 1950, 1954, 1957, 1961, 1964, 1968, 1971, 1975, 1978, 1982, 1985, 2006, 2009, 2013, 2016, 2020, 2023, 2027, 2030, 2034, 2037, 2041, 2044, 2048, 2051, 2055, 2058, 2079, 2082, 2086, 2089, 2093, 2096, 2100, 2103, 2107, 2110, 2114, 2117, 2121, 2124, 2128, 2131, 2152, 2155, 2159, 2162, 2166, 2169, 2173, 2176, 2180, 2183, 2187, 2190, 2194, 2197, 2201, 2204, 2225, 2228, 2232, 2235, 2239, 2242, 2246, 2249, 2253, 2256, 2260, 2263, 2267, 2270, 2274, 2277, 2298, 2301, 2305, 2308, 2312, 2315, 2319, 2322, 2326, 2329, 2333, 2336, 2340, 2343, 2347, 2350, 2371, 2374, 2378, 2381, 2385, 2388, 2392, 2395, 2399, 2402, 2406, 2409, 2413, 2416, 2420, 2423, 2444, 2447, 2451, 2454, 2458, 2461, 2465, 2468, 2472, 2475, 2479, 2482, 2486, 2489, 2493, 2496, 2517, 2520, 2524, 2527, 2531, 2534, 2538, 2541, 2545, 2548, 2552, 2555, 2559, 2562, 2566, 2569, 2590, 2593, 2597, 2600, 2604, 2607, 2611, 2614, 2618, 2621, 2625, 2628, 2632, 2635, 2639, 2642, 2663, 2666, 2670, 2673, 2677, 2680, 2684, 2687, 2691, 2694, 2698, 2701, 2705, 2708, 2712, 2715, 2736, 2739, 2743, 2746, 2750, 2753, 2757, 2760, 2764, 2767, 2771, 2774, 2778, 2781, 2785, 2788, 2809, 2812, 2816, 2819, 2823, 2826, 2830, 2833, 2837, 2840, 2844, 2847, 2851, 2854, 2858, 2861, 2882, 2885, 2889, 2892, 2896, 2899, 2903, 2906, 2910, 2913, 2917, 2920, 2924, 2927, 2931, 2934, 2955, 2958, 2962, 2965, 2969, 2972, 2976, 2979, 2983, 2986, 2990, 2993, 2997, 3000, 3004, 3007, 3028, 3031, 3035, 3038, 3042, 3045, 3049, 3052, 3056, 3059, 3063, 3066, 3070, 3073, 3077, 3080, 3101, 3104, 3108, 3111, 3115, 3118, 3122, 3125, 3129, 3132, 3136, 3139, 3143, 3146, 3150, 3153, 3174, 3177, 3181, 3184, 3188, 3191, 3195, 3198, 3202, 3205, 3209, 3212, 3216, 3219, 3223, 3226, 3247, 3250, 3254, 3257, 3261, 3264, 3268, 3271, 3275, 3278, 3282, 3285, 3289, 3292, 3296, 3299, 3320, 3323, 3327, 3330, 3334, 3337, 3341, 3344, 3348, 3351, 3355, 3358, 3362, 3365, 3369, 3372, 3395, 3396, 3397, 3399, 3400, 3402, 3403, 3405, 3406, 3408, 3409, 3410, 3413, 3414, 3416, 3417, 3419, 3420, 3422, 3423, 3425, 3427, 3444, 3447, 3452, 3453, 3457, 3458, 3463, 3464, 3466, 3467, 3468, 3471, 3472, 3474, 3476, 3479, 3480, 3482, 3516, 3517, 3519, 3520, 3524, 3527, 3532, 3535);
    model.result().dataset().create("surf5", "Surface");
    model.result().dataset("surf5").label("Interior Walls (fp)");
    model.result().dataset("surf5").selection().set(3411);
    model.result().dataset().create("mesh1", "Mesh");
    model.result().dataset("mesh1").set("mesh", "mesh1");
    model.result().dataset().create("mesh2", "Mesh");
    model.result().dataset("mesh2").set("mesh", "mesh2");
    model.result().dataset("mesh2").set("sorder", "quadratic");
    model.result().dataset().create("filt1", "Filter");
    model.result().dataset("filt1").set("data", "lshl1");
    model.result().dataset("filt1").set("expr", "y");
    model.result().dataset("filt1").set("unit", "cm");
    model.result().dataset("filt1").set("bounds", "upper");
    model.result().dataset("filt1").set("upperexpr", "4");
    model.result().dataset().create("filt2", "Filter");
    model.result().dataset("filt2").set("data", "lshl1");
    model.result().dataset("filt2").set("expr", "y");
    model.result().dataset("filt2").set("unit", "cm");
    model.result().dataset("filt2").set("bounds", "lower");
    model.result().dataset("filt2").set("upperexpr", "4");
    model.result().dataset().create("filt3", "Filter");
    model.result().dataset("filt3").set("data", "mesh2");
    model.result().dataset("filt3").set("expr", "y");
    model.result().dataset("filt2").set("unit", "cm");
    model.result().dataset("filt3").set("bounds", "upper");
    model.result().dataset("filt3").set("upperexpr", "4");
    model.result().create("pg1", "PlotGroup3D");
    model.result("pg1").label("Temperature (ht)");
    model.result("pg1").create("surf1", "Surface");
    model.result("pg1").feature("surf1").set("colortable", "HeatCameraLight");
    model.result("pg1").feature("surf1").set("smooth", "internal");
    model.result("pg1").feature("surf1").set("resolution", "normal");
    model.result("pg1").create("surf2", "Surface");
    model.result("pg1").feature("surf2").set("titletype", "none");
    model.result("pg1").feature("surf2").set("data", "lshl1");
    model.result("pg1").feature("surf2").set("smooth", "internal");
    model.result("pg1").feature("surf2").set("inheritplot", "surf1");
    model.result("pg1").feature("surf2").set("resolution", "normal");
    model.result().create("pg2", "PlotGroup3D");
    model.result("pg2").label("Isothermal Contours (ht)");
    model.result("pg2").create("iso1", "Isosurface");
    model.result("pg2").feature("iso1").label("Isosurface");
    model.result("pg2").feature("iso1").set("number", 10);
    model.result("pg2").feature("iso1").set("levelrounding", false);
    model.result("pg2").feature("iso1").set("colortable", "HeatCameraLight");
    model.result("pg2").feature("iso1").set("resolution", "normal");
    model.result().create("pg3", "PlotGroup3D");
    model.result("pg3").label("Velocity (spf)");
    model.result("pg3").set("frametype", "spatial");
    model.result("pg3").create("slc1", "Slice");
    model.result("pg3").feature("slc1").label("Slice");
    model.result("pg3").feature("slc1").set("expr", "spf.U");
    model.result("pg3").feature("slc1").set("smooth", "internal");
    model.result("pg3").feature("slc1").set("resolution", "normal");
    model.result().create("pg4", "PlotGroup3D");
    model.result("pg4").label("Pressure (spf)");
    model.result("pg4").set("frametype", "spatial");
    model.result("pg4").create("surf1", "Surface");
    model.result("pg4").feature("surf1").label("Surface");
    model.result("pg4").feature("surf1").set("expr", "p");
    model.result("pg4").feature("surf1").set("data", "surf1");
    model.result("pg4").feature("surf1").set("colortable", "Dipole");
    model.result("pg4").feature("surf1").set("smooth", "internal");
    model.result("pg4").feature("surf1").set("resolution", "normal");
    model.result("pg4").feature("surf1").create("tran1", "Transparency");
    model.result("pg4").create("slit1", "SurfaceSlit");
    model.result("pg4").feature("slit1").set("data", "surf2");
    model.result("pg4").feature("slit1").set("upexpr", "up(p)");
    model.result("pg4").feature("slit1").set("upunit", "Pa");
    model.result("pg4").feature("slit1").set("updescr", "Evaluate in domain on upside");
    model.result("pg4").feature("slit1").set("downexpr", "down(p)");
    model.result("pg4").feature("slit1").set("downunit", "Pa");
    model.result("pg4").feature("slit1").set("downdescr", "Evaluate in domain on downside");
    model.result("pg4").feature("slit1").set("titletype", "none");
    model.result("pg4").feature("slit1").set("smooth", "internal");
    model.result("pg4").feature("slit1").set("inheritplot", "surf1");
    model.result("pg4").feature("slit1").set("resolution", "normal");
    model.result().create("pg5", "PlotGroup3D");
    model.result("pg5").label("Wall Resolution (spf)");
    model.result("pg5").set("frametype", "spatial");
    model.result("pg5").create("surf1", "Surface");
    model.result("pg5").feature("surf1").label("Wall Resolution");
    model.result("pg5").feature("surf1").set("expr", "spf.Delta_wPlus");
    model.result("pg5").feature("surf1").set("data", "surf1");
    model.result("pg5").feature("surf1").set("smooth", "internal");
    model.result("pg5").feature("surf1").set("resolution", "normal");
    model.result("pg5").feature("surf1").create("filt1", "Filter");
    model.result("pg5").feature("surf1").feature("filt1").set("expr", "y<7[cm]");
    model.result("pg5").create("slit1", "SurfaceSlit");
    model.result("pg5").feature("slit1").label("Wall Resolution, Interior Walls");
    model.result("pg5").feature("slit1").set("titletype", "none");
    model.result("pg5").feature("slit1").set("data", "surf2");
    model.result("pg5").feature("slit1").set("upexpr", "spf.Delta_wPlus_u");
    model.result("pg5").feature("slit1").set("upunit", "1");
    model.result("pg5").feature("slit1").set("updescr", "Wall resolution in viscous units");
    model.result("pg5").feature("slit1").set("downexpr", "spf.Delta_wPlus_d");
    model.result("pg5").feature("slit1").set("downunit", "1");
    model.result("pg5").feature("slit1").set("downdescr", "Wall resolution in viscous units");
    model.result("pg5").feature("slit1").set("smooth", "internal");
    model.result("pg5").feature("slit1").set("inheritplot", "surf1");
    model.result("pg5").feature("slit1").set("resolution", "normal");
    model.result("pg5").feature("slit1").create("filt1", "Filter");
    model.result("pg5").feature("slit1").feature("filt1").set("expr", "y<7[cm]");
    model.result().create("pg6", "PlotGroup3D");
    model.result("pg6").label("Velocity (fp)");
    model.result("pg6").set("frametype", "spatial");
    model.result("pg6").create("slc1", "Slice");
    model.result("pg6").feature("slc1").set("expr", "fp.U");
    model.result("pg6").feature("slc1").label("Slice");
    model.result("pg6").feature("slc1").set("smooth", "internal");
    model.result("pg6").feature("slc1").set("resolution", "normal");
    model.result().create("pg7", "PlotGroup3D");
    model.result("pg7").label("Pressure (fp)");
    model.result("pg7").set("frametype", "spatial");
    model.result("pg7").create("surf1", "Surface");
    model.result("pg7").feature("surf1").label("Surface");
    model.result("pg7").feature("surf1").set("expr", "p2");
    model.result("pg7").feature("surf1").create("tran1", "Transparency");
    model.result("pg7").feature("surf1").set("data", "surf4");
    model.result("pg7").feature("surf1").set("colortable", "Dipole");
    model.result("pg7").feature("surf1").set("smooth", "internal");
    model.result("pg7").feature("surf1").set("resolution", "normal");
    model.result("pg7").create("slit1", "SurfaceSlit");
    model.result("pg7").feature("slit1").set("data", "surf5");
    model.result("pg7").feature("slit1").set("upexpr", "up(p2)");
    model.result("pg7").feature("slit1").set("upunit", "Pa");
    model.result("pg7").feature("slit1").set("updescr", "Evaluate in domain on upside");
    model.result("pg7").feature("slit1").set("downexpr", "down(p2)");
    model.result("pg7").feature("slit1").set("downunit", "Pa");
    model.result("pg7").feature("slit1").set("downdescr", "Evaluate in domain on downside");
    model.result("pg7").feature("slit1").set("titletype", "none");
    model.result("pg7").feature("slit1").set("smooth", "internal");
    model.result("pg7").feature("slit1").set("inheritplot", "surf1");
    model.result("pg7").feature("slit1").set("resolution", "normal");
    model.result().create("pg8", "PlotGroup3D");
    model.result("pg8").label("Air Temperature and Velocity");
    model.result("pg8").set("titletype", "manual");
    model.result("pg8").set("title", "Temperature (\u00b0C) and velocity (m/s) of air in the domain");
    model.result("pg8").set("view", "view8");
    model.result("pg8").set("legendpos", "rightdouble");
    model.result("pg8").set("edges", false);
    model.result("pg8").create("surf1", "Surface");
    model.result("pg8").feature("surf1").set("data", "filt1");
    model.result("pg8").feature("surf1").set("expr", "1");
    model.result("pg8").feature("surf1").create("mtrl1", "MaterialAppearance");
    model.result("pg8").feature("surf1").feature("mtrl1").set("material", "mat3");
    model.result("pg8").feature().duplicate("surf2", "surf1");
    model.result("pg8").feature("surf2").set("data", "filt2");
    model.result("pg8").feature("surf2").create("tran1", "Transparency");
    model.result("pg8").feature("surf2").feature("tran1").set("transparency", 0.7);
    model.result("pg8").feature("surf2").feature("tran1").set("uniformblending", 0.6);
    model.result("pg8").create("slc1", "Slice");
    model.result("pg8").feature("slc1").set("quickplane", "xy");
    model.result("pg8").feature("slc1").set("quickznumber", 1);
    model.result("pg8").feature("slc1").set("interactive", true);
    model.result("pg8").feature("slc1").set("shift", 0.038);
    model.result("pg8").feature("slc1").set("colortable", "HeatCameraLight");
    model.result("pg8").feature("slc1").create("sel1", "Selection");
    model.result("pg8").feature("slc1").feature("sel1").selection().named("geom1_csel2_dom");
    model.result("pg8").create("slc2", "Slice");
    model.result("pg8").feature("slc2").set("expr", "spf.U");
    model.result("pg8").feature("slc2").set("quickplane", "xy");
    model.result("pg8").feature("slc2").set("quickznumber", 1);
    model.result("pg8").feature("slc2").set("interactive", true);
    model.result("pg8").feature("slc2").set("shift", -0.048);
    model.result("pg8").feature("slc2").create("sel1", "Selection");
    model.result("pg8").feature("slc2").feature("sel1").selection().named("geom1_csel2_dom");
    model.result().create("pg9", "PlotGroup3D");
    model.result("pg9").label("Oil Streamlines");
    model.result("pg9").set("view", "view8");
    model.result("pg9").set("edges", false);
    model.result("pg9").create("surf1", "Surface");
    model.result("pg9").feature("surf1").set("data", "filt1");
    model.result("pg9").feature("surf1").set("colortable", "HeatCameraLight");
    model.result("pg9").create("str1", "Streamline");
    model.result("pg9").feature("str1").set("expr", new String[]{"u2", "v2", "w2"});
    model.result("pg9").feature("str1").set("selnumber", 50);
    model.result("pg9").feature("str1").selection().set(3547);

    return model;
  }

  public static Model run4(Model model) {
    model.result("pg9").feature("str1").set("linetype", "tube");
    model.result("pg9").feature("str1").set("radiusexpr", "0.05");
    model.result("pg9").feature("str1").set("tuberadiusscaleactive", true);
    model.result("pg9").feature("str1").set("pointtype", "arrow");
    model.result("pg9").feature("str1").set("arrowscaleactive", true);
    model.result("pg9").feature("str1").set("arrowscale", 7);
    model.result("pg9").feature("str1").set("arrowcountactive", true);
    model.result("pg9").feature("str1").set("arrowcount", 200);
    model.result("pg9").feature("str1").set("inheritplot", "surf1");
    model.result("pg9").feature("str1").create("col1", "Color");
    model.result().duplicate("pg10", "pg9");
    model.result("pg10").label("Oil Streamlines With Casing");
    model.result("pg10").create("surf2", "Surface");
    model.result("pg10").feature("surf2").set("data", "mesh2");
    model.result("pg10").feature("surf2").set("titletype", "none");
    model.result("pg10").feature("surf2").set("expr", "1");
    model.result("pg10").feature("surf2").create("mtrl1", "MaterialAppearance");
    model.result("pg10").feature("surf2").feature("mtrl1").set("appearance", "custom");
    model.result("pg10").feature("surf2").feature("mtrl1").set("family", "steelscratched");
    model.result("pg10").feature("surf2").create("tran1", "Transparency");
    model.result("pg10").feature("surf2").feature("tran1").set("transparency", 0.15);
    model.result("pg10").feature("surf2").feature("tran1").set("uniformblending", 1);
    model.result().create("pg11", "PlotGroup3D");
    model.result("pg11").label("Oil Velocity");
    model.result("pg11").set("view", "view9");
    model.result("pg11").set("edges", false);
    model.result("pg11").create("surf1", "Surface");
    model.result("pg11").feature("surf1").set("titletype", "none");
    model.result("pg11").feature("surf1").set("data", "filt1");
    model.result("pg11").feature("surf1").set("expr", "1");
    model.result("pg11").feature("surf1").create("mtrl1", "MaterialAppearance");
    model.result("pg11").feature("surf1").feature("mtrl1").set("material", "mat3");
    model.result("pg11").create("surf2", "Surface");
    model.result("pg11").feature("surf2").set("titletype", "none");
    model.result("pg11").feature("surf2").set("data", "filt3");
    model.result("pg11").feature("surf2").set("expr", "1");
    model.result("pg11").feature("surf2").create("mtrl1", "MaterialAppearance");
    model.result("pg11").feature("surf2").feature("mtrl1").set("appearance", "custom");
    model.result("pg11").feature("surf2").feature("mtrl1").set("family", "steelscratched");
    model.result("pg11").create("slc1", "Slice");
    model.result("pg11").feature("slc1").set("expr", "fp.U");
    model.result("pg11").feature("slc1").set("quickplane", "zx");
    model.result("pg11").feature("slc1").set("quickynumber", 1);
    model.result().create("pg12", "PlotGroup3D");
    model.result("pg12").label("Mesh Plot");
    model.result("pg12").set("data", "mesh1");
    model.result("pg12").set("view", "view10");
    model.result("pg12").set("legendpos", "left");
    model.result("pg12").set("inherithide", true);
    model.result("pg12").set("showlegendsmaxmin", true);
    model.result("pg12").create("mesh1", "Mesh");
    model.result("pg12").feature("mesh1").set("colortable", "TrafficFlow");
    model.result("pg12").feature("mesh1").set("colortabletrans", "nonlinear");
    model.result("pg12").feature("mesh1").set("nonlinearcolortablerev", true);
    model.result("pg12").feature("mesh1").set("meshdomain", "volume");
    model.result("pg12").feature("mesh1").create("filt1", "Filter");
    model.result("pg12").feature("mesh1").feature("filt1").set("expr", "y<4[cm]");
    model.result().numerical().create("gev1", "EvalGlobal");
    model.result().numerical("gev1").setIndex("expr", "ht.ofl1.ntfluxInt+ht.ifl1.ntfluxInt", 0);
    model.result().numerical("gev1").setIndex("descr", "Oil total net heat rate", 0);
    model.result().numerical("gev1").setIndex("expr", "ht.ofl2.ntfluxInt+ht.ifl2.ntfluxInt", 1);
    model.result().numerical("gev1").setIndex("descr", "Air total net heat rate", 1);
    model.result().numerical().create("av1", "AvSurface");
    model.result().numerical("av1").set("intvolume", true);
    model.result().numerical("av1").selection().set(3546);
    model.result().numerical().create("av2", "AvSurface");
    model.result().numerical("av2").set("intvolume", true);
    model.result().numerical("av2").selection().set(177);

    model.component("comp1").view("view7").set("locked", true);
    model.component("comp1").view("view7").set("showgrid", false);
    model.component("comp1").view("view7").set("showaxisorientation", false);
    model.component("comp1").view("view7").set("ssao", true);
    model.component("comp1").view("view7").set("ssaopreset", "high");
    model.component("comp1").view("view7").set("transparency", true);
    model.component("comp1").view("view7").set("transparencylevel", 0.05);
    model.component("comp1").view("view7").set("showmaterial", true);
    model.component("comp1").view("view7").camera().set("zoomanglefull", 56);
    model.component("comp1").view("view7").camera().set("position", new double[]{48, 28, 20});
    model.component("comp1").view("view7").camera().set("target", new double[]{-122, -85, -32});
    model.component("comp1").view("view7").camera().set("up", new double[]{-0.19, -0.17, 1});
    model.component("comp1").view("view7").camera().set("rotationpoint", new double[]{11.85, 3.85, 8.8});
    model.component("comp1").view("view7").camera().set("viewoffset", new double[]{0.05, 0.07});
    model.view("view8").set("locked", true);
    model.view("view8").set("showgrid", false);
    model.view("view8").set("showaxisorientation", false);
    model.view("view8").set("ssao", true);
    model.view("view8").set("ssaopreset", "high");
    model.view("view8").camera().set("zoomanglefull", 56);
    model.view("view8").camera().set("position", new double[]{48, 28, 20});
    model.view("view8").camera().set("target", new double[]{-122, -85, -32});
    model.view("view8").camera().set("up", new double[]{-0.19, -0.17, 1});
    model.view("view8").camera().set("rotationpoint", new double[]{11.85, 3.85, 8.8});
    model.view("view8").camera().set("viewoffset", new double[]{0.05, 0.07});
    model.view("view9").set("locked", true);
    model.view("view9").set("showgrid", false);
    model.view("view9").set("showaxisorientation", false);
    model.view("view9").camera().set("projection", "orthographic");
    model.view("view9").camera().set("orthoscale", 32);
    model.view("view9").camera().set("position", new double[]{12, 176, 8.8});
    model.view("view9").camera().set("target", new double[]{12, 1.85, 8.8});
    model.view("view9").camera().set("up", new double[]{0, 0, 1});
    model.view("view9").camera().set("rotationpoint", new double[]{12, 1.85, 8.8});
    model.view("view9").camera().set("viewoffset", new double[]{-0.045, -0.024});
    model.view("view10").set("locked", true);
    model.view("view10").set("showgrid", false);
    model.view("view10").set("showaxisorientation", false);
    model.view("view10").camera().set("projection", "orthographic");
    model.view("view10").camera().set("orthoscale", 10.5);
    model.view("view10").camera().set("position", new double[]{12, 212, 8.8});
    model.view("view10").camera().set("target", new double[]{12, 3.85, 8.8});
    model.view("view10").camera().set("up", new double[]{0, 0, 1});
    model.view("view10").camera().set("rotationpoint", new double[]{12, 4, 15});
    model.view("view10").camera().set("viewoffset", new double[]{1, -0.86});

    model.component("comp1").material("mat3").selection().named("sel10");
    model.component("comp1").material("mat3").selection().named("sel11");

    model.result("pg8").run();
    model.result("pg12").run();
    model.result("pg11").run();
    model.result("pg10").run();

    model.title("\u677f\u7fc5\u5f0f\u6362\u70ed\u5668");

    model
         .description("\u672c\u6559\u5b66\u6a21\u578b\u6f14\u793a\u5982\u4f55\u4f7f\u7528\u94dd\u5236\u677f\u7fc5\u5f0f\u6362\u70ed\u5668\u901a\u8fc7\u51b7\u7a7a\u6c14\u5bf9\u70ed\u6cb9\u8fdb\u884c\u51b7\u5374\u7684\u8fc7\u7a0b\u3002\n\n\u4e3a\u4e86\u6700\u5927\u9650\u5ea6\u5730\u63d0\u9ad8\u4f20\u70ed\u6548\u7387\uff0c\u8be5\u6362\u70ed\u5668\u91c7\u7528\u591a\u5b54\u94dd\u57fa\u4f53\u5236\u6210\uff0c\u70ed\u6cb9\u5728\u5176\u4e2d\u6d41\u52a8\u3002\u70ed\u91cf\u901a\u8fc7\u4e0e\u591a\u5b54\u57fa\u4f53\u63a5\u89e6\u7684\u94dd\u7fc5\u7247\u8fdb\u884c\u4f20\u5bfc\u3002\u672c\u4f8b\u5c06\u8fd9\u4e9b\u7fc5\u7247\u4f5c\u4e3a\u8584\u5c42\u8fdb\u884c\u5efa\u6a21\uff0c\u56e0\u6b64\u6ca1\u6709\u7ed8\u5236\u5b83\u4eec\u7684\u539a\u5ea6\uff0c\u4f46\u5728\u4f20\u70ed\u65b9\u7a0b\u4e2d\u4ecd\u5c06\u5176\u8003\u8651\u5728\u5185\u3002");

    model.label("plate_fin_heat_exchanger.mph");

    model.result("pg10").run();
    model.result("pg12").run();
    model.result("pg1").run();
    model.result("pg5").run();

    return model;
  }

  public static void main(String[] args) {
    Model model = run();
    model = run2(model);
    model = run3(model);
    run4(model);
  }

}
