# TennisAI 快速入门

## 1. 检查环境

确认本机已安装 `ffmpeg`，并且 PowerShell 可以直接执行：

```powershell
ffmpeg -version
```

## 2. 创建新的分析会话

建议每次训练都使用独立会话，命名保持简短清晰，例如 `serve-side-view`。如果是团队使用，建议同时传入球员信息，让文件自动落到分层目录里。

```powershell
./scripts/new-analysis-session.ps1 -SessionName "serve-side-view" -ActionType serve -AthleteName "张三" -AthleteId "zhang-san"
```

执行后会生成：

- `videos/zhang-san/serve/2026-03-25-serve-side-view/`
- `frames/zhang-san/serve/2026-03-25-serve-side-view/`
- `analysis/zhang-san/serve/2026-03-25-serve-side-view.md`
- `analysis/zhang-san/serve/2026-03-25-serve-side-view.json`

## 3. 放入训练视频

把原始视频放进新建好的 `videos/<athlete_id>/<action_type>/<session-id>/` 目录，建议文件名和会话名保持一致，例如：

```text
videos/zhang-san/serve/2026-03-25-serve-side-view/2026-03-25-serve-side-view.mp4
```

如果你想直接一步开始分析，也可以跳过手工建目录，直接运行统一入口脚本：

```powershell
./scripts/start-analysis.ps1 -InputVideo "D:\videos\serve-1.mp4" -SessionName "basket-serve" -ActionType serve -AthleteName "Simon" -AthleteId "simon"
```

这个脚本会自动建目录、复制视频、跑分析并重建总览。

## 4. 提取关键帧

```powershell
./scripts/extract-frames.ps1 `
  -InputVideo "videos/2026-03-25-serve-side-view/2026-03-25-serve-side-view.mp4" `
  -OutputDir "frames/2026-03-25-serve-side-view" `
  -Interval 1
```

如果目标目录里已经有旧图片，追加 `-Force` 即可覆盖同名前缀的输出：

```powershell
./scripts/extract-frames.ps1 `
  -InputVideo "videos/2026-03-25-serve-side-view/2026-03-25-serve-side-view.mp4" `
  -OutputDir "frames/2026-03-25-serve-side-view" `
  -Interval 1 `
  -Force
```

## 5. 完成动作分析

打开 `analysis/<session-id>.md`，围绕以下内容记录观察结果：

- 准备姿势
- 引拍轨迹
- 击球瞬间
- 随挥完整性
- 与参考动作的差异
- 下次训练重点

报告中的“结构化数据”区块是 JSON 的主要来源。填完报告后执行：

```powershell
./scripts/sync-report-to-json.ps1 -ReportPath "analysis/2026-03-25-serve-side-view.md"
```

脚本会自动更新同名的 `analysis/<session-id>.json`。

推荐至少补充这些字段：

- `athlete`
- `coach`
- `camera_view`
- `focus_points`
- `issues`
- `next_steps`
- `metrics.consistency_score`
- `metrics.balance_score`
- `metrics.timing_score`

## 6. 生成训练汇总

当 `analysis/` 下积累了多次训练的 JSON 后，可以生成一个总览文档：

```powershell
./scripts/build-training-summary.ps1
```

默认会输出到：

```text
analysis/training-summary.md
analysis/training-summary.json
analysis/training-summary.csv
```

其中：

- `training-summary.md` 适合人工阅读
- `training-summary.json` 适合 Web 页面、图表组件或 API 直接消费
- `training-summary.csv` 适合导入 Excel、Sheets 或 BI 工具

这个汇总文件适合回顾最近一段时间练了哪些动作、主要问题集中在哪里、评分是否有提升。

也可以按动作类型或日期范围筛选，例如：

```powershell
./scripts/build-training-summary.ps1 -ActionType serve,forehand -DateFrom 2026-03-01 -DateTo 2026-03-31
```

也可以按球员筛选：

```powershell
./scripts/build-training-summary.ps1 -Athlete zhang-san,li-si -ActionType serve,forehand_slice
```

## 7. 打开本地 Dashboard

项目自带一个纯静态页面：

```text
dashboard/index.html
```

推荐先启动一个本地静态服务器，再打开这个页面。最简单的方式之一是：

```powershell
cd dashboard
python -m http.server 8000
```

然后在浏览器中访问：

```text
http://localhost:8000
```

页面会默认尝试读取：

```text
../analysis/training-summary.json
```

如果浏览器因为 `file://` 或跨源限制无法自动读取，也可以直接点击页面里的 `Choose JSON`，手动选择 `analysis/training-summary.json`。

