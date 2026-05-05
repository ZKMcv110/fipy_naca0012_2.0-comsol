#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据集自动化生成与调度主控端 - 基础双变量版
【核心功能】：
1. 拉丁超立方采样 (LHS) 均匀生成 500 个样本。
2. 通过 subprocess.run() 多进程调用 comsol单次执行脚本.py。
3. 捕获最终目标 Nu 和 f，存入包含 9 列指标的 final_results.csv 账本。
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
    """基础版：从子进程输出文本中精准抓取 Nu 和 f"""
    lines = stdout_text.split('\n')
    for line in lines:
        if "CFD_RESULT_DATA:" in line:
            parts = line.split("CFD_RESULT_DATA:")[1].strip().split(',')
            res_dict = {}
            for part in parts:
                k, v = part.split('=')
                res_dict[k.strip()] = float(v.strip())
            return res_dict.get('Nu'), res_dict.get('f')
    return None, None

def main():
    print("=====================================================")
    print("🚀 高维拓扑数据集全自动生成流水线启动 (基础双特征提取版)")
    print("=====================================================")
    
    num_samples = 500
    results_dir = "consol_cfddata"
    csv_dir = "csv_data"
    csv_file = os.path.join(csv_dir, "final_results.csv")
    
    os.makedirs(results_dir, exist_ok=True)
    os.makedirs(csv_dir, exist_ok=True)
    
    samples_df = generate_lhs_samples(num_samples)
    
    # ⚠️ 修复:每次运行都重新创建 CSV,避免重复追加
    csv_header = ['case_id', 'Ta', 'Twa', 'Tb', 'Ts', 'Tt', 'Tad', 'Nu', 'f', 'target_param', 'failure_reason']
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(csv_header)
        
    print(f"📁 准备循环调度 COMSOL 进程求解 {num_samples} 个 Cases...")
    
    for idx, row in samples_df.iterrows():
        case_id = idx + 1
        params = row.to_dict()
        outdir = os.path.join(results_dir, f"case_{case_id}_cfd_solution")
        
        print(f"\n▶ 正在派发 Case {case_id}/{num_samples}")
        
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
                nu, f_factor = "NaN", "NaN"
            else:
                nu, f_factor = extract_results_from_stdout(result.stdout)
                if nu is None:
                    print(f"   ⚠️ 未能在输出中找到结果标签。已记录错误日志。")
                    os.makedirs(outdir, exist_ok=True)
                    with open(os.path.join(outdir, "error.log"), "w", encoding="utf-8") as log_f:
                        log_f.write(f"--- STDERR (报错信息) ---\n{result.stderr}\n\n--- STDOUT (标准输出) ---\n{result.stdout}")
                    nu, f_factor = "NaN", "NaN"
                else:
                    print(f"   ✅ Case {case_id} 成功 | Nu: {nu:.2f}, f: {f_factor:.4f}")
            
        except subprocess.TimeoutExpired:
            print(f"   ❌ Case {case_id} 计算超时 (>600s)，已强行终止！")
            nu, f_factor = "NaN", "NaN"
        except Exception as e:
            print(f"   ❌ 系统调度错误: {str(e)}")
            nu, f_factor = "NaN", "NaN"
            
        # 写入 9 列数据到基础版账本
        with open(csv_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                case_id, 
                f"{params['Ta']:.6f}", f"{params['Twa']:.6f}", f"{params['Tb']:.6f}", 
                f"{params['Ts']:.6f}", f"{params['Tt']:.6f}", f"{params['Tad']:.6f}", 
                nu, f_factor
            ])

    print("\n🎉 全局计算完毕！")
    print(f"基础物理指标已保存至: {os.path.abspath(csv_file)}")

if __name__ == "__main__":
    main()