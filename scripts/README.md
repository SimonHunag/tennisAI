# 网球视频分析脚本

## `new-analysis-session.ps1`

创建一次新的训练分析会话，并自动生成目录、Markdown 报告和 JSON 元数据。

```powershell
./new-analysis-session.ps1 -SessionName "serve-side-view" -ActionType serve -AthleteName "张三" -AthleteId "zhang-san"
```

参数：

- `SessionName`: 会话名称，会和日期一起组成最终的会话 ID
- `ActionType`: 动作类型，可选 `serve`、`forehand`、`backhand`、`forehand_slice`、`backhand_slice`、`volley`、`other`
- `Date`: 可选，默认使用当天日期
- `AthleteName`: 可选，球员姓名，用于写入报告和元数据
- `AthleteId`: 可选，球员稳定标识，用于目录分层，推荐使用英文短横线格式

生成的 `analysis/<athlete_id>/<action_type>/<session-id>.json` 基于 [analysis/metadata-template.json](D:/ai/tennisAI/analysis/metadata-template.json) 创建，后续可直接补充结构化字段。

## `start-analysis.ps1`

统一的分析开始脚本。它会自动：

1. 创建标准会话目录
2. 把输入视频复制到标准位置
3. 发球视频自动做多片段检测、逐段分析和总结报告
4. 非发球视频直接跑单条分析
5. 重建训练总览

```powershell
./start-analysis.ps1 -InputVideo "D:\videos\serve-1.mp4" -SessionName "basket-serve" -ActionType serve -AthleteName "Simon" -AthleteId "simon"
```

参数：

- `InputVideo`: 原始视频路径，必填
- `SessionName`: 会话名称，必填
- `ActionType`: 动作类型，必填
- `AthleteName`: 球员名称，必填
- `AthleteId`: 球员 ID，必填
- `Date`: 可选，默认当天
- `Provider`: `mediapipe` 或 `stub`
- `Handedness`: `right` 或 `left`
- `SampleEvery`: 姿态提取采样步长
- `ModelAssetPath`: `mediapipe` 模型文件路径

## `extract-frames.ps1`

从视频中按固定时间间隔提取图片帧。

```powershell
./extract-frames.ps1 -InputVideo "videos/2026-03-25-serve-side-view/2026-03-25-serve-side-view.mp4" -OutputDir "frames/2026-03-25-serve-side-view" -Interval 1
```

参数：

- `InputVideo`: 输入视频路径，必填
- `OutputDir`: 输出目录，默认使用 `frames/<视频名>`
- `Interval`: 提取间隔，单位秒，默认 `1`
- `Force`: 允许覆盖当前输出目录下同名前缀的旧图片

## `sync-report-to-json.ps1`

从 Markdown 报告中读取结构化数据区块，并更新同名 JSON 元数据。

```powershell
./sync-report-to-json.ps1 -ReportPath "../analysis/2026-03-25-serve-side-view.md"
```

参数：

- `ReportPath`: Markdown 报告路径，必填
- `MetadataPath`: 可选，默认使用与报告同名的 `.json`

## `extract-pose.py`

从视频生成姿态关键点 JSON，作为自动分析脚本的输入。

```powershell
python ./extract-pose.py --input-video "videos/2026-03-25-serve-side-view/2026-03-25-serve-side-view.mp4" --provider stub --action-type serve
```

参数：

- `input-video`: 输入视频路径，必填
- `output`: 可选，输出路径，默认与视频同目录同名 `-pose.json`
- `provider`: `stub` 或 `mediapipe`
- `model-asset-path`: 使用 `mediapipe` 时必填，指向 `pose_landmarker.task`
- `action-type`: 动作类型
- `handedness`: `right` 或 `left`
- `sample-every`: 每隔多少帧保留一帧

说明：

- `stub` 会生成时间戳和空关键点结构，适合先打通整条分析链路
- `mediapipe` 会在本机已安装依赖且提供模型文件时输出真实人体关键点
- 模型目录建议使用 `assets/models/`，说明见 `assets/models/README.md`

## `build-training-summary.ps1`

扫描 `analysis/` 下的会话元数据 JSON，并生成训练汇总 Markdown、dashboard JSON 和 dashboard CSV。

```powershell
./build-training-summary.ps1
```

参数：

- `AnalysisDir`: 元数据所在目录，默认 `analysis`
- `OutputPath`: 汇总文件输出路径，默认 `analysis/training-summary.md`
- `JsonOutputPath`: dashboard JSON 输出路径，默认与 Markdown 同目录同名 `.json`
- `CsvOutputPath`: dashboard CSV 输出路径，默认与 Markdown 同目录同名 `.csv`
- `ActionType`: 可选，按动作类型筛选，支持多个值
- `Athlete`: 可选，按球员姓名或球员 ID 筛选，支持多个值
- `DateFrom`: 可选，起始日期，格式 `yyyy-MM-dd`
- `DateTo`: 可选，结束日期，格式 `yyyy-MM-dd`

