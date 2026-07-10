#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))


"""
CNN+CBAM+GAP 模型预测脚本
使用训练好的最佳模型对新的 CFD 算例进行 Nu/f 预测

用法：
  python CNN_CBAM_预测.py --case-id 42
  python CNN_CBAM_预测.py --all-test       # 预测全部测试集并打印结果
"""

import argparse
import json
import os
import sys

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(errors="replace")

import numpy as np
import pandas as pd
import torch
from PIL import Image

from CNN_CBAM_GAP_模型定义 import CFDFieldToPerformanceCNN

PARAM_COLS = ["Ta", "Twa", "Tb", "Ts", "Tt", "Tad"]
FIELD_PNGS = ["velocity_magnitude.png", "pressure.png", "temperature.png"]


def load_model(model_path, device, num_scalars=6):
    """加载训练好的模型权重"""
    model = CFDFieldToPerformanceCNN(num_fields=3, num_scalars=num_scalars, output_size=2)
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.to(device)
    model.eval()
    return model


def load_stats(stats_path):
    """加载归一化统计量"""
    with open(stats_path, "r", encoding="utf-8") as f:
        return json.load(f)


def prepare_input(case_id, data_dir, df, stats, img_size=224):
    """为一个 case 准备模型输入"""
    row = df.loc[df["case_id"] == case_id].iloc[0]

    # 图像
    case_dir = os.path.join(data_dir, f"case_{case_id}_cfd_solution")
    imgs = []
    for name in FIELD_PNGS:
        img = Image.open(os.path.join(case_dir, name)).convert("RGB")
        img = img.resize((img_size, img_size), Image.BILINEAR)
        arr = np.asarray(img, dtype=np.float32) / 255.0
        arr = (arr - 0.5) / 0.5
        imgs.append(arr)
    images = torch.tensor(np.stack(imgs)).permute(0, 3, 1, 2).unsqueeze(0)  # (1, 3, 3, H, W)

    # 参数
    ps = stats["param"]
    params = []
    for col in PARAM_COLS:
        m = ps[f"{col}_mean"]
        s = ps[f"{col}_std"]
        params.append((float(row[col]) - m) / (s + 1e-8))
    scalars = torch.tensor([params], dtype=torch.float32)

    return images, scalars, row


def predict_one(model, images, scalars, stats, device):
    """预测单个 case，返回反归一化后的 Nu 和 f"""
    with torch.no_grad():
        out = model(images.to(device), scalars.to(device)).cpu().numpy()[0]

    ts = stats["target"]
    nu = out[0] * (ts["nu_std"] + 1e-8) + ts["nu_mean"]
    f  = out[1] * (ts["f_std"]  + 1e-8) + ts["f_mean"]
    return nu, f


def main():
    parser = argparse.ArgumentParser(description="使用 CNN+CBAM+GAP 模型预测 Nu/f")
    parser.add_argument("--model-path", default=os.path.join("cnn_cbam_gap_results", "cnn_cbam_gap_best.pth"))
    parser.add_argument("--stats-path", default=os.path.join("cnn_cbam_gap_results", "dataset_stats.json"))
    parser.add_argument("--labels",     default=os.path.join("consol_cfddata", "labels.csv"))
    parser.add_argument("--data-dir",   default="consol_cfddata")
    parser.add_argument("--split-file", default=os.path.join("ai_cnn_model_results", "dataset_split.csv"))
    parser.add_argument("--img-size",   type=int, default=224)

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--case-id", type=int, help="预测指定 case")
    group.add_argument("--all-test", action="store_true", help="预测全部测试集")
    group.add_argument("--all", action="store_true", help="预测全部 500 个 case")

    args = parser.parse_args()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # 加载模型和统计量
    stats = load_stats(args.stats_path)
    model = load_model(args.model_path, device)
    df = pd.read_csv(args.labels)
    df["case_id"] = df["case_id"].astype(int)

    if args.case_id:
        # 单个 case 预测
        imgs, sca, row = prepare_input(args.case_id, args.data_dir, df, stats, args.img_size)
        nu, f = predict_one(model, imgs, sca, stats, device)
        eta = nu / max(f, 1e-12) ** (1.0 / 3)
        print(f"\n===== Case {args.case_id} 预测结果 =====")
        print(f"  Nu  = {nu:.4f}   (CFD: {float(row['Nu']):.4f})")
        print(f"  f   = {f:.6f}   (CFD: {float(row['f']):.6f})")
        print(f"  eta = {eta:.4f}")

    else:
        # 批量预测
        if args.all_test and os.path.exists(args.split_file):
            split_df = pd.read_csv(args.split_file)
            case_ids = split_df.loc[split_df["split"] == "test", "case_id"].astype(int).tolist()
            print(f"[INFO] 预测测试集: {len(case_ids)} 个 case")
        else:
            case_ids = df["case_id"].tolist()
            print(f"[INFO] 预测全部: {len(case_ids)} 个 case")

        results = []
        for cid in case_ids:
            try:
                imgs, sca, row = prepare_input(cid, args.data_dir, df, stats, args.img_size)
                nu, f = predict_one(model, imgs, sca, stats, device)
                true_nu = float(row["Nu"])
                true_f = float(row["f"])
                results.append({
                    "case_id": cid,
                    "true_Nu": true_nu, "pred_Nu": nu, "err_Nu": nu - true_nu,
                    "true_f": true_f,   "pred_f": f,   "err_f": f - true_f,
                })
            except Exception as e:
                print(f"[WARN] case {cid} 失败: {e}")

        res_df = pd.DataFrame(results)
        print(f"\n{'case_id':>8} {'true_Nu':>10} {'pred_Nu':>10} {'err_Nu':>10} "
              f"{'true_f':>12} {'pred_f':>12} {'err_f':>12}")
        print("-" * 80)
        for _, r in res_df.iterrows():
            print(f"{int(r.case_id):>8} {r.true_Nu:>10.4f} {r.pred_Nu:>10.4f} {r.err_Nu:>10.4f} "
                  f"{r.true_f:>12.6f} {r.pred_f:>12.6f} {r.err_f:>12.6f}")

        # 汇总
        from sklearn.metrics import r2_score, mean_absolute_error
        print(f"\n===== 汇总 =====")
        print(f"  Nu: R2={r2_score(res_df.true_Nu, res_df.pred_Nu):.4f}  "
              f"MAE={mean_absolute_error(res_df.true_Nu, res_df.pred_Nu):.4f}")
        print(f"  f:  R2={r2_score(res_df.true_f, res_df.pred_f):.4f}  "
              f"MAE={mean_absolute_error(res_df.true_f, res_df.pred_f):.6f}")


if __name__ == "__main__":
    main()
