#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试单个 COMSOL 案例 - 用于调试物理特征提取
"""

import subprocess
import sys

def test_single_case():
    print("="*60)
    print("测试单个 COMSOL 案例")
    print("="*60)
    
    # 使用与 consol500组参数.py 相同的参数
    cmd = [
        sys.executable, "comsol单次执行脚本.py",
        "--Ta", "0.025",      # Ta 范围 [0.00, 0.05] 的中间值
        "--Twa", "0.40",      # Twa 范围 [0.20, 0.60] 的中间值
        "--Tb", "0.115",      # Tb 范围 [0.08, 0.15] 的中间值
        "--Tt", "0.85",       # Tt 范围 [0.50, 1.20] 的中间值
        "--Ts", "1.00",       # Ts 范围 [0.50, 1.50] 的中间值
        "--Tad", "0.50",      # Tad 范围 [0.00, 1.00] 的中间值
        "--outdir", "test_case_debug"
    ]
    
    print(f"\n执行命令:")
    print(" ".join(cmd))
    print("\n" + "-"*60)
    
    try:
        result = subprocess.run(
            cmd, 
            capture_output=False,  # 直接输出到控制台,便于实时查看
            text=True,
            timeout=600
        )
        
        print("\n" + "="*60)
        if result.returncode == 0:
            print("测试成功!")
        else:
            print(f"测试失败,返回码: {result.returncode}")
        print("="*60)
        
    except subprocess.TimeoutExpired:
        print("\n❌ 计算超时 (>600s)")
    except Exception as e:
        print(f"\n❌ 执行错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_single_case()