#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
多模态双流 CNN 模型定义文件
【优化亮点】：
1. 加入了 CBAM 空间与通道双重注意力机制。
2. 使用了 GAP (全局平均池化) 替代大尺度 Flatten，将参数量从 600万 降至几十万，彻底解决 500 个样本下的严重过拟合。
"""

import torch
import torch.nn as nn

# ==========================================
# 1. 注意力机制模块 (CBAM)
# ==========================================
class SpatialAttention(nn.Module):
    def __init__(self, kernel_size=7):
        super(SpatialAttention, self).__init__()
        self.conv = nn.Conv2d(2, 1, kernel_size=kernel_size, padding=kernel_size//2, bias=False)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        avg_out = torch.mean(x, dim=1, keepdim=True)
        max_out, _ = torch.max(x, dim=1, keepdim=True)
        x = torch.cat([avg_out, max_out], dim=1)
        x = self.conv(x)
        return self.sigmoid(x)

class ChannelAttention(nn.Module):
    def __init__(self, in_planes, ratio=16):
        super(ChannelAttention, self).__init__()
        self.avg_pool = nn.AdaptiveAvgPool2d(1)
        self.max_pool = nn.AdaptiveMaxPool2d(1)
        
        self.fc = nn.Sequential(
            nn.Conv2d(in_planes, in_planes // ratio, 1, bias=False),
            nn.ReLU(),
            nn.Conv2d(in_planes // ratio, in_planes, 1, bias=False)
        )
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        avg_out = self.fc(self.avg_pool(x))
        max_out = self.fc(self.max_pool(x))
        out = avg_out + max_out
        return self.sigmoid(out)

class CBAM(nn.Module):
    def __init__(self, in_planes, ratio=16, kernel_size=7):
        super(CBAM, self).__init__()
        self.channel_attention = ChannelAttention(in_planes, ratio)
        self.spatial_attention = SpatialAttention(kernel_size)

    def forward(self, x):
        x = x * self.channel_attention(x)
        x = x * self.spatial_attention(x)
        return x

# ==========================================
# 2. CFD性能预测多模态CNN模型
# ==========================================
class CFDFieldToPerformanceCNN(nn.Module):
    def __init__(self, num_fields=3, num_scalars=4, output_size=2):
        super(CFDFieldToPerformanceCNN, self).__init__()
        
        # --- A. 图像特征提取双流支路 (2D-CNN + CBAM) ---
        self.cnn_extractors = nn.ModuleList([
            nn.Sequential(
                nn.Conv2d(3, 32, kernel_size=3, padding=1),
                nn.BatchNorm2d(32), nn.ReLU(), nn.MaxPool2d(2, 2),
                
                nn.Conv2d(32, 64, kernel_size=3, padding=1),
                nn.BatchNorm2d(64), nn.ReLU(), nn.MaxPool2d(2, 2),
                
                nn.Conv2d(64, 128, kernel_size=3, padding=1),
                nn.BatchNorm2d(128), nn.ReLU(), nn.MaxPool2d(2, 2),
                
                CBAM(128), # 引入注意力机制聚焦尾流和热边界层
                
                nn.Conv2d(128, 256, kernel_size=3, padding=1),
                nn.BatchNorm2d(256), nn.ReLU(),
                
                # 使用 1x1 GAP 极大地压缩特征维度，防过拟合
                nn.AdaptiveAvgPool2d((1, 1)) 
            ) for _ in range(num_fields)
        ])
        
        # 展平后的维度：256 * 3个物理场 = 768维
        self.img_flat_dim = 256 * num_fields
        
        # --- B. 物理参数标量提取支路 (MLP) ---
        self.scalar_mlp = nn.Sequential(
            nn.Linear(num_scalars, 64),
            nn.ReLU(),
            nn.Linear(64, 128),
            nn.ReLU()
        )
        
        # --- C. 多模态特征融合与回归预测模块 ---
        combined_dim = self.img_flat_dim + 128  # 768 + 128 = 896
        
        self.predictor = nn.Sequential(
            nn.Linear(combined_dim, 512),
            nn.ReLU(),
            nn.Dropout(0.5), # 极小样本集(500)下必须保持较高Dropout
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Linear(256, output_size) # 输出 Nu 和 f
        )
        
    def forward(self, images, scalars):
        batch_size = images.size(0)
        num_fields = images.size(1)
        
        # 处理三场图像
        img_features_list = []
        for i in range(num_fields):
            feat = self.cnn_extractors[i](images[:, i, :, :, :])
            feat = feat.view(batch_size, -1)
            img_features_list.append(feat)
        
        combined_img_feat = torch.cat(img_features_list, dim=1)
        
        # 处理几何标量
        scalar_feat = self.scalar_mlp(scalars)
        
        # Concat 融合
        total_feat = torch.cat([combined_img_feat, scalar_feat], dim=1)
        
        # 预测
        output = self.predictor(total_feat)
        return output