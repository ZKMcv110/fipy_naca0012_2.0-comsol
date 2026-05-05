# CNN 模型训练与预测使用指南

## 📋 前置条件

### 1. 确保已完成 CFD 仿真
- 运行 `consol500组参数.py` 生成至少 **50 个有效案例** (Nu 和 f 不为 NaN)
- 数据保存在 `consol_cfddata/` 目录下
- 结果汇总在 `csv_data/final_results.csv`

### 2. 检查依赖库
```bash
pip install torch torchvision pandas numpy scikit-learn matplotlib pillow
```

---

## 🚀 三步训练流程

### Step 1: 准备数据 ✅
无需额外操作,确保以下文件存在:
- `consol_cfddata/case_X_cfd_solution/` - 包含三场云图和 result.json
- `csv_data/final_results.csv` - 包含所有案例的参数和结果

### Step 2: 训练模型
```bash
python cnnstep2.py
```

**训练过程:**
- 自动过滤掉失败的案例 (Nu 或 f 为 NaN)
- 按 75% 训练集、15% 验证集、10% 测试集划分
- 训练 50 个 epoch
- 自动生成:
  - `ai_cnn_model_results/cfd_cnn_model.pth` - 最佳模型权重
  - `ai_cnn_model_results/dataset_stats.json` - 数据统计信息
  - `ai_cnn_model_results/loss_curve.png` - Loss 收敛曲线
  - `ai_cnn_model_results/final_prediction.png` - 预测误差散点图
  - `ai_cnn_model_results/metrics.json` - 评估指标

### Step 3: 预测新案例
```bash
python cnnstep3.py
```

**修改待预测的案例:**
编辑 `cnnstep3.py` 第 147 行:
```python
latest_solution_dir = 'consol_cfddata/case_1_cfd_solution'  # 改为目标 case
```

---

## 📊 输出说明

### 训练结果 (`ai_cnn_model_results/`)
| 文件 | 说明 |
|------|------|
| `cfd_cnn_model.pth` | 训练好的模型权重 |
| `dataset_stats.json` | 训练集的统计分布(均值/标准差) |
| `loss_curve.png` | 训练/验证 Loss 收敛曲线 |
| `final_prediction.png` | Nu 和 f 的预测 vs 真实值散点图 |
| `metrics.json` | MSE、MAE 等评估指标 |

### 预测结果
- 控制台输出: Nu、f、综合评价因子 η
- 可视化图表: `ai_cnn_model_results/current_prediction_visual.png`

---

## ⚠️ 常见问题

### Q1: 提示"有效样本数太少"
**原因**: CSV 中太多 NaN 数据  
**解决**: 重新运行 CFD 仿真,确保更多案例成功计算

### Q2: 找不到图像文件
**原因**: 目录路径不匹配  
**解决**: 确认 `consol_cfddata/case_X_cfd_solution/` 下有三个 PNG 文件

### Q3: 预测结果不准确
**原因**: 
- 训练数据量不足 (<100 个案例)
- 训练轮次不够
**解决**: 
- 增加 CFD 仿真案例数量
- 修改 `cnnstep2.py` 中的 `num_epochs=100`

### Q4: GPU 内存不足
**解决**: 修改 `cnnstep2.py`,减小 batch_size:
```python
'train': DataLoader(train_ds, batch_size=4, ...)  # 从 8 改为 4
```

---

## 🎯 关键参数说明

### 物理参数 (4 维输入)
| 参数 | 含义 | 范围 |
|------|------|------|
| Tt | 横向间距系数 | 0.50 - 1.20 |
| Ts | 纵向间距系数 | 0.50 - 1.50 |
| Tad | 交错位移系数 | 0.00 - 1.00 |
| Tb | 翼型厚度系数 | 0.08 - 0.15 |

### 预测目标 (2 维输出)
| 参数 | 含义 | 单位 |
|------|------|------|
| Nu | 努塞尔数 (换热强度) | 无量纲 |
| f | 摩擦系数 (流动阻力) | 无量纲 |

---

## 💡 优化建议

1. **数据质量优先**: 确保至少有 **100+ 成功案例**
2. **调整学习率**: 如果 Loss 不收敛,尝试 `lr=0.0001`
3. **增加 Epoch**: 小数据集可以训练更多轮次 (100-200)
4. **数据增强**: 可以对图像进行随机旋转、翻转等增强

---

*最后更新: 2026-04-16*