#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
检查数据集完整性 - 验证500个案例的图像文件是否完整
"""

import os
import sys
from pathlib import Path
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def check_dataset_integrity():
    print("="*60)
    print("🔍 检查数据集完整性")
    print("="*60)
    
    # 读取标签文件
    csv_file = PROJECT_ROOT / 'consol_cfddata' / 'labels.csv'
    if not os.path.exists(csv_file):
        print(f"❌ 错误: 找不到 {csv_file}")
        return
    
    df = pd.read_csv(csv_file, on_bad_lines='skip')
    print(f"\n📊 标签文件统计:")
    print(f"  总行数: {len(df)}")
    
    # 过滤有效数据
    valid_mask = df['Nu'].notna() & df['f'].notna()
    df_valid = df[valid_mask]
    print(f"  有效行数 (Nu和f非NaN): {len(df_valid)}")
    
    # 检查图像完整性
    complete_cases = []
    missing_cases = []
    
    print(f"\n🔍 正在检查 {len(df_valid)} 个案例的图像文件...")
    
    for idx, row in df_valid.iterrows():
        case_id = int(row['case_id'])
        img_dir = PROJECT_ROOT / 'consol_cfddata' / f'case_{case_id}_cfd_solution'
        
        required_files = [
            'velocity_magnitude.png',
            'pressure.png',
            'temperature.png'
        ]
        
        has_all = all(os.path.exists(os.path.join(img_dir, f)) for f in required_files)
        
        if has_all:
            complete_cases.append(case_id)
        else:
            missing_cases.append(case_id)
    
    print(f"\n✅ 检查结果:")
    print(f"  图像完整的案例数: {len(complete_cases)}")
    print(f"  缺失图像的案例数: {len(missing_cases)}")
    
    if missing_cases:
        print(f"\n⚠️  前20个缺失图像的案例ID: {missing_cases[:20]}")
        print(f"\n💡 建议: 只使用图像完整的 {len(complete_cases)} 个案例进行训练")
        
        # 创建仅包含完整案例的CSV
        df_complete = df_valid[df_valid['case_id'].isin(complete_cases)]
        output_file = PROJECT_ROOT / 'consol_cfddata' / 'labels_complete.csv'
        df_complete.to_csv(output_file, index=False)
        print(f"\n✅ 已生成完整案例标签文件: {output_file}")
        print(f"   包含 {len(df_complete)} 个案例")
    else:
        print(f"\n🎉 所有案例的图像文件都完整!")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    check_dataset_integrity()
