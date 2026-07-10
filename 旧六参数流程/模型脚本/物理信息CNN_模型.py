#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""PI-CNN-CBAM: Physics-Informed CNN with CBAM attention for Nu/f prediction.

Architecture (based on cnnstep1.py GAP variant + auxiliary field head):
  - 3 parallel CNN branches (velocity / pressure / temperature PNGs) with CBAM
  - GAP(1x1) anti-overfitting pooling
  - Parameter MLP for 6 geometry parameters
  - Concat fusion -> dual-head output:
      Primary head:  Nu, f  (scalar performance metrics)
      Auxiliary head: T(x,y) 64x64 temperature field  (training only)
  - Physics constraint: Laplacian(T) ~ 0 in air domain (steady-state heat eq.)

During inference the field head is discarded; only Nu/f head is used.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


# ============================================================
#  CBAM attention modules (same API as cnn_model_definition.py)
# ============================================================

class ChannelAttention(nn.Module):
    def __init__(self, in_planes, ratio=16):
        super().__init__()
        self.avg_pool = nn.AdaptiveAvgPool2d(1)
        self.max_pool = nn.AdaptiveMaxPool2d(1)
        mid = max(in_planes // ratio, 1)
        self.fc = nn.Sequential(
            nn.Conv2d(in_planes, mid, 1, bias=False),
            nn.ReLU(),
            nn.Conv2d(mid, in_planes, 1, bias=False),
        )
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        out = self.sigmoid(self.fc(self.avg_pool(x)) + self.fc(self.max_pool(x)))
        return out


class SpatialAttention(nn.Module):
    def __init__(self, kernel_size=7):
        super().__init__()
        self.conv = nn.Conv2d(2, 1, kernel_size, padding=kernel_size // 2, bias=False)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        avg_out = torch.mean(x, dim=1, keepdim=True)
        max_out, _ = torch.max(x, dim=1, keepdim=True)
        return self.sigmoid(self.conv(torch.cat([avg_out, max_out], dim=1)))


class CBAM(nn.Module):
    def __init__(self, in_planes, ratio=16, kernel_size=7):
        super().__init__()
        self.channel_attention = ChannelAttention(in_planes, ratio)
        self.spatial_attention = SpatialAttention(kernel_size)

    def forward(self, x):
        x = x * self.channel_attention(x)
        x = x * self.spatial_attention(x)
        return x


# ============================================================
#  Auxiliary Field Decoder Head
#  fused_feat (B, fused_dim) -> T_hat (B, 1, 64, 64)
# ============================================================

class FieldHead(nn.Module):
    """Lightweight decoder that reconstructs a 64x64 temperature field
    from the fused feature vector, providing a physics-constraint pathway."""

    def __init__(self, fused_dim=896, base_ch=256):
        super().__init__()
        # Project to small spatial feature map: (B, base_ch, 4, 4)
        self.project = nn.Sequential(
            nn.Linear(fused_dim, base_ch * 4 * 4),
            nn.Unflatten(1, (base_ch, 4, 4)),
            nn.BatchNorm2d(base_ch),
            nn.GELU(),
        )
        # Upsample blocks: 4->8->16->32->64
        self.up1 = self._up_block(base_ch, base_ch // 2)       # 256->128
        self.up2 = self._up_block(base_ch // 2, base_ch // 4)   # 128->64
        self.up3 = self._up_block(base_ch // 4, base_ch // 8)   # 64->32
        self.up4 = self._up_block(base_ch // 8, base_ch // 16)  # 32->16
        # CBAM at intermediate resolutions
        self.cbam_8 = CBAM(base_ch // 2, ratio=16)   # at 8x8, 128 ch
        self.cbam_16 = CBAM(base_ch // 4, ratio=16)   # at 16x16, 64 ch
        # Final output
        self.out_conv = nn.Conv2d(base_ch // 16, 1, kernel_size=1)

    @staticmethod
    def _up_block(in_ch, out_ch):
        return nn.Sequential(
            nn.ConvTranspose2d(in_ch, out_ch, kernel_size=4, stride=2, padding=1),
            nn.BatchNorm2d(out_ch),
            nn.GELU(),
        )

    def forward(self, fused_feat):
        x = self.project(fused_feat)          # (B, 256, 4, 4)
        x = self.up1(x)                       # (B, 128, 8, 8)
        x = self.cbam_8(x)
        x = self.up2(x)                       # (B, 64, 16, 16)
        x = self.cbam_16(x)
        x = self.up3(x)                       # (B, 32, 32, 32)
        x = self.up4(x)                       # (B, 16, 64, 64)
        return self.out_conv(x)               # (B, 1, 64, 64)


# ============================================================
#  PI-CNN-CBAM  (main model)
# ============================================================

class PICNNCBAM(nn.Module):
    """Physics-Informed CNN with CBAM for Nu/f prediction.

    Inherits the backbone structure from cnnstep1.py (GAP version),
    adds an auxiliary FieldHead for physics-constrained training.
    """

    def __init__(self, num_fields=3, num_scalars=6, output_size=2,
                 img_size=224, cbam_ratio=16):
        super().__init__()

        # ---- A. Image Feature Extractors (3 branches + CBAM + GAP) ----
        self.cnn_extractors = nn.ModuleList([
            nn.Sequential(
                # Block 1: 224 -> 112
                nn.Conv2d(3, 32, 3, padding=1),
                nn.BatchNorm2d(32), nn.ReLU(), nn.MaxPool2d(2, 2),
                # Block 2: 112 -> 56
                nn.Conv2d(32, 64, 3, padding=1),
                nn.BatchNorm2d(64), nn.ReLU(), nn.MaxPool2d(2, 2),
                # Block 3: 56 -> 28
                nn.Conv2d(64, 128, 3, padding=1),
                nn.BatchNorm2d(128), nn.ReLU(), nn.MaxPool2d(2, 2),
                # CBAM attention at 128 channels
                CBAM(128, ratio=cbam_ratio),
                # Block 4: 28 -> 28 (no spatial reduction)
                nn.Conv2d(128, 256, 3, padding=1),
                nn.BatchNorm2d(256), nn.ReLU(),
                # GAP: 28x28 -> 1x1  (anti-overfitting for small data)
                nn.AdaptiveAvgPool2d((1, 1)),
            ) for _ in range(num_fields)
        ])

        # 256 channels * 3 fields = 768
        self.img_flat_dim = 256 * num_fields

        # ---- B. Parameter MLP ----
        self.scalar_mlp = nn.Sequential(
            nn.Linear(num_scalars, 64), nn.ReLU(),
            nn.Linear(64, 128), nn.ReLU(),
        )

        # ---- C. Fused Predictor (primary Nu/f head) ----
        combined_dim = self.img_flat_dim + 128   # 768 + 128 = 896
        self.predictor = nn.Sequential(
            nn.Linear(combined_dim, 512), nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(512, 256), nn.ReLU(),
            nn.Linear(256, output_size),
        )

        # ---- D. Auxiliary Field Head (training only) ----
        self.field_head = FieldHead(fused_dim=combined_dim)

    def forward(self, images, scalars, return_field=False):
        """
        Args:
            images: (B, num_fields, 3, H, W) field contour PNGs
            scalars: (B, num_scalars) geometry parameters
            return_field: if True, also return predicted T field (B, 1, 64, 64)
        Returns:
            nu_f: (B, 2) predicted Nu and f
            field: (B, 1, 64, 64) predicted temperature field (only if return_field=True)
        """
        B = images.size(0)

        # 1. Image features
        img_feats = []
        for i in range(images.size(1)):
            feat = self.cnn_extractors[i](images[:, i])   # (B, 256, 1, 1)
            img_feats.append(feat.view(B, -1))             # (B, 256)
        combined_img = torch.cat(img_feats, dim=1)         # (B, 768)

        # 2. Parameter features
        scalar_feat = self.scalar_mlp(scalars)             # (B, 128)

        # 3. Fusion
        fused = torch.cat([combined_img, scalar_feat], dim=1)  # (B, 896)

        # 4. Primary prediction
        nu_f = self.predictor(fused)                       # (B, 2)

        if return_field or self.training:
            field = self.field_head(fused)                 # (B, 1, 64, 64)
            return nu_f, field
        return nu_f


# ============================================================
#  Physics Losses
# ============================================================

def physics_loss_laplacian(T_pred, mask):
    """Laplacian(T) ~ 0 in air domain (steady-state heat conduction).

    Uses 5-point finite-difference stencil on the interior pixels.
    Only enforces the constraint where mask == 1 (air domain).

    Args:
        T_pred: (B, 1, H, W) predicted temperature field
        mask:   (B, 1, H, W) air domain mask (1=air, 0=solid)
    """
    T = T_pred.squeeze(1)   # (B, H, W)
    lap = (T[:, 2:, 1:-1] + T[:, :-2, 1:-1]
           + T[:, 1:-1, 2:] + T[:, 1:-1, :-2]
           - 4.0 * T[:, 1:-1, 1:-1])
    m = mask.squeeze(1)[:, 1:-1, 1:-1]
    return (lap * m).pow(2).sum() / (m.sum().clamp(min=1))


def physics_loss_divergence(u_pred, v_pred, mask):
    """div(u, v) ~ 0 in air domain (incompressibility, optional)."""
    u = u_pred.squeeze(1)
    v = v_pred.squeeze(1)
    dudx = (u[:, 1:-1, 2:] - u[:, 1:-1, :-2]) / 2.0
    dvdy = (v[:, 2:, 1:-1] - v[:, :-2, 1:-1]) / 2.0
    div = dudx + dvdy
    m = mask.squeeze(1)[:, 1:-1, 1:-1]
    return (div * m).pow(2).sum() / (m.sum().clamp(min=1))
