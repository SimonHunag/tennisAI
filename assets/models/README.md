# 模型文件说明

这里用于存放本地姿态分析模型文件。

当前项目使用 MediaPipe Pose Landmarker 时，建议把模型放在：

```text
assets/models/pose_landmarker.task
```

使用示例：

```powershell
python ./scripts/extract-pose.py --input-video "videos/your-video.mp4" --provider mediapipe --model-asset-path "assets/models/pose_landmarker.task" --action-type serve
```

说明：

- `stub` provider 不需要模型文件
- `mediapipe` provider 需要本地 `.task` 模型
- 建议统一使用这个目录，方便脚本默认读取和团队协作

