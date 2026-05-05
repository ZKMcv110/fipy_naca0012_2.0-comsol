#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据集自动化生成与调度主控端 - 全特征解耦提取版
【核心功能】：
1. 拉丁超立方采样 (LHS) 均匀生成 500 个样本。
2. 通过 subprocess.run() 多进程调用 comsol_worker.py。
3. 捕获完整的 10 项物理源数据，存入包含 17 列极其详尽指标的 final_results.csv 账本。
"""

import os
import csv
import subprocess
import numpy as np
import pandas as pd
from scipy.stats import qmc

# ==========================================
# 1. 物理参数设计空间
# ==========================================
PARAM_BOUNDS = {
    'Ta':  [0.00, 0.05],
    'Twa': [0.20, 0.60],
    'Tb':  [0.08, 0.15],
    'Ts':  [0.50, 1.50],
    'Tt':  [0.50, 1.20],
    'Tad': [0.00, 1.00]
}

def generate_lhs_samples(num_samples=500):
    print(f"🎲 正在 6 维参数空间内进行拉丁超立方采样 ({num_samples} 个样本)...")
    dim = len(PARAM_BOUNDS)
    sampler = qmc.LatinHypercube(d=dim, seed=42)
    sample_unit = sampler.random(n=num_samples)
    
    lower_bounds = np.array([bounds[0] for bounds in PARAM_BOUNDS.values()])
    upper_bounds = np.array([bounds[1] for bounds in PARAM_BOUNDS.values()])
    
    real_samples = qmc.scale(sample_unit, lower_bounds, upper_bounds)
    return pd.DataFrame(real_samples, columns=PARAM_BOUNDS.keys())

def extract_results_from_stdout(stdout_text):
    """满血升级版：从子进程的输出文本中精准抓取完整的 10 个源头与目标物理量"""
    lines = stdout_text.split('\n')
    for line in lines:
        if "CFD_RESULT_DATA:" in line:
            parts = line.split("CFD_RESULT_DATA:")[1].strip().split(',')
            res_dict = {}
            for part in parts:
                k, v = part.split('=')
                res_dict[k.strip()] = float(v.strip())
            return (
                res_dict.get('Nu'), res_dict.get('f'), 
                res_dict.get('T_in'), res_dict.get('T_out'),
                res_dict.get('v_in'), res_dict.get('v_out'),
                res_dict.get('p_in'), res_dict.get('p_out'),
                res_dict.get('T_wing'), res_dict.get('vol')
            )
    return (None,) * 10

def main():
    print("=====================================================")
    print("🚀 高维拓扑数据集全自动生成流水线启动 (全量特征解耦提取版)")
    print("=====================================================")
    
    num_samples = 500
    results_dir = "consol_cfddata"
    csv_dir = "csv_data"
    csv_file = os.path.join(csv_dir, "final_results.csv")
    
    os.makedirs(results_dir, exist_ok=True)
    os.makedirs(csv_dir, exist_ok=True)
    
    samples_df = generate_lhs_samples(num_samples)
    
    # ⚠️ 初始化扩充后的 CSV 表头：包含 6个几何特征 + 2个目标标签 + 8个源头监控物理量
    if not os.path.exists(csv_file):
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'case_id', 'Ta', 'Twa', 'Tb', 'Ts', 'Tt', 'Tad', 
                'Nu', 'f', 
                'T_in', 'T_out', 'v_in', 'v_out', 'p_in', 'p_out', 'T_wing', 'vol'
            ])
            
    print(f"📁 准备循环调度 COMSOL 进程求解 {num_samples} 个 Cases...")
    
    for idx, row in samples_df.iterrows():
        case_id = idx + 1
        params = row.to_dict()
        outdir = os.path.join(results_dir, f"case_{case_id}_cfd_solution")
        
        print(f"\n▶ 正在派发 Case {case_id}/{num_samples}")
        
        # ⚠️ 注意这里调用的是你的脚本名字 comsol单次执行脚本.py
        cmd = [
            "python", "comsol单次执行脚本.py",
            "--Ta", str(params['Ta']),
            "--Twa", str(params['Twa']),
            "--Tb", str(params['Tb']),
            "--Tt", str(params['Tt']),
            "--Ts", str(params['Ts']),
            "--Tad", str(params['Tad']),
            "--outdir", outdir
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            
            if result.returncode != 0:
                print(f"   ❌ 子进程崩溃或报错 (返回码: {result.returncode})")
                os.makedirs(outdir, exist_ok=True)
                with open(os.path.join(outdir, "error.log"), "w", encoding="utf-8") as log_f:
                    log_f.write(f"--- STDERR (报错信息) ---\n{result.stderr}\n\n--- STDOUT (标准输出) ---\n{result.stdout}")
                outputs = ("NaN",) * 10
            else:
                outputs = extract_results_from_stdout(result.stdout)
                if outputs[0] is None:
                    print(f"   ⚠️ 未能在输出中找到结果标签。已记录错误日志。")
                    os.makedirs(outdir, exist_ok=True)
                    with open(os.path.join(outdir, "error.log"), "w", encoding="utf-8") as log_f:
                        log_f.write(f"--- STDERR (报错信息) ---\n{result.stderr}\n\n--- STDOUT (标准输出) ---\n{result.stdout}")
                    outputs = ("NaN",) * 10
                else:
                    nu, f_factor, t_in, t_out, v_in, v_out, p_in, p_out, t_wing, vol = outputs
                    print(f"   ✅ Case {case_id} 成功 | Nu: {nu:.2f}, f: {f_factor:.4f}, T_wing: {t_wing:.2f}K, P_drop: {abs(p_in-p_out):.2f}Pa")
            
        except subprocess.TimeoutExpired:
            print(f"   ❌ Case {case_id} 计算超时 (>600s)，已强行终止！")
            outputs = ("NaN",) * 10
        except Exception as e:
            print(f"   ❌ 系统调度错误: {str(e)}")
            outputs = ("NaN",) * 10
            
        # 将整整 17 列极其珍贵的数据写入账本！
        with open(csv_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer_row = [case_id, 
                          f"{params['Ta']:.6f}", f"{params['Twa']:.6f}", f"{params['Tb']:.6f}", 
                          f"{params['Ts']:.6f}", f"{params['Tt']:.6f}", f"{params['Tad']:.6f}"]
            # 拼接解包出的那 10 个提取数据
            writer_row.extend(list(outputs))
            writer.writerow(writer_row)

    print("\n🎉 全局计算完毕！")
    print(f"所有特征解耦数据均已保存至: {os.path.abspath(csv_file)}")

if __name__ == "__main__":
    main()