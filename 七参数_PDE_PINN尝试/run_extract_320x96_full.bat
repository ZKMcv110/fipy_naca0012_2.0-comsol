@echo off
cd /d "F:\pyProject\fipy_naca0012_2.0"
set PYTHON=F:\pyProject\fipy_naca0012_2.0\myenvs_fipynaca2.0\Scripts\python.exe
set SCRIPT=F:\pyProject\fipy_naca0012_2.0\七参数_PDE_PINN尝试\01_导出全场数据.py
set OUTDIR=F:\pyProject\fipy_naca0012_2.0\七参数_PDE_PINN尝试\field_data_320x96

echo [%date% %time%] START high-resolution field export 320x96 > "F:\pyProject\fipy_naca0012_2.0\七参数_PDE_PINN尝试\extract_320x96_full.log"
"%PYTHON%" "%SCRIPT%" --nx 320 --ny 96 --output-dir "%OUTDIR%" >> "F:\pyProject\fipy_naca0012_2.0\七参数_PDE_PINN尝试\extract_320x96_full.log" 2>> "F:\pyProject\fipy_naca0012_2.0\七参数_PDE_PINN尝试\extract_320x96_full.err"
echo [%date% %time%] DONE >> "F:\pyProject\fipy_naca0012_2.0\七参数_PDE_PINN尝试\extract_320x96_full.log"
