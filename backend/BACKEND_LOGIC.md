# 后台分析逻辑

## 总览

当前项目的后台分析主链路是：

```text
视频 -> 姿态关键点 -> 动作分段 -> 特征提取 -> 规则判断 -> 调整建议
```

前端页面只负责读取结果并展示，真正的分析核心在脚本层。

## 数据分层

### 1. 会话层

主文件：`analysis/<session-id>.json`

用于记录：

- 这次训练是谁、什么动作、哪一天
- 报告路径、原始视频路径、人工备注等元数据

### 2. 姿态层

主文件：`analysis/<session-id>-pose.json`

参考模板：`analysis/pose-template.json`

用于记录：

- 每一帧的人体关键点
- 关键点的置信度和时间戳

关键字段包括：

- `frames`
- `fps`
- `handedness`

### 3. 自动分析层

主文件：`analysis/<session-id>-analysis.json`

参考模板：`analysis/auto-analysis-template.json`

用于记录：

- 自动识别出的阶段
- 提取出的动作指标
- 命中的问题标签和建议

## 当前规则分析思路

当前版本优先使用规则法，而不是直接依赖黑盒模型。这样更容易解释问题，也方便教练和球员理解。

### 发球

当前重点关注的基础指标包括：

- `contact_wrist_height`
- `contact_wrist_forward_offset`
- `hip_shift`
- `average_knee_flexion`
- `wrist_vertical_range`
- `contact_elbow_angle`
- `contact_shoulder_angle`
- `finish_elbow_angle`
- `finish_wrist_shoulder_offset`
- `follow_through_drop`
- `finish_cross_body_offset`

对应输出的问题标签包括：

- 击球点偏低
- 击球点偏后
- 重心前送不足
- 蹬地不足
- 击球时手臂伸展不足
- 击球角度偏收
- 收拍不完整
- 收拍没有自然过身

### 正手 / 反手 / 截击

当前版本已经接入基础规则分析，重点关注：

- 击球点相对身体的位置
- 下肢和重心是否参与
- 挥拍路径和收拍完整性

后续还可以继续扩到：

- 正手削球
- 反手削球
- 不同机位下的专项规则

## 关键脚本

### `scripts/extract-pose.py`

输入：

- 原始视频

输出：

- `analysis/<session-id>-pose.json`

作用：

- 从视频中提取人体关键点
- 支持 `stub` 和 `mediapipe` 两种 provider

### `scripts/analyze-pose.py`

输入：

- `analysis/<session-id>-pose.json`

输出：

- `analysis/<session-id>-analysis.json`

作用：

- 自动估计动作阶段
- 计算动作指标
- 命中规则问题标签
- 生成调整重点

## 后续建议

当前项目已经适合做训练反馈闭环，下一步建议优先做：

1. 继续补强发球分段和发球专用规则
2. 让不同动作类型都具备独立的指标解释
3. 增加同一球员多次训练的自动对比分析
4. 让 dashboard 直接消费更完整的自动分析结果

