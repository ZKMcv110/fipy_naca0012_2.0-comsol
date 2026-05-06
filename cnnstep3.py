#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Predict Nu and f for one CFD case using the trained CNN model."""

import argparse
import json
import os

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from PIL import Image
from torchvision import transforms

from cnn_model_definition import CFDFieldToPerformanceCNN


PARAM_COLS = ['Ta', 'Twa', 'Tb', 'Ts', 'Tt', 'Tad']
MODEL_DIR = 'ai_cnn_model_results'
DATA_DIR = 'consol_cfddata'
LABELS_CSV = os.path.join(DATA_DIR, 'labels.csv')
REQUIRED_IMAGES = {
    'velocity': 'velocity_magnitude.png',
    'pressure': 'pressure.png',
    'temperature': 'temperature.png',
}


def load_trained_model(model_path, device):
    model = CFDFieldToPerformanceCNN(num_fields=3, num_scalars=len(PARAM_COLS), output_size=2)
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found: {model_path}")

    model.load_state_dict(torch.load(model_path, map_location=device), strict=False)
    model.to(device)
    model.eval()
    return model


def preprocess_field_images(case_dir, device):
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5]),
    ])

    tensors = []
    paths = {}
    for field_name, file_name in REQUIRED_IMAGES.items():
        path = os.path.join(case_dir, file_name)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Missing {field_name} image: {path}")
        paths[field_name] = path
        tensors.append(transform(Image.open(path).convert('RGB')))

    images = torch.stack(tensors, dim=0).unsqueeze(0).to(device)
    return images, paths


def load_case_from_labels(case_id):
    if not os.path.exists(LABELS_CSV):
        raise FileNotFoundError(f"Missing {LABELS_CSV}. Run rebuild_labels_from_results.py first.")

    df = pd.read_csv(LABELS_CSV)
    case_row = df[df['case_id'].astype(int) == int(case_id)]
    if len(case_row) == 0:
        raise ValueError(f"case_id={case_id} was not found in {LABELS_CSV}")

    row = case_row.iloc[0]
    scalars = [float(row[name]) for name in PARAM_COLS]
    true_nu = float(row['Nu']) if 'Nu' in row else None
    true_f = float(row['f']) if 'f' in row else None
    return scalars, true_nu, true_f


def get_manual_scalars(args):
    values = [args.Ta, args.Twa, args.Tb, args.Ts, args.Tt, args.Tad]
    if any(value is None for value in values):
        missing = [name for name, value in zip(PARAM_COLS, values) if value is None]
        raise ValueError(f"Manual prediction requires all 6 parameters. Missing: {missing}")
    return [float(value) for value in values]


def predict_performance(model, images, scalars, stats, device):
    p_stats = stats['param']
    norm_params = [
        (scalars[i] - p_stats[f'{name}_mean']) / (p_stats[f'{name}_std'] + 1e-8)
        for i, name in enumerate(PARAM_COLS)
    ]
    params_tensor = torch.tensor([norm_params], dtype=torch.float32).to(device)

    with torch.no_grad():
        norm_nu, norm_f = model(images, params_tensor)[0].cpu().numpy()

    t_stats = stats['target']
    real_nu = norm_nu * (t_stats['nu_std'] + 1e-8) + t_stats['nu_mean']
    real_f = norm_f * (t_stats['f_std'] + 1e-8) + t_stats['f_mean']
    return float(real_nu), float(real_f)


def print_parameter_range_check(scalars, stats):
    print("\nParameter range check based on training statistics:")
    for name, value in zip(PARAM_COLS, scalars):
        mean = stats['param'][f'{name}_mean']
        std = stats['param'][f'{name}_std']
        lower = mean - 3 * std
        upper = mean + 3 * std
        status = "OK" if lower <= value <= upper else "OUT_OF_RANGE"
        print(f"  {name}: {value:.6f} ({lower:.6f} to {upper:.6f}) {status}")


def visualize_prediction(image_paths, nu_pred, f_pred, save_path):
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    fields = [
        ('velocity', 'Velocity Field'),
        ('pressure', 'Pressure Field'),
        ('temperature', 'Temperature Field'),
    ]

    for ax, (field_name, title) in zip(axes, fields):
        ax.imshow(Image.open(image_paths[field_name]))
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.axis('off')

    eta = nu_pred / (f_pred ** (1.0 / 3.0)) if f_pred > 0 else 0
    fig.suptitle(
        f"Multimodal CNN Prediction\nNu: {nu_pred:.4f} | f: {f_pred:.6f} | Performance (eta): {eta:.4f}",
        fontsize=18,
        fontweight='heavy',
        color='#800000',
        y=1.05,
    )
    plt.tight_layout()
    plt.savefig(save_path, dpi=200, bbox_inches='tight')
    plt.close()


def main():
    parser = argparse.ArgumentParser(description='Predict Nu/f for a CFD case with the trained CNN.')
    parser.add_argument('--case_id', type=int, default=1, help='Case ID to predict. Default: 1.')
    parser.add_argument('--manual', action='store_true', help='Use manually supplied parameters instead of labels.csv.')
    parser.add_argument('--Ta', type=float, default=None)
    parser.add_argument('--Twa', type=float, default=None)
    parser.add_argument('--Tb', type=float, default=None)
    parser.add_argument('--Ts', type=float, default=None)
    parser.add_argument('--Tt', type=float, default=None)
    parser.add_argument('--Tad', type=float, default=None)
    args = parser.parse_args()

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model_path = os.path.join(MODEL_DIR, 'cfd_cnn_model.pth')
    stats_path = os.path.join(MODEL_DIR, 'dataset_stats.json')

    if not os.path.exists(stats_path):
        raise FileNotFoundError(f"Missing {stats_path}. Run cnnstep2.py first.")

    with open(stats_path, 'r', encoding='utf-8') as f:
        stats = json.load(f)

    model = load_trained_model(model_path, device)

    if args.manual:
        scalars = get_manual_scalars(args)
        true_nu, true_f = None, None
    else:
        scalars, true_nu, true_f = load_case_from_labels(args.case_id)

    case_dir = os.path.join(DATA_DIR, f'case_{args.case_id}_cfd_solution')
    images, image_paths = preprocess_field_images(case_dir, device)
    print_parameter_range_check(scalars, stats)

    nu_pred, f_pred = predict_performance(model, images, scalars, stats, device)

    print("\nPrediction:")
    print(f"  case_id: {args.case_id}")
    print(f"  parameters ({', '.join(PARAM_COLS)}): {scalars}")
    if true_nu is not None and true_f is not None:
        print(f"  CFD true Nu: {true_nu:.6f}")
        print(f"  CFD true f : {true_f:.6f}")
    print(f"  CNN predicted Nu: {nu_pred:.6f}")
    print(f"  CNN predicted f : {f_pred:.6f}")
    if f_pred > 0:
        print(f"  eta = Nu/(f^(1/3)): {nu_pred / (f_pred ** (1.0 / 3.0)):.6f}")

    os.makedirs(MODEL_DIR, exist_ok=True)
    vis_path = os.path.join(MODEL_DIR, 'current_prediction_visual.png')
    visualize_prediction(image_paths, nu_pred, f_pred, vis_path)
    print(f"Saved visualization: {vis_path}")


if __name__ == '__main__':
    main()
