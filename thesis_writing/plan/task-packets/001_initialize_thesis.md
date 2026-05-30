# Task Packet

- Scope：初始化大论文写作工程，将现有期刊式草稿转化为可分章推进的学位论文结构。
- Files to read：`academic_pre_review_committee_loaded.md`、`README.md`、`research-writing-skill-main/SKILL.md`
- Files allowed to edit：`thesis_writing/plan/`、`thesis_writing/chapters/`、`thesis_writing/refs/`、`thesis_writing/figures/`、`thesis_writing/tables/`
- Required skills：using-research-writing、paper-orchestration、writing-chapters
- Evidence/data inputs：现有草稿、项目代码结构、结果目录
- Required artifacts：项目概览、论文大纲、进度追踪、章节架构、任务包
- Rejection checks：不能直接生成整篇正文；不能捏造学校模板；不能把未经核对的数据写成最终结论
- Validation commands：`Get-ChildItem -Force plan, chapters, refs, figures, tables`

## Chapter-writing additions

- Target chapter file and exclusive owner：本任务不写正文，仅初始化结构。
- Required argument chain：研究背景 -> 现有草稿基础 -> 学位论文扩展需求 -> 分章架构。
- Minimum prose length：不适用。
- Required sources and data artifacts：现有草稿和项目 README。
- Prohibited structure：不输出“万能论文模板”作为最终正文。
- Required handoff format：状态、文件路径、未解决的信息缺口、下一步建议。
