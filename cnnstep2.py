#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
严谨的 CFD 性能参数预测模型训练脚本
【功能说明】：
1. 彻底修复数据泄露：先打乱划分训练集/测试集，再仅基于训练集计算统计分布。
2. 包含完整的评估与绘图逻辑：训练结束后自动生成 Loss 收敛曲线图和 Nu/f 误差散点图。
"""

import os
import json
import argparse
import sys

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(errors="replace")

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import pandas as pd
import numpy as np
from PIL import Image
from torchvision import transforms
import matplotlib.pyplot as plt
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

from cnn_model_definition import CFDFieldToPerformanceCNN

PARAM_COLS = ['Ta', 'Twa', 'Tb', 'Ts', 'Tt', 'Tad']
REQUIRED_IMAGE_FILES = ['velocity_magnitude.png', 'pressure.png', 'temperature.png']

# ==========================================
# 工具函数：计算数据集统计量 (绝对防止数据泄露)
# ==========================================
def calculate_dataset_stats(data_frame, train_indices, param_cols):
    train_df = data_frame.iloc[train_indices]
    stats = {'target': {}, 'param': {}}
    
    # Target 统计量
    stats['target']['nu_mean'] = float(train_df['Nu'].mean())
    stats['target']['nu_std'] = float(train_df['Nu'].std())
    stats['target']['f_mean'] = float(train_df['f'].mean())
    stats['target']['f_std'] = float(train_df['f'].std())
    
    # 物理参数 统计量
    for col in param_cols:
        stats['param'][f'{col}_mean'] = float(train_df[col].mean())
        stats['param'][f'{col}_std'] = float(train_df[col].std())
    
    return stats

# ==========================================
# 数据集类
# ==========================================
class CFDFieldDataset(Dataset):
    def __init__(self, data_dir, data_frame, valid_indices, stats, transform=None, field_types=None):
        self.data_dir = data_dir
        self.data_frame = data_frame
        self.valid_indices = valid_indices
        self.transform = transform
        self.field_types = field_types or ['velocity_field', 'pressure_field', 'temperature_field']
        # 修复:使用正确的 4 个物理参数 (根据实际数据集选择最重要的4个)
        self.param_cols = PARAM_COLS
        
        if stats is None:
            raise ValueError("必须传入统计量字典以进行归一化！")
        self.target_stats = stats['target']
        self.param_stats = stats['param']

        # 修复:直接从 DataFrame 获取有效的 case_id,而不是扫描目录
        self.case_ids = data_frame.iloc[valid_indices]['case_id'].values

    def __len__(self):
        return len(self.valid_indices)
    
    def __getitem__(self, idx):
        actual_idx = self.valid_indices[idx]
        row = self.data_frame.iloc[actual_idx]
        
        # 修复:根据 case_id 构建目录路径
        case_id = int(row['case_id'])
        sol_dir = f"case_{case_id}_cfd_solution"
        img_dir = os.path.join(self.data_dir, sol_dir)
        
        field_map = {'velocity_field': 'velocity_magnitude.png', 'pressure_field': 'pressure.png', 'temperature_field': 'temperature.png'}
        
        # 1. 图像处理
        imgs = []
        for ft in self.field_types:
            p = os.path.join(img_dir, field_map.get(ft, f'{ft}.png'))
            if os.path.exists(p):
                img = Image.open(p).convert('RGB')
                if self.transform: img = self.transform(img)
                imgs.append(img)
            else:
                print(f"[WARN] 图像文件不存在: {p}")
                imgs.append(torch.zeros(3, 224, 224))
        images = torch.stack(imgs, dim=0)
        
        # 2. 物理参数 Z-score 归一化
        params = []
        for col in self.param_cols:
            val = float(row[col])
            mean = self.param_stats[f'{col}_mean']
            std = self.param_stats[f'{col}_std']
            params.append((val - mean) / (std + 1e-8))
        params_tensor = torch.tensor(params, dtype=torch.float32)
        
        # 3. 输出目标 Z-score 归一化
        norm_nu = (float(row['Nu']) - self.target_stats['nu_mean']) / (self.target_stats['nu_std'] + 1e-8)
        norm_f = (float(row['f']) - self.target_stats['f_mean']) / (self.target_stats['f_std'] + 1e-8)
        performance = torch.tensor([norm_nu, norm_f], dtype=torch.float32)
        
        return {'images': images, 'parameters': params_tensor, 'performance': performance, 'case_id': case_id}

def collate_fn(batch):
    return {
        'images': torch.stack([item['images'] for item in batch], dim=0),
        'parameters': torch.stack([item['parameters'] for item in batch], dim=0),
        'performance': torch.stack([item['performance'] for item in batch], dim=0),
        'case_id': [item['case_id'] for item in batch]
    }

def validate_training_rows(data_frame, data_dir):
    required_cols = ['case_id', 'Nu', 'f'] + PARAM_COLS
    missing_cols = [col for col in required_cols if col not in data_frame.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns in labels CSV: {missing_cols}")

    valid_rows = []
    skipped = {'bad_numeric': 0, 'bad_target': 0, 'missing_images': 0}

    for _, row in data_frame.iterrows():
        try:
            case_id = int(row['case_id'])
            values = [float(row[col]) for col in ['Nu', 'f'] + PARAM_COLS]
        except Exception:
            skipped['bad_numeric'] += 1
            continue

        if not all(np.isfinite(values)) or values[0] <= 0 or values[1] <= 0:
            skipped['bad_target'] += 1
            continue

        case_dir = os.path.join(data_dir, f'case_{case_id}_cfd_solution')
        if not all(os.path.exists(os.path.join(case_dir, name)) for name in REQUIRED_IMAGE_FILES):
            skipped['missing_images'] += 1
            continue

        valid_rows.append(row)

    clean_df = pd.DataFrame(valid_rows).reset_index(drop=True)
    print(f"[INFO] Validated labels: kept {len(clean_df)} / {len(data_frame)} rows")
    for reason, count in skipped.items():
        if count:
            print(f"[WARN] Skipped {count} rows due to {reason}")
    return clean_df

# ==========================================
# 训练与评估函数
# ==========================================
def train_model(model, train_loader, val_loader, criterion, optimizer, num_epochs=100, device='cpu', model_dir='.'):
    train_hist, val_hist = [], []
    model.to(device)
    best_loss = float('inf')
    
    for epoch in range(num_epochs):
        model.train()
        run_loss = 0.0
        
        for data in train_loader:
            imgs = data['images'].to(device)
            params = data['parameters'].to(device)
            targets = data['performance'].to(device)
            
            optimizer.zero_grad()
            outputs = model(imgs, params)
            loss = criterion(outputs, targets)
            loss.backward()
            optimizer.step()
            run_loss += loss.item() * imgs.size(0)
            
        avg_train_loss = run_loss / len(train_loader.dataset)
        train_hist.append(avg_train_loss)
        
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for data in val_loader:
                imgs = data['images'].to(device)
                params = data['parameters'].to(device)
                targets = data['performance'].to(device)
                outputs = model(imgs, params)
                loss = criterion(outputs, targets)
                val_loss += loss.item() * imgs.size(0)
        
        avg_val_loss = val_loss / len(val_loader.dataset)
        val_hist.append(avg_val_loss)
        
        print(f"Epoch [{epoch+1}/{num_epochs}] Train Loss: {avg_train_loss:.6f} | Val Loss: {avg_val_loss:.6f}")
        
        if avg_val_loss < best_loss:
            best_loss = avg_val_loss
            torch.save(model.state_dict(), os.path.join(model_dir, 'best_model.pth'))

    model.load_state_dict(torch.load(os.path.join(model_dir, 'best_model.pth')))
    return train_hist, val_hist

def _mape_percent(true_values, pred_values):
    true_values = np.asarray(true_values, dtype=float)
    pred_values = np.asarray(pred_values, dtype=float)
    denom = np.maximum(np.abs(true_values), 1e-12)
    return float(np.mean(np.abs((true_values - pred_values) / denom)) * 100.0)


def _target_metrics(true_values, pred_values, prefix):
    mse = float(mean_squared_error(true_values, pred_values))
    return {
        f'{prefix}_MSE': mse,
        f'{prefix}_RMSE': float(np.sqrt(mse)),
        f'{prefix}_MAE': float(mean_absolute_error(true_values, pred_values)),
        f'{prefix}_MAPE_percent': _mape_percent(true_values, pred_values),
        f'{prefix}_R2': float(r2_score(true_values, pred_values)),
    }


def evaluate_model(model, test_loader, stats, device='cpu'):
    """评估模型并进行严格的反归一化"""
    model.to(device)
    model.eval()
    
    true_list, pred_list, case_ids = [], [], []
    with torch.no_grad():
        for data in test_loader:
            imgs = data['images'].to(device)
            params = data['parameters'].to(device)
            targets = data['performance'].to(device)
            
            outputs = model(imgs, params)
            true_list.extend(targets.cpu().numpy())
            pred_list.extend(outputs.cpu().numpy())
            case_ids.extend(data['case_id'])
            
    true_norm = np.array(true_list)
    pred_norm = np.array(pred_list)
    
    true_real = np.zeros_like(true_norm)
    pred_real = np.zeros_like(pred_norm)
    
    t_stats = stats['target']
    # 反归一化 Nu
    true_real[:, 0] = true_norm[:, 0] * (t_stats['nu_std'] + 1e-8) + t_stats['nu_mean']
    pred_real[:, 0] = pred_norm[:, 0] * (t_stats['nu_std'] + 1e-8) + t_stats['nu_mean']
    # 反归一化 f
    true_real[:, 1] = true_norm[:, 1] * (t_stats['f_std'] + 1e-8) + t_stats['f_mean']
    pred_real[:, 1] = pred_norm[:, 1] * (t_stats['f_std'] + 1e-8) + t_stats['f_mean']
    
    metrics = {}
    metrics.update(_target_metrics(true_real[:, 0], pred_real[:, 0], 'Nu'))
    metrics.update(_target_metrics(true_real[:, 1], pred_real[:, 1], 'f'))
    return metrics, true_real, pred_real, case_ids


def save_evaluation_artifacts(metrics, true_vals, pred_vals, case_ids, save_dir):
    """Save paper-ready test metrics and per-case predictions."""
    os.makedirs(save_dir, exist_ok=True)

    eps = 1e-12
    true_nu = true_vals[:, 0]
    pred_nu = pred_vals[:, 0]
    true_f = true_vals[:, 1]
    pred_f = pred_vals[:, 1]

    detail_df = pd.DataFrame({
        'case_id': case_ids,
        'true_Nu': true_nu,
        'pred_Nu': pred_nu,
        'error_Nu': pred_nu - true_nu,
        'abs_error_Nu': np.abs(pred_nu - true_nu),
        'ape_Nu_percent': np.abs((pred_nu - true_nu) / np.maximum(np.abs(true_nu), eps)) * 100.0,
        'true_f': true_f,
        'pred_f': pred_f,
        'error_f': pred_f - true_f,
        'abs_error_f': np.abs(pred_f - true_f),
        'ape_f_percent': np.abs((pred_f - true_f) / np.maximum(np.abs(true_f), eps)) * 100.0,
        'true_eta_proxy': true_nu / np.maximum(true_f, eps) ** (1.0 / 3.0),
        'pred_eta_proxy': pred_nu / np.maximum(pred_f, eps) ** (1.0 / 3.0),
    })
    detail_path = os.path.join(save_dir, 'test_predictions.csv')
    detail_df.to_csv(detail_path, index=False, encoding='utf-8-sig')

    table7_df = pd.DataFrame([
        {
            'target': 'Nu',
            'R2': metrics['Nu_R2'],
            'MSE': metrics['Nu_MSE'],
            'RMSE': metrics['Nu_RMSE'],
            'MAE': metrics['Nu_MAE'],
            'MAPE_percent': metrics['Nu_MAPE_percent'],
        },
        {
            'target': 'f',
            'R2': metrics['f_R2'],
            'MSE': metrics['f_MSE'],
            'RMSE': metrics['f_RMSE'],
            'MAE': metrics['f_MAE'],
            'MAPE_percent': metrics['f_MAPE_percent'],
        },
    ])
    table7_path = os.path.join(save_dir, 'paper_table7_metrics.csv')
    table7_df.to_csv(table7_path, index=False, encoding='utf-8-sig')

    summary_path = os.path.join(save_dir, 'paper_table7_metrics.md')
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write('| Target | R2 | MSE | RMSE | MAE | MAPE/% |\n')
        f.write('|---|---:|---:|---:|---:|---:|\n')
        for _, row in table7_df.iterrows():
            f.write(
                f"| {row['target']} | {row['R2']:.4f} | {row['MSE']:.6g} | "
                f"{row['RMSE']:.6g} | {row['MAE']:.6g} | {row['MAPE_percent']:.3f} |\n"
            )

    print(f"[INFO] Saved per-case test predictions: {detail_path}")
    print(f"[INFO] Saved paper Table 7 metrics: {table7_path}")
    print(f"[INFO] Saved markdown Table 7 metrics: {summary_path}")


def save_split_indices(save_dir, data_frame, train_idx, val_idx, test_idx):
    rows = []
    for split_name, indices in [('train', train_idx), ('val', val_idx), ('test', test_idx)]:
        for idx in indices:
            rows.append({'split': split_name, 'row_index': int(idx), 'case_id': int(data_frame.iloc[idx]['case_id'])})
    split_df = pd.DataFrame(rows)
    split_path = os.path.join(save_dir, 'dataset_split.csv')
    split_df.to_csv(split_path, index=False, encoding='utf-8-sig')
    print(f"[INFO] Saved dataset split: {split_path}")

# ==========================================
# 绘图工具函数 (训练结束后生成并保存图表)
# ==========================================
def plot_results(true_vals, pred_vals, save_dir):
    """绘制 Nu 和 f 的真实值与预测值散点对比图"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # 绘制 Nu - 添加轻微抖动让重叠的点分开
    nu_true = true_vals[:, 0]
    nu_pred = pred_vals[:, 0]
    # 添加随机抖动 (jitter)
    nu_metrics = _target_metrics(nu_true, nu_pred, 'Nu')
    
    ax1.scatter(nu_true, nu_pred, alpha=0.75, c='#1f77b4', edgecolors='white', s=56, linewidth=0.8)
    min_v, max_v = true_vals[:, 0].min() - 2, true_vals[:, 0].max() + 2
    ax1.plot([min_v, max_v], [min_v, max_v], 'r--', lw=2, label='Ideal (y=x)')
    ax1.set_xlim(min_v, max_v)
    ax1.set_ylim(min_v, max_v)
    ax1.set_title(f"Nu Prediction (n={len(nu_true)}, R2={nu_metrics['Nu_R2']:.3f}, MAE={nu_metrics['Nu_MAE']:.3f})")
    ax1.set_xlabel('CFD True Nu')
    ax1.set_ylabel('CNN Predicted Nu')
    ax1.legend()
    ax1.grid(True, linestyle=':', alpha=0.6)
    
    # 绘制 f - 添加轻微抖动
    f_true = true_vals[:, 1]
    f_pred = pred_vals[:, 1]
    f_metrics = _target_metrics(f_true, f_pred, 'f')
    
    ax2.scatter(f_true, f_pred, alpha=0.75, c='#ff7f0e', edgecolors='white', s=56, linewidth=0.8)
    min_v_f, max_v_f = true_vals[:, 1].min() - 0.0005, true_vals[:, 1].max() + 0.0005
    ax2.plot([min_v_f, max_v_f], [min_v_f, max_v_f], 'r--', lw=2, label='Ideal (y=x)')
    ax2.set_xlim(min_v_f, max_v_f)
    ax2.set_ylim(min_v_f, max_v_f)
    ax2.set_title(f"f Prediction (n={len(f_true)}, R2={f_metrics['f_R2']:.3f}, MAE={f_metrics['f_MAE']:.6f})")
    ax2.set_xlabel('CFD True f')
    ax2.set_ylabel('CNN Predicted f')
    ax2.legend()
    ax2.grid(True, linestyle=':', alpha=0.6)
    
    plt.tight_layout()
    save_path = os.path.join(save_dir, 'final_prediction.png')
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"🎯 预测结果误差散点图已保存至: {save_path}")