说明：

- 如果存在 `analysis/<session-id>-analysis.json`，脚本会把自动分析摘要一起并入 dashboard JSON 和 CSV

## `dashboard/index.html`

纯静态本地可视化页面，读取 `analysis/training-summary.json` 并展示训练概览、动作分布、重点问题和会话列表。

如果浏览器无法直接从本地文件系统读取 JSON，可以通过页面内置的 `Choose JSON` 手动选择导出的数据文件。

## `analyze-pose.py`

读取姿态关键点 JSON，提取第一版动作特征，并基于规则生成自动分析结果。

```powershell
python ./scripts/analyze-pose.py --input analysis/2026-03-25-serve-side-view-pose.json
```

输出：

- 默认生成 `analysis/<session-id>-analysis.json`

当前已支持：

- `serve`
- `forehand`
- `backhand`
- `volley`

## `run-analysis-pipeline.py`

串联姿态提取、自动分析，以及可选的训练汇总重建。

```powershell
python ./run-analysis-pipeline.py --input-video "videos/2026-03-25-serve-side-view/2026-03-25-serve-side-view.mp4" --provider stub --action-type serve
```

参数：

- `input-video`: 输入视频路径，必填
- `provider`: `stub` 或 `mediapipe`
- `action-type`: 动作类型
- `handedness`: `right` 或 `left`
- `sample-every`: 每隔多少帧保留一帧
- `model-asset-path`: 使用 `mediapipe` 时传入模型文件
- `pose-output`: 可选，自定义姿态 JSON 输出路径
- `analysis-output`: 可选，自定义分析 JSON 输出路径
- `skip-summary`: 可选，跳过训练汇总重建
- `detect-serve-segments`: 当 `action-type=serve` 时，自动识别一个视频中的多个发球片段并逐段分析

多发球视频输出：

- `analysis/<video-name>-segments.json`
- `analysis/<video-name>-segment-001-analysis.json`
- `analysis/<video-name>-segment-002-analysis.json`
- ...

## `process-serve-video.py`

针对一个包含多个发球练习片段的整段视频，批量完成：

1. 读取 `clips.json`
2. 裁切单独片段视频
3. 对每个片段运行姿态提取和自动分析
4. 生成批处理索引 JSON

```powershell
python ./process-serve-video.py --input-video "videos/Serving_practice_1.mp4" --clips-json "analysis/Serving_practice_1-clips.json" --provider stub
```

参数：

- `input-video`: 原始整段发球视频
- `clips-json`: `detect-serve-clips.py` 生成的片段清单
- `provider`: `stub` 或 `mediapipe`
- `model-asset-path`: 使用 `mediapipe` 时传入模型文件
- `handedness`: `right` 或 `left`
- `sample-every`: 每隔多少帧保留一帧
- `clips-dir`: 可选，裁切后片段视频的输出目录
- `analysis-dir`: 可选，pose 和 analysis JSON 的输出目录
- `skip-summary`: 可选，跳过训练汇总重建

## `generate-serve-report.py`

把 `process-serve-video.py` 生成的批处理结果整理成一份中文 Markdown 发球总结报告。

```powershell
python ./generate-serve-report.py --batch-analysis "analysis/Serving_practice_1-batch-analysis.json"
```

参数：

- `batch-analysis`: `process-serve-video.py` 生成的批处理索引 JSON
- `output`: 可选，自定义 Markdown 报告输出路径
- `json-output`: 可选，自定义前端报告 JSON 输出路径

默认输出：

- `analysis/<video-name>-serve-report.md`
- `analysis/<video-name>-serve-report.json`

## `compare-serve-reports.py`

比较两份 `*-serve-report.json`，生成一份中文对比报告，适合同一球员同一动作的前后对照。

```powershell
python ./compare-serve-reports.py --baseline "analysis/serve-day-1-serve-report.json" --target "analysis/serve-day-2-serve-report.json"
```

参数：

- `baseline`: 基线报告 JSON
- `target`: 对比报告 JSON
- `output`: 可选，自定义 Markdown 输出路径
- `json-output`: 可选，自定义 JSON 输出路径

## `render-feedback-video.py`

根据原视频、姿态 JSON 和分析 JSON，输出一条带动作反馈的可视化视频。

- 默认关键点显示为绿色
- 当前阶段需要重点关注的关键点显示为红色
- 左上角会附带当前指标和问题提示

```powershell
python ./render-feedback-video.py --video "videos/laofeng/serve/2026-03-26-1774525501975601/2026-03-26-1774525501975601.mp4" --pose "analysis/laofeng/serve/2026-03-26-1774525501975601/2026-03-26-1774525501975601-pose.json" --analysis "analysis/laofeng/serve/2026-03-26-1774525501975601/2026-03-26-1774525501975601-analysis.json"
```

参数：

- `video`: 原始视频路径
- `pose`: 姿态 JSON 路径
- `analysis`: 自动分析 JSON 路径
- `output`: 可选，自定义输出视频路径
