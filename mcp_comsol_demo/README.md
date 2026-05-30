# COMSOL MCP Mini Demo

这个文件夹是一个和当前项目思路相近、但不依赖你论文数据的 MCP 示例。

目标流程：

```text
几何参数 -> COMSOL MCP -> 参数化二维通道/管束示例 -> 流动与传热设置 -> 求解/导出 -> result.json
```

它不是你的正式 `fipy_naca0012_2.0` 数据流程，只是用来演示 `comsol-multiphysics` MCP 怎么被调用。

## 先看调用计划

不会启动 COMSOL：

```powershell
python mcp_comsol_demo\mini_heat_exchanger_mcp_demo.py --dry-run
```

## 检查 MCP 是否能连上

只调用 MCP 的 `comsol_status` 和 `docs_get`，不会求解：

```powershell
python mcp_comsol_demo\mini_heat_exchanger_mcp_demo.py --check-mcp
```

## 真正执行建模

会尝试启动 COMSOL，然后创建一个示例模型。第一次可能很慢：

```powershell
python mcp_comsol_demo\mini_heat_exchanger_mcp_demo.py --execute --start-comsol
```

如果你已经用 COMSOL Server 开了端口，例如 `2036`，可以改为连接已有服务：

```powershell
python mcp_comsol_demo\mini_heat_exchanger_mcp_demo.py --execute --connect-port 2036
```

## 这个例子和你项目的对应关系

| 你的项目 | 这个 MCP demo |
|---|---|
| `consol500组参数.py` 批量参数 | `DEMO_PARAMETERS` 里的一组几何/工况参数 |
| COMSOL 建模脚本 | MCP 工具调用序列 |
| `result.json` | `demo_outputs/result_plan.json` / 真跑后可扩展为结果 JSON |
| 速度、温度、压力云图 | `results_export_image` 工具预留导出步骤 |
| `labels.csv` | 可由多个 demo run 的 result JSON 重建 |

## 注意

这个第三方 COMSOL MCP 目前更适合做“自动化建模接口演示”。正式论文数据还是建议继续使用你已有的、可重复的 COMSOL 脚本流程。