当会话对应的 `analysis/<session-id>-analysis.json` 存在时，dashboard 会额外展示：

- 自动命中的问题标签
- 自动分析给出的下次重点
- 自动提取的关键指标摘要

## 8. 生成自动分析结果

当你已经有姿态关键点 JSON 后，可以直接生成第一版自动分析结果：

如果你还没有姿态关键点，可以先从视频生成姿态 JSON：

```powershell
python ./scripts/extract-pose.py --input-video "videos/2026-03-25-serve-side-view/2026-03-25-serve-side-view.mp4" --provider stub --action-type serve
```

如果本机已经安装了 `mediapipe`，也可以改成真实姿态提取：

```powershell
python ./scripts/extract-pose.py --input-video "videos/2026-03-25-serve-side-view/2026-03-25-serve-side-view.mp4" --provider mediapipe --model-asset-path "assets/models/pose_landmarker.task" --action-type serve
```

模型文件目录说明见：

```text
assets/models/README.md
```

然后再运行自动分析：

```powershell
python ./scripts/analyze-pose.py --input analysis/2026-03-25-serve-side-view-pose.json
```

如果你想一次跑完整条后台链路，也可以直接使用：

```powershell
python ./scripts/run-analysis-pipeline.py --input-video "videos/2026-03-25-serve-side-view/2026-03-25-serve-side-view.mp4" --provider stub --action-type serve
```

如果一个视频里包含多个发球练习片段，可以开启分段识别：

```powershell
python ./scripts/run-analysis-pipeline.py --input-video "videos/2026-03-25-serve-side-view/2026-03-25-serve-side-view.mp4" --provider mediapipe --model-asset-path "assets/models/pose_landmarker.task" --action-type serve --detect-serve-segments
```

这时会额外生成：

```text
analysis/<video-name>-segments.json
analysis/<video-name>-segment-001-analysis.json
analysis/<video-name>-segment-002-analysis.json
```

如果你已经有 `clips.json`，也可以直接批量处理整段发球视频：

```powershell
python ./scripts/process-serve-video.py --input-video "videos/Serving_practice_1.mp4" --clips-json "analysis/Serving_practice_1-clips.json" --provider stub
```

如果后面你已经准备好了 `pose_landmarker.task`，就把 `stub` 改成：

```powershell
python ./scripts/process-serve-video.py --input-video "videos/Serving_practice_1.mp4" --clips-json "analysis/Serving_practice_1-clips.json" --provider mediapipe --model-asset-path "assets/models/pose_landmarker.task"
```

如果你想把多段发球结果整理成一份中文总结报告，可以继续运行：

```powershell
python ./scripts/generate-serve-report.py --batch-analysis "analysis/Serving_practice_1-batch-analysis.json"
```

默认会生成：

```text
analysis/Serving_practice_1-serve-report.md
analysis/Serving_practice_1-serve-report.json
```

然后可以打开：

```text
dashboard/serve-report.html
```

页面会优先尝试读取：

```text
analysis/Serving_practice_1-serve-report.json
```

如果浏览器拦截自动读取，也可以在页面里手动选择这个 JSON 文件。

姿态 JSON 的结构参考：

```text
analysis/pose-template.json
```

分析结果的结构参考：

```text
analysis/auto-analysis-template.json
```

后台分析逻辑说明见：

```text
backend/BACKEND_LOGIC.md
```

## 9. 使用参考动作

将职业选手或教练的示范视频放入 `reference/` 目录，再和自己的关键帧做逐项对比。建议尽量统一拍摄角度、机位高度和画面方向。
