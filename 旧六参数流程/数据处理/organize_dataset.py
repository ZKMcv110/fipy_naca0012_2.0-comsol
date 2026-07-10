#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
整理 CFD 数据集 - 将标签文件整合到 consol_cfddata 目录
【功能】:
1. 复制清理后的 CSV 到 consol_cfddata/labels.csv
2. 生成数据摘要报告
3. 验证数据完整性
"""

import os
import shutil
import sys
from pathlib import Path
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def organize_dataset():
    print("="*60)
    print("📂 整理 CFD 数据集")
    print("="*60)
    
    # 源文件路径(按优先级)
    source_files = [
        PROJECT_ROOT / 'csv_data' / 'final_results_unique.csv',
        PROJECT_ROOT / 'csv_data' / 'final_results_clean.csv',
        PROJECT_ROOT / 'csv_data' / 'final_results.csv'
    ]
    
    # 目标路径
    target_dir = PROJECT_ROOT / 'consol_cfddata'
    target_file = os.path.join(target_dir, 'labels.csv')
    
    # 找到可用的源文件
    source_file = None
    for f in source_files:
        if os.path.exists(f):
            source_file = f
            break
    
    if not source_file:
        print("❌ 错误: 找不到任何 CSV 文件!")
        return
    
    print(f"\n📄 源文件: {source_file}")
    print(f"📁 目标文件: {target_file}")
    
    # 复制文件
    try:
        shutil.copy2(source_file, target_file)
        print(f"✅ 文件复制成功!")
    except Exception as e:
        print(f"❌ 文件复制失败: {e}")
        return
    
    # 读取并验证数据
    df = pd.read_csv(target_file, on_bad_lines='skip')
    valid_mask = df['Nu'].notna() & df['f'].notna()
    df_valid = df[valid_mask]
    
    print(f"\n📊 数据统计:")
    print(f"  总行数: {len(df)}")
    print(f"  有效行数 (Nu和f非NaN): {len(df_valid)}")
    print(f"  案例ID范围: {int(df_valid['case_id'].min())} - {int(df_valid['case_id'].max())}")
    
    # 检查图像文件完整性
    missing_images = []
    for idx, row in df_valid.iterrows():
        case_id = int(row['case_id'])
        img_dir = os.path.join(target_dir, f'case_{case_id}_cfd_solution')
        
        required_files = [
            'velocity_magnitude.png',
            'pressure.png',
            'temperature.png'
        ]
        
        for img_file in required_files:
            img_path = os.path.join(img_dir, img_file)
            if not os.path.exists(img_path):
                missing_images.append((case_id, img_file))
    
    if missing_images:
        print(f"\n⚠️  缺失图像文件: {len(missing_images)} 个")
        for case_id, img_file in missing_images[:5]:
            print(f"  - case_{case_id}: {img_file}")
        if len(missing_images) > 5:
            print(f"  ... 还有 {len(missing_images) - 5} 个")
    else:
        print(f"\n✅ 所有案例的图像文件完整!")
    
    # 生成摘要报告
    report_file = os.path.join(target_dir, 'dataset_summary.txt')
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("CFD 数据集摘要报告\n")
        f.write("="*60 + "\n\n")
        f.write(f"生成时间: {pd.Timestamp.now()}\n")
        f.write(f"数据来源: {source_file}\n\n")
        f.write(f"统计信息:\n")
        f.write(f"  总案例数: {len(df)}\n")
        f.write(f"  有效案例数: {len(df_valid)}\n")
        f.write(f"  案例ID范围: {int(df_valid['case_id'].min())} - {int(df_valid['case_id'].max())}\n\n")
        f.write(f"物理参数范围:\n")
        for col in ['Tt', 'Ts', 'Tad', 'Tb']:
            if col in df_valid.columns:
                f.write(f"  {col}: {df_valid[col].min():.4f} - {df_valid[col].max():.4f}\n")
        f.write(f"\n目标变量范围:\n")
        f.write(f"  Nu: {df_valid['Nu'].min():.4f} - {df_valid['Nu'].max():.4f}\n")
        f.write(f"  f: {df_valid['f'].min():.6f} - {df_valid['f'].max():.6f}\n\n")
        f.write(f"图像完整性: {'完整' if not missing_images else f'缺失 {len(missing_images)} 个文件'}\n")
    
    print(f"\n📝 摘要报告已保存至: {report_file}")
    print("\n" + "="*60)
    print("✅ 数据集整理完成!")
    print("="*60)

if __name__ == "__main__":
    organize_dataset()