def main():
    parser = argparse.ArgumentParser(description='Train CNN model on a selectable number of CFD cases.')
    parser.add_argument('--num-samples', type=int, default=None,
                        help='Number of valid cases to use. Default: use all valid cases.')
    parser.add_argument('--sample-mode', choices=['first', 'random'], default='first',
                        help='How to choose cases when --num-samples is set. Default: first.')
    parser.add_argument('--seed', type=int, default=42,
                        help='Random seed for sampling and train/val/test split. Default: 42.')
    parser.add_argument('--eval-only', action='store_true',
                        help='Only evaluate an existing trained model and regenerate paper metrics.')
    parser.add_argument('--model-path', default=None,
                        help='Model .pth path for --eval-only. Default: ai_cnn_model_results/cfd_cnn_model.pth.')
    args = parser.parse_args()

    print(">>> 启动无数据泄露的严谨 CFD 参数预测模型训练 <<<")
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"使用计算设备: {device}")
    
    # 修复:使用正确的数据目录和清理后的 CSV 文件
    results_dir = 'consol_cfddata'
    
    # 优先使用 consol_cfddata 目录下的统一标签文件
    csv_file = os.path.join(results_dir, 'labels.csv')
    
    # 如果不存在,尝试 csv_data 目录下的文件
    if not os.path.exists(csv_file):
        csv_file = os.path.join('csv_data', 'final_results_unique.csv')
    
    if not os.path.exists(csv_file):
        csv_file = os.path.join('csv_data', 'final_results_clean.csv')
        print("⚠️  警告: 未找到去重后的 CSV,使用清理后的文件")
    
    # 如果清理后的文件也不存在,尝试原始文件
    if not os.path.exists(csv_file):
        csv_file = os.path.join('csv_data', 'final_results.csv')
        print("⚠️  警告: 使用原始 CSV 文件(可能包含错误行)")
    
    csv_file = os.path.join(results_dir, 'labels.csv')

    model_dir = 'ai_cnn_model_results'
    os.makedirs(model_dir, exist_ok=True)
    
    if not os.path.exists(csv_file):
        print(f"❌ 错误: CSV 文件不存在: {csv_file}")
        return

    # 统一使用 0.5 作为均值和方差进行标准化
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5])
    ])
    
    # 修复:使用 on_bad_lines='skip' 跳过格式错误的行
    try:
        data_frame = pd.read_csv(csv_file, on_bad_lines='skip')
    except Exception as e:
        print(f"❌ CSV 读取失败: {e}")
        return
    
    print(f"📊 原始数据行数: {len(data_frame)}")
    print(f"📋 列名: {list(data_frame.columns)}")
    
    # 修复:过滤掉 Nu 或 f 为 NaN 的失败案例
    data_frame = validate_training_rows(data_frame, results_dir)
    valid_mask = data_frame['Nu'].notna() & data_frame['f'].notna()
    data_frame = data_frame[valid_mask].reset_index(drop=True)

    if args.num_samples is not None:
        if args.num_samples <= 0:
            raise ValueError("--num-samples must be a positive integer")

        requested = args.num_samples
        available = len(data_frame)
        use_count = min(requested, available)

        if args.sample_mode == 'random':
            data_frame = data_frame.sample(n=use_count, random_state=args.seed).reset_index(drop=True)
        else:
            data_frame = data_frame.head(use_count).reset_index(drop=True)

        if requested > available:
            print(f"[WARN] Requested {requested} samples, but only {available} valid cases are available. Using {use_count}.")
        print(f"[INFO] Using {len(data_frame)} valid cases for this run (mode={args.sample_mode}).")
    
    print(f"✅ 有效样本数: {len(data_frame)} (已过滤 {valid_mask.sum() - len(data_frame)} 个失败案例)")
    
    if len(data_frame) < 10:
        print("❌ 错误: 有效样本数太少,无法训练!")
        return
    
    valid_indices = list(range(len(data_frame)))
    
    # ---------------------------------------------------------
    # 【数据划分核心逻辑】：必须打乱数据后才能进行统计！
    # ---------------------------------------------------------
    np.random.seed(args.seed)
    shuffled_indices = np.random.permutation(valid_indices)
    
    # 小样本集调整:至少保证每个集合有 1 个样本
    if len(shuffled_indices) <= 5:
        train_size = max(1, int(0.6 * len(shuffled_indices)))
        val_size = max(1, int(0.2 * len(shuffled_indices)))
    else:
        train_size = int(0.75 * len(shuffled_indices))
        val_size = int(0.15 * len(shuffled_indices))
    
    train_idx = shuffled_indices[:train_size]
    val_idx = shuffled_indices[train_size:train_size+val_size]
    test_idx = shuffled_indices[train_size+val_size:]
    
    # 确保测试集至少有 1 个样本
    if len(test_idx) == 0:
        test_idx = val_idx[-1:]
        val_idx = val_idx[:-1]
    
    print(f"训练集: {len(train_idx)}, 验证集: {len(val_idx)}, 测试集: {len(test_idx)}")
    
    # 计算统计分布（仅依赖训练集）
    save_split_indices(model_dir, data_frame, train_idx, val_idx, test_idx)

    stats_path = os.path.join(model_dir, 'dataset_stats.json')
    if args.eval_only and os.path.exists(stats_path):
        with open(stats_path, 'r', encoding='utf-8') as f:
            stats = json.load(f)
        print(f"[INFO] Loaded existing normalization stats: {stats_path}")
    else:
        stats = calculate_dataset_stats(data_frame, train_idx, PARAM_COLS)
        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=4)
        
    train_ds = CFDFieldDataset(results_dir, data_frame, train_idx, stats, transform)
    val_ds = CFDFieldDataset(results_dir, data_frame, val_idx, stats, transform)
    test_ds = CFDFieldDataset(results_dir, data_frame, test_idx, stats, transform)
    
    loaders = {
        'train': DataLoader(train_ds, batch_size=16, shuffle=True, collate_fn=collate_fn),
        'val': DataLoader(val_ds, batch_size=16, shuffle=False, collate_fn=collate_fn),
        'test': DataLoader(test_ds, batch_size=16, shuffle=False, collate_fn=collate_fn)
    }
    
    model = CFDFieldToPerformanceCNN(num_fields=3, num_scalars=len(PARAM_COLS), output_size=2)
    optimizer = optim.Adam(model.parameters(), lr=0.0005, weight_decay=1e-4)
    criterion = nn.MSELoss()

    if args.eval_only:
        model_path = args.model_path or os.path.join(model_dir, 'cfd_cnn_model.pth')
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found for --eval-only: {model_path}")
        model.load_state_dict(torch.load(model_path, map_location=device))
        print(f"[INFO] Loaded model for evaluation: {model_path}")

        metrics, true_vals, pred_vals, case_ids = evaluate_model(model, loaders['test'], stats, device)
        print("\n[INFO] Test metrics:")
        for k, v in metrics.items():
            print(f"  {k}: {v:.6f}")

        with open(os.path.join(model_dir, 'metrics.json'), 'w', encoding='utf-8') as f:
            json.dump({k: float(v) for k, v in metrics.items()}, f, indent=4)

        save_evaluation_artifacts(metrics, true_vals, pred_vals, case_ids, model_dir)
        plot_results(true_vals, pred_vals, model_dir)
        return
    
    print("\n🚀 开始训练网络...")
    # 使用标准训练轮次
    num_epochs = 50
    train_hist, val_hist = train_model(model, loaders['train'], loaders['val'], criterion, optimizer, num_epochs=num_epochs, device=device, model_dir=model_dir)
    
    # ==========================================
    # 训练结束：生成并保存 Loss 收敛曲线
    # ==========================================
    print("\n📊 正在生成训练报告与图表...")
    plt.figure(figsize=(10, 6))
    plt.plot(train_hist, label='Train Loss (MSE)', linewidth=2)
    plt.plot(val_hist, label='Validation Loss (MSE)', linewidth=2)
    plt.title('Training and Validation Loss Convergence')
    plt.xlabel('Epochs')
    plt.ylabel('MSE Loss (Normalized)')
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.7)
    loss_curve_path = os.path.join(model_dir, 'loss_curve.png')
    plt.savefig(loss_curve_path, dpi=300)
    plt.close()
    print(f"📉 Loss 收敛曲线已保存至: {loss_curve_path}")

    # ==========================================
    # 评估并在测试集上生成预测散点图
    # ==========================================
    metrics, true_vals, pred_vals, case_ids = evaluate_model(model, loaders['test'], stats, device)
    
    print("\n✅ 评估指标 (测试集 - 物理真实值):")
    for k, v in metrics.items(): print(f"  {k}: {v:.6f}")
    
    with open(os.path.join(model_dir, 'metrics.json'), 'w', encoding='utf-8') as f:
        json.dump({k: float(v) for k, v in metrics.items()}, f, indent=4)
    save_evaluation_artifacts(metrics, true_vals, pred_vals, case_ids, model_dir)
        
    # 调用绘图工具绘制 Nu/f 散点图
    plot_results(true_vals, pred_vals, model_dir)
    print(f"🎯 预测结果误差散点图已保存至: {os.path.join(model_dir, 'final_prediction.png')}")
    
    torch.save(model.state_dict(), os.path.join(model_dir, 'cfd_cnn_model.pth'))
    print("\n🏆 模型权重及所有统计量已保存完毕。训练流程结束。")

if __name__ == '__main__':
    main()
