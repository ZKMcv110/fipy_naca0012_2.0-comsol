@echo off
cd /d "F:\pyProject\fipy_naca0012_2.0\七参数_PDE_PINN尝试"
"F:\pyProject\fipy_naca0012_2.0\myenvs_fipynaca2.0\Scripts\python.exe" "01_导出全场数据.py" > extract_full_log.txt 2> extract_full_err.txt
echo DONE >> extract_full_log.txt
