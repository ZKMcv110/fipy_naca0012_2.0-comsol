# RTK - Rust Token Killer（Codex CLI）

**用途**：为常见 shell 命令提供更紧凑的输出，减少 Codex 读取终端结果时的上下文消耗。

## 规则

运行 shell 命令时，优先使用 `rtk` 前缀。

示例：

```bash
rtk git status
rtk cargo test
rtk npm run build
rtk pytest -q
```

## 元命令

```bash
rtk gain            # 查看 token 节省统计
rtk gain --history  # 查看近期命令节省历史
rtk proxy <cmd>     # 原样运行命令，不过滤输出
```

## 验证

```bash
rtk --version
rtk gain
where rtk
```
