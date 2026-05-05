#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
严谨的 CNN 模型预测与可视化执行脚本
【功能说明】：
1. 预测前置：强制加载真实物理参数，激活模型的多模态分支。
2. 物理反归一化：将网络输出转换为具有真实物理意义的 Nu 和 f 数值。
3. 高清可视化：自动将输入的三场流体力学云图与预测结果拼接，生成用于学术汇报的可视化图表。
"""

import torch
import numpy as np
import os
import json
from PIL import Image
from torchvision import transforms
import matplotlib.pyplot as plt

# 导入我们的多模态模型定义
from cnn_model_definition import CFDFieldToPerformanceCNN

def load_trained_model(model_path, device):
    """加载模型结构与训练好的权重"""
    # 结构必须与训练时保持一致：3个物理场图像，4个标量输入
    model = CFDFieldToPerformanceCNN(num_fields=3, num_scalars=4, output_size=2)
    if os.path.exists(model_path):
        model.load_state_dict(torch.load(model_path, map_location=device), strict=False)
        model.to(device)
        model.eval()
        return model
    else:
        raise FileNotFoundError(f"找不到模型文件 {model_path}，请先运行训练脚本。")

def preprocess_field_images(velocity_img_path, pressure_img_path, temperature_img_path, device):
    """
    流场图像预处理
    【注意】：此处必须与训练脚本保持完全相同的 0.5 均值/方差标准化
    """
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5])
    ])
    
    vel_img = Image.open(velocity_img_path).convert('RGB')
    pres_img = Image.open(pressure_img_path).convert('RGB')
    temp_img = Image.open(temperature_img_path).convert('RGB')
    
    # 堆叠成 (3, 3, 224, 224) 的张量形状
    images = torch.stack([transform(vel_img), transform(pres_img), transform(temp_img)], dim=0)
    return images.unsqueeze(0).to(device)

def predict_performance(model, images, actual_scalars, stats_dict):
    """
    进行预测，并将输出转换回真实的物理数值
    """
    with torch.no_grad():
        # 1. 物理参数标量的 Z-score 归一化 (使用训练集的统计特性)
        p_stats = stats_dict['param']
        norm_params = [
            (actual_scalars[0] - p_stats['Tt_mean']) / (p_stats['Tt_std'] + 1e-8),
            (actual_scalars[1] - p_stats['Ts_mean']) / (p_stats['Ts_std'] + 1e-8),
            (actual_scalars[2] - p_stats['Tad_mean']) / (p_stats['Tad_std'] + 1e-8),
            (actual_scalars[3] - p_stats['Tb_mean']) / (p_stats['Tb_std'] + 1e-8)
        ]
        params_tensor = torch.tensor([norm_params], dtype=torch.float32).to(images.device)
        
        # 2. 网络前向传播 (得到的是归一化后的输出)
        outputs = model(images, params_tensor)
        norm_nu, norm_f = outputs[0].cpu().numpy()
        
        # 3. 目标反归一化，还原成真实世界的 Nu 和 f
        t_stats = stats_dict['target']
        real_nu = norm_nu * (t_stats['nu_std'] + 1e-8) + t_stats['nu_mean']
        real_f  = norm_f  * (t_stats['f_std'] + 1e-8) + t_stats['f_mean']
        
        return real_nu, real_f

def visualize_prediction(velocity_path, pressure_path, temp_path, nu_pred, f_pred, save_dir):
    """
    可视化当前的输入流场图，并将预测结果醒目地写在图表正上方
    """
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    
    try:
        # 显示速度场
        axes[0].imshow(Image.open(velocity_path))
        axes[0].set_title('Velocity Field', fontsize=14, fontweight='bold')
        axes[0].axis('off')
        
        # 显示压力场
        axes[1].imshow(Image.open(pressure_path))
        axes[1].set_title('Pressure Field', fontsize=14, fontweight='bold')
        axes[1].axis('off')
        
        # 显示温度场
        axes[2].imshow(Image.open(temp_path))
        axes[2].set_title('Temperature Field', fontsize=14, fontweight='bold')
        axes[2].axis('off')
        
        # 计算综合性能评价因子 \eta
        target_param = nu_pred / (f_pred**(1/3)) if f_pred > 0 else 0
        
        # 顶部大标题：融合预测数值展示
        title_text = (f"Multimodal CNN Prediction\n"
                      f"Nu: {nu_pred:.4f}  |  f: {f_pred:.6f}  |  Performance (\u03b7): {target_param:.4f}")
        plt.suptitle(title_text, fontsize=18, fontweight='heavy', color='#800000', y=1.05)
        
        save_path = os.path.join(save_dir, 'current_prediction_visual.png')
        plt.tight_layout()
        plt.savefig(save_path, dpi=200, bbox_inches='tight')
        plt.close()
        return save_path
        
    except Exception as e:
        print(f"⚠️ 流场可视化生成失败，请检查图像文件是否存在: {e}")
        return None

def main():
    print(">>> 启动基于多模态融合的 CFD 性能预测与可视化 <<<")
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"计算设备: {device}")
    
    # 目录配置
    model_dir = 'ai_cnn_model_results'
    model_path = os.path.join(model_dir, 'cfd_cnn_model.pth')
    stats_path = os.path.join(model_dir, 'dataset_stats.json')
    
    # 检查核心配置文件
    if not os.path.exists(stats_path):
        print("❌ 致命错误：缺少 dataset_stats.json！请先运行 cnn_performance_predictor.py 完成训练。")
        return
        
    with open(stats_path, 'r') as f:
        stats_dict = json.load(f)
        
    model = load_trained_model(model_path, device)
    
    # 指向你要预测的那一组 CFD 图片文件夹
    # ⚠️ 【用户注意】：实际使用时，请修改为你真正要预测的文件夹路径！
    latest_solution_dir = 'results/latest_cfd_solution'
    if not os.path.exists(latest_solution_dir):
        print(f"⚠️ 提示: 未找到待预测图像目录 {latest_solution_dir}，脚本终止。")
        print("（请将最新的 CFD 输出图片存入该文件夹，或修改代码中的路径）")
        return
    
    # ==========================================
    # ⚠️ 极度重要：输入对应的真实物理几何参数
    # 顺序为: [Tt (横向间距), Ts (纵向间距), Tad (交错位移), Tb (厚度)]
    # ==========================================
    actual_current_scalars = [0.8, 1.0, 0.25, 0.12] 
    print(f"当前输入的几何参数 (Tt, Ts, Tad, Tb): {actual_current_scalars}")
    
    # 图片路径拼接
    vel_path = os.path.join(latest_solution_dir, 'velocity_magnitude.png')
    pres_path = os.path.join(latest_solution_dir, 'pressure.png')
    temp_path = os.path.join(latest_solution_dir, 'temperature.png')
    
    # 加载张量
    images = preprocess_field_images(vel_path, pres_path, temp_path, device)
    
    # 核心：预测与反归一化
    nu_pred, f_pred = predict_performance(model, images, actual_current_scalars, stats_dict)
    
    print(f"\n✅ === 最终物理预测结果 ===")
    print(f"  Nu (努塞尔数): {nu_pred:.4f}")
    print(f"  f  (摩擦因子): {f_pred:.6f}")
    if f_pred > 0:
        print(f"  综合评价因子 \u03b7 = Nu/(f^(1/3)): {nu_pred / (f_pred**(1/3)):.4f}")
    print("=========================\n")

    # ==========================================
    # 生成可视化结果展示图
    # ==========================================
    vis_path = visualize_prediction(vel_path, pres_path, temp_path, nu_pred, f_pred, model_dir)
    
    if vis_path:
        print(f"📸 可视化图表生成成功！")
        print(f"📍 请前往此处查看并截图用于论文: {os.path.abspath(vis_path)}")
    else:
        print("可视化生成失败，但数值预测已完成。")

if __name__ == "__main__":
    main()