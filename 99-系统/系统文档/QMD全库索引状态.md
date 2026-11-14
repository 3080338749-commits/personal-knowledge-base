---
type: system
status: complete
updated: 2026-11-14
---
# QMD全库索引状态

本页为本次首次索引自动生成的状态，不是学习或掌握记录。只在进度变化时更新。

- 检查时间：2026-10-17T13:43:15+08:00（北京时间）
- 状态：complete
- 主集合工作笔记：62
- 完整向量已完成：62
- 剩余：0
- 当前向量分块：246
- 科研11篇已完成，四条中文语义查询已验收；全部笔记关键词检索可用。

全库首次向量索引完成；无需重新下载模型。

索引可断点续建；原笔记和评分不受中断影响。完成记录以本页及验收证据/QMD全库索引运行状态.json为准。

## 2026-11-14 本机配置修正与重建

修正 `%USERPROFILE%/.config/qmd/personal-kb.yml`：补回排除规则（排除备份、09-系统配置、系统文档/私密、笔记模板、AGENTS/CLAUDE、.git）并为 `fiber-research` 设置 `includeByDefault: false`。运行 `update` 与 `cleanup` 后：`personal-kb` 137 篇、`fiber-research` 22 篇，索引大小 4.5 MB，向量 0（未下载模型）。
