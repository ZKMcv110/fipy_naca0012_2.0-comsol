@echo off
cd /d "F:\pyProject\fipy_naca0012_2.0"

python "七参数_MLP_CNN流场重建\01_构建流场数据集.py" ^
  --field-dir "七参数_PDE_PINN尝试\field_data_320x96" ^
  --output "七参数_MLP_CNN流场重建\data\field_reconstruction_dataset_320x96_full.npz" ^
  --case-output-dir "七参数_MLP_CNN流场重建\data\standard_case_npz_320x96_full"

python "七参数_MLP_CNN流场重建\08_UNet高精度流场重建训练.py" ^
  --dataset "七参数_MLP_CNN流场重建\data\field_reconstruction_dataset_320x96_full.npz" ^
  --field-dir "七参数_PDE_PINN尝试\field_data_320x96" ^
  --epochs 50 ^
  --batch-size 2 ^
  --field-weights "1,5,3,2" ^
  --grad-weight 0.3 ^
  --output-dir "七参数_MLP_CNN流场重建\results\unet_mask_320x96_full_e50"
