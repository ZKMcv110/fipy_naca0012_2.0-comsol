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
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import pandas as pd
import numpy as np
from PIL import Image
from torchvision import transforms
import matplotlib.pyplot as plt
from sklearn.metrics import mean_squared_error, mean_absolute_error

from cnn_model_definition import CFDFieldToPerformanceCNN

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
        self.param_cols = ['Tt', 'Ts', 'Tad', 'Tb']
        
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

def evaluate_model(model, test_loader, stats, device='cpu'):
    """评估模型并进行严格的反归一化"""
    model.to(device)
    model.eval()
    
    true_list, pred_list = [], []
    with torch.no_grad():
        for data in test_loader:
            imgs = data['images'].to(device)
            params = data['parameters'].to(device)
            targets = data['performance'].to(device)
            
            outputs = model(imgs, params)
            true_list.extend(targets.cpu().numpy())
            pred_list.extend(outputs.cpu().numpy())
            
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
    
    metrics = {
        'Nu_MSE': mean_squared_error(true_real[:, 0], pred_real[:, 0]),
        'f_MSE': mean_squared_error(true_real[:, 1], pred_real[:, 1]),
        'Nu_MAE': mean_absolute_error(true_real[:, 0], pred_real[:, 0]),
        'f_MAE': mean_absolute_error(true_real[:, 1], pred_real[:, 1])
    }
    return metrics, true_real, pred_real

# ==========================================
# 绘图工具函数 (训练结束后生成并保存图表)
# ==========================================
def plot_results(true_vals, pred_vals, save_dir):
    """绘制 Nu 和 f 的真实值与预测值散点对比图"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # 绘制 Nu
    ax1.scatter(true_vals[:, 0], pred_vals[:, 0], alpha=0.7, c='#1f77b4', edgecolors='white', s=50)
    min_v, max_v = true_vals[:, 0].min(), true_vals[:, 0].max()
    ax1.plot([min_v, max_v], [min_v, max_v], 'r--', lw=2, label='Ideal (y=x)')
    ax1.set_title(f'Nu Prediction on Test Set (MAE: {mean_absolute_error(true_vals[:,0], pred_vals[:,0]):.2f})')
    ax1.set_xlabel('CFD True Nu')
    ax1.set_ylabel('CNN Predicted Nu')
    ax1.legend()
    ax1.grid(True, linestyle=':', alpha=0.6)
    
    # 绘制 f
    ax2.scatter(true_vals[:, 1], pred_vals[:, 1], alpha=0.7, c='#ff7f0e', edgecolors='white', s=50)
    min_v, max_v = true_vals[:, 1].min(), true_vals[:, 1].max()
    ax2.plot([min_v, max_v], [min_v, max_v], 'r--', lw=2, label='Ideal (y=x)')
    ax2.set_title(f'f Prediction on Test Set (MAE: {mean_absolute_error(true_vals[:,1], pred_vals[:,1]):.6f})')
    ax2.set_xlabel('CFD True f')
    ax2.set_ylabel('CNN Predicted f')
    ax2.legend()
    ax2.grid(True, linestyle=':', alpha=0.6)
    
    plt.tight_layout()
    plt.savefig(os.path.join(save_dir, 'final_prediction.png'), dpi=300)
    plt.close()

def main():
    print(">>> 启动无数据泄露的严谨 CFD 参数预测模型训练 <<<")
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"使用计算设备: {device}")
    
    # 修复:使用正确的数据目录
    results_dir = 'consol_cfddata'
    csv_file = os.path.join('csv_data', 'final_results.csv')
    model_dir = 'ai_cnn_model_results'
    os.makedirs(model_dir, exist_ok=True)
    
    if not os.path.exists(csv_file):
        print(f"请确保 CSV 文件存在: {csv_file}")
        return

    # 统一使用 0.5 作为均值和方差进行标准化
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5])
    ])
    
    data_frame = pd.read_csv(csv_file)
    
    # 修复:过滤掉 Nu 或 f 为 NaN 的失败案例
    valid_mask = data_frame['Nu'].notna() & data_frame['f'].notna()
    data_frame = data_frame[valid_mask].reset_index(drop=True)
    
    print(f"总样本数: {len(data_frame)}, 有效样本数: {len(data_frame)}")
    
    if len(data_frame) < 10:
        print("❌ 错误: 有效样本数太少,无法训练!")
        return
    
    valid_indices = list(range(len(data_frame)))
    
    # ---------------------------------------------------------
    # 【数据划分核心逻辑】：必须打乱数据后才能进行统计！
    # ---------------------------------------------------------
    np.random.seed(42)
    shuffled_indices = np.random.permutation(valid_indices)
    train_size = int(0.75 * len(shuffled_indices))
    val_size = int(0.15 * len(shuffled_indices))
    
    train_idx = shuffled_indices[:train_size]
    val_idx = shuffled_indices[train_size:train_size+val_size]
    test_idx = shuffled_indices[train_size+val_size:]
    
    print(f"训练集: {len(train_idx)}, 验证集: {len(val_idx)}, 测试集: {len(test_idx)}")
    
    # 计算统计分布（仅依赖训练集）
    stats = calculate_dataset_stats(data_frame, train_idx, ['Tt', 'Ts', 'Tad', 'Tb'])
    
    with open(os.path.join(model_dir, 'dataset_stats.json'), 'w') as f:
        json.dump(stats, f, indent=4)
        
    train_ds = CFDFieldDataset(results_dir, data_frame, train_idx, stats, transform)
    val_ds = CFDFieldDataset(results_dir, data_frame, val_idx, stats, transform)
    test_ds = CFDFieldDataset(results_dir, data_frame, test_idx, stats, transform)
    
    loaders = {
        'train': DataLoader(train_ds, batch_size=8, shuffle=True, collate_fn=collate_fn),
        'val': DataLoader(val_ds, batch_size=8, shuffle=False, collate_fn=collate_fn),
        'test': DataLoader(test_ds, batch_size=8, shuffle=False, collate_fn=collate_fn)
    }
    
    model = CFDFieldToPerformanceCNN(num_fields=3, num_scalars=4, output_size=2)
    optimizer = optim.Adam(model.parameters(), lr=0.0005, weight_decay=1e-4)
    criterion = nn.MSELoss()
    
    print("\n🚀 开始训练网络...")
    train_hist, val_hist = train_model(model, loaders['train'], loaders['val'], criterion, optimizer, num_epochs=50, device=device, model_dir=model_dir)
    
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
    metrics, true_vals, pred_vals = evaluate_model(model, loaders['test'], stats, device)
    
    print("\n✅ 评估指标 (测试集 - 物理真实值):")
    for k, v in metrics.items(): print(f"  {k}: {v:.6f}")
    
    with open(os.path.join(model_dir, 'metrics.json'), 'w') as f:
        json.dump({k: float(v) for k, v in metrics.items()}, f, indent=4)
        
    # 调用绘图工具绘制 Nu/f 散点图
    plot_results(true_vals, pred_vals, model_dir)
    print(f"🎯 预测结果误差散点图已保存至: {os.path.join(model_dir, 'final_prediction.png')}")
    
    torch.save(model.state_dict(), os.path.join(model_dir, 'cfd_cnn_model.pth'))
    print("\n🏆 模型权重及所有统计量已保存完毕。训练流程结束。")

if __name__ == '__main__':
    main()