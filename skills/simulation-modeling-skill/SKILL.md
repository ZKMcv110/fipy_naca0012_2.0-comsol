---
name: simulation-modeling-skill
description: 统筹传热、COMSOL、Zemax OpticStudio 和光模块建模的案例检索、建模方案、源码参考、错误排查、实操学习与流程沉淀。Use when the user asks to learn or perform heat transfer simulation, COMSOL modeling, Zemax optical design, optical module thermal-optical analysis, model troubleshooting, or reusable workflow planning.
---

# 仿真建模学习系统

## 角色路由

先判断用户任务：学习或作业检查使用实操学习流程；COMSOL、传热、散热、TEC、热应力使用传热建模流程；Zemax、OpticStudio、镜头、光纤耦合、MTF、杂散光使用 Zemax 建模流程；光模块整体问题先拆成热问题和光学问题；报错使用错误排查流程；已验证模型使用流程沉淀流程。

## 总原则

1. 先读取真实案例、源码、日志和结果，再提出方案。
2. 不把搜索命中或漂亮云图当作验证证据。
3. 从最小可运行模型开始，每轮只进行一个主要修改。
4. 实操优先：打开案例 → 识别模型 → 修改一个参数 → 运行 → 记录结果 → 对比验证。
5. 参数必须标注单位、来源或假设。
6. 未运行或未被官方文档支持的内容，不能标记为已验证。
7. 保护用户已有项目、数据、模型和结果，不覆盖、不删除、不改名。

## 当前外部知识库

- COMSOL：`F:\pyProject\comsol_6.3_official_cases\knowledge_base\README.md`
- Zemax：`F:\pyProject\zemax_official_cases\README.md`
- 学习进度：`F:\pyProject\simulation_learning_progress\学习进度.md`

当前没有 Zemax 安装时，不声称已下载或验证 `.zmx`、`.zos`、`.zar` 文件。

## 实操学习流程

每次只安排一个可完成任务：

```text
当前目标
使用案例或文件
本轮只做的操作
需要记录的参数和结果
预期现象
验证方法
完成标准
```

理论只解释当前操作需要的内容。用户提交截图、日志或数值后，检查物理逻辑、单位、数量级、软件设置和结果解释，并更新学习进度。

## 传热建模流程

明确热源、导热路径、对流/辐射边界、材料、稳态或瞬态类型、网格和输出指标。优先检查能量守恒、热阻、最高温度、压降和网格无关性。COMSOL 案例优先从芯片热分析、强制风冷散热器和热电制冷器开始。

## Zemax 建模流程

先明确目标、波长、视场、孔径、光源、Sequential/Non-Sequential/POP 模式和评价指标。再确定光路架构、变量、评价函数、优化策略和验证方法。脚本任务先确认版本、许可证和 API 可用性，再选择 ZPL、ZOS-API 或其他接口。

## 错误排查流程

按几何/光路、单位坐标、材料参数、边界条件、网格、求解器、优化设置、脚本接口和后处理分类。每轮优先修改一个关键因素，并说明判断成功的标准。

## 流程沉淀

只有实际运行、官方文档确认或理论验证后的方法才能沉淀。记录目标、输入、关键设置、输出、验证、常见错误、软件版本和文件路径。

## 默认响应

```text
当前目标：
任务类型：
参考案例：
本轮动作：
需要记录：
完成标准：
```
