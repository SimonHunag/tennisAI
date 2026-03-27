# TennisAI - 网球动作视频分析

TennisAI 目前是一个轻量级的训练分析工作台，用来整理网球训练视频、提取关键帧，并沉淀每次训练的分析报告。

## 当前已实现

- 视频按训练会话归档
- 使用 `ffmpeg` 提取固定间隔的视频帧
- 自动创建分析会话目录、Markdown 报告和 JSON 元数据
- 使用统一模板记录动作问题、改进建议和下次训练重点
- 支持从 Markdown 报告回写结构化 JSON
- 基于会话元数据生成训练汇总报告，以及适合图表或前端消费的 JSON、CSV 数据
- 提供一个纯静态本地 dashboard 页面，用于查看训练概览和会话列表
- 提供姿态分析脚本骨架，用于从关键点数据生成问题与调整建议
- 提供后端流水线入口脚本，用于串联姿态提取、自动分析和汇总重建
- Dashboard 可展示自动分析结果，包括规则命中的问题标签、关键指标和建议重点
- 支持对单个视频中的多个发球练习片段进行自动识别与逐段分析
- 支持把多片段发球结果整理成中文总结报告
- 提供独立的发球报告前端页面，用于查看单条视频的分析结果
- 支持按球员和动作类型分层归档，适合团队长期追踪
- 支持对两次发球报告做结构化对比，方便看同一球员的前后变化

## 规划中

- 自动关键帧筛选
- 骨架标注与动作检测
- 与参考动作做叠加对比
- 长期训练进度统计

## 项目结构

```text
tennisAI/
├── analysis/           # Markdown 报告、元数据模板和训练汇总
├── backend/            # 后台分析逻辑说明
├── dashboard/          # 纯静态本地可视化页面
├── frames/             # 每次训练提取出的关键帧
├── reference/          # 参考视频或标准动作素材
├── scripts/            # 自动化脚本
├── TEAM_WORKFLOW.md    # 团队目录规范和长期追踪建议
└── videos/             # 每次训练的视频目录
```

推荐分层：

```text
videos/<athlete_id>/<action_type>/<session_id>/<session_id>.mp4
frames/<athlete_id>/<action_type>/<session_id>/
analysis/<athlete_id>/<action_type>/<session_id>.md
analysis/<athlete_id>/<action_type>/<session_id>.json
```

## 推荐工作流

1. 使用 `scripts/new-analysis-session.ps1` 创建一次新的训练会话。
也可以直接用 `scripts/start-analysis.ps1` 从原始视频一键开始分析。
2. 把原始视频放入对应的 `videos/<session-id>/` 目录。
3. 使用 `scripts/extract-frames.ps1` 把关键帧提取到 `frames/<session-id>/`。
4. 打开 `analysis/<session-id>.md`，结合 `reference/` 中的标准动作做人工分析，并填写结构化数据区块。
5. 运行 `scripts/sync-report-to-json.ps1`，把 Markdown 中的关键信息同步到 JSON。
6. 定期运行 `scripts/build-training-summary.ps1`，生成可筛选的训练汇总视图，以及 dashboard JSON 和 CSV 数据文件。
7. 打开 `dashboard/index.html`，查看本地可视化页面。
8. 生成姿态关键点后，运行 `scripts/analyze-pose.py`，输出自动分析结果。
9. 如果是包含多个发球片段的训练视频，可在批量分析后运行 `scripts/generate-serve-report.py` 生成中文总结报告。
10. 打开 `dashboard/serve-report.html`，查看单条发球视频的前端报告页面。

## 依赖

- PowerShell 5.1+ 或 PowerShell 7+
- `ffmpeg`
- 可选：`python`，用于快速启动本地静态服务器

## 快速开始

查看 `GETTING_STARTED.md`。
