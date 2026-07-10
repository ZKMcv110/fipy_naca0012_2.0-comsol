# COMSOL 单工况测试

本文件夹用于保存单个 COMSOL case 的调试入口和调试输出。

## 这个脚本是什么

`test_single_case.py` 不是 `mcp_comsol_demo/` 那种 COMSOL skill/MCP 自动建模演示脚本。它只是一个固定参数的单工况测试脚本，用来调用项目根目录下的：

```text
../comsol单次执行脚本.py
```

它传入一组中间值参数：

```text
Ta=0.025
Twa=0.40
Tb=0.115
Tt=0.85
Ts=1.00
Tad=0.50
```

主要用途是调试单个 COMSOL 工况能不能跑通，以及物理特征、图像和 `result.json` 是否能正常输出。

## 怎么运行

请在项目根目录运行：

```powershell
.\myenvs_fipynaca2.0\Scripts\python.exe .\旧六参数流程\单工况测试\test_single_case.py
```

脚本内部会自动回到项目根目录调用 `comsol单次执行脚本.py`。

## 输出位置

默认输出到：

```text
旧六参数流程/单工况测试/test_case_debug/
```

如果以后看到这个文件夹，可以把它理解为单工况调试产物，不是正式 500 组 COMSOL 数据集。

正式批量结果仍然在：

```text
consol_cfddata/
```

## 和 MCP/skill 自动建模 demo 的区别

- `旧六参数流程/单工况测试/`：当前项目真实 COMSOL 单工况调试。
- `mcp_comsol_demo/`：COMSOL skill/MCP 自动建模演示或实验代码。
