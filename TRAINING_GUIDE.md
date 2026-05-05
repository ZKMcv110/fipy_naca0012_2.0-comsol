# 500案例CNN训练说明

## 📊 当前训练配置

- **数据集**: 500个完整CFD案例
- **数据划分**:
  - 训练集: 375个案例 (75%)
  - 验证集: 75个案例 (15%)
  - 测试集: 50个案例 (10%)
- **训练轮次**: 50 epochs
- **Batch Size**: 16
- **学习率**: 0.0005
- **设备**: CUDA (GPU加速)

## ⏱️ 预计训练时间

根据硬件配置不同,预计需要:
- **高性能GPU** (RTX 3090/4090): 约 15-30 分钟
- **中端GPU** (RTX 2060/3060): 约 30-60 分钟
- **CPU模式**: 约 2-4 小时

## 📈 训练监控

训练过程中会实时显示:
```
Epoch [1/50] Train Loss: 1.253146 | Val Loss: 0.696206
Epoch [2/50] Train Loss: xxxxxxxx | Val Loss: xxxxxxxx
...
```

**正常现象:**
- ✅ Train Loss 逐渐下降
- ✅ Val Loss 波动但总体趋势下降
- ⚠️ 如果 Val Loss 持续上升,可能是过拟合

## 📁 输出文件

训练完成后会在 `ai_cnn_model_results/` 生成:

| 文件 | 说明 |
|------|------|
| `cfd_cnn_model.pth` | 最终模型权重 (~30MB) |
| `best_model.pth` | 验证集最佳模型 |
| `dataset_stats.json` | 数据统计信息 |
| `metrics.json` | 评估指标 |
| `loss_curve.png` | Loss收敛曲线图 |
| `final_prediction.png` | 预测vs真实值散点图 |

## ⚠️ 注意事项

1. **不要中断训练**: 训练过程中请勿关闭终端
2. **GPU内存**: 如遇OOM错误,可减小batch_size到8
3. **后台运行**: 如需长时间训练,建议使用:
   ```bash
   # Windows PowerShell
   Start-Process python -ArgumentList "cnnstep2.py" -NoNewWindow
   
   # 或使用 nohup (Linux)
   nohup python cnnstep2.py > training.log 2>&1 &
   ```

## 🔍 查看训练进度

在另一个终端窗口运行:
```bash
# 查看最后10行输出
Get-Content ai_cnn_model_results\training.log -Tail 10

# 或实时监控
Get-Content ai_cnn_model_results\training.log -Wait -Tail 20
```

## ✅ 训练完成标志

看到以下输出表示训练成功:
```
🏆 模型权重及所有统计量已保存完毕。训练流程结束。
```

## 🚀 下一步

训练完成后可以:

1. **查看评估结果**:
   ```bash
   cat ai_cnn_model_results/metrics.json
   ```

2. **测试预测功能**:
   ```bash
   python cnnstep3.py
   ```

3. **可视化结果**:
   - 打开 `ai_cnn_model_results/loss_curve.png` 查看训练过程
   - 打开 `ai_cnn_model_results/final_prediction.png` 查看预测效果

---
*训练开始时间: 2026-04-16*