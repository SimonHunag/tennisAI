# 团队工作流

为了支持多球员、多动作和长期对比，建议统一采用下面的目录层次：

```text
videos/<athlete_id>/<action_type>/<session_id>/<session_id>.mp4
frames/<athlete_id>/<action_type>/<session_id>/
analysis/<athlete_id>/<action_type>/<session_id>.md
analysis/<athlete_id>/<action_type>/<session_id>.json
```

推荐动作类型：

- `serve`
- `forehand`
- `backhand`
- `forehand_slice`
- `backhand_slice`
- `volley`

推荐会话命名：

- `2026-03-26-basket-serve`
- `2026-03-26-cross-forehand`
- `2026-03-26-low-backhand-slice`

推荐球员标识：

- `zhang-san`
- `li-si`
- `u12-a-01`

这样做的好处：

- 同一个球员的同类动作天然归档在一起
- 后续按球员、按动作做长期趋势分析更容易
- 别人接手时，不需要先猜每个文件属于谁

如果后续要做“对比分析”，建议至少固定这 3 个维度：

- 同一球员，不同日期，同一动作
- 不同球员，同一动作，同一训练周期
- 同一球员，同一动作，不同机位

第一版可以直接用：

```powershell
python ./scripts/compare-serve-reports.py --baseline "analysis/player-a/serve/2026-03-01-serve-report.json" --target "analysis/player-a/serve/2026-03-15-serve-report.json"
```
