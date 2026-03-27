import argparse
import importlib.util
import json
from pathlib import Path

import cv2


LANDMARK_MAP = {
    "nose": 0,
    "left_shoulder": 11,
    "right_shoulder": 12,
    "left_elbow": 13,
    "right_elbow": 14,
    "left_wrist": 15,
    "right_wrist": 16,
    "left_hip": 23,
    "right_hip": 24,
    "left_knee": 25,
    "right_knee": 26,
    "left_ankle": 27,
    "right_ankle": 28,
}


def save_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def get_video_capture(video_path: Path):
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")
    return capture


def build_pose_document(session_id, action_type, handedness, fps, frames):
    return {
        "session_id": session_id,
        "action_type": action_type,
        "coordinate_system": {
            "origin": "top_left",
            "x_range": [0.0, 1.0],
            "y_range": [0.0, 1.0],
            "note": "Smaller y means higher in the frame.",
        },
        "fps": fps,
        "handedness": handedness,
        "frames": frames,
    }


def extract_stub(video_path: Path, action_type: str, handedness: str, sample_every: int):
    capture = get_video_capture(video_path)
    fps = capture.get(cv2.CAP_PROP_FPS) or 30.0
    session_id = video_path.stem
    frames = []
    frame_index = 0

    try:
        while True:
            ok, _ = capture.read()
            if not ok:
                break

            if frame_index % sample_every == 0:
                frames.append(
                    {
                        "frame_index": frame_index,
                        "timestamp": round(frame_index / fps, 4),
                        "keypoints": {},
                    }
                )
            frame_index += 1
    finally:
        capture.release()

    return build_pose_document(session_id, action_type, handedness, round(fps, 4), frames)


def landmark_to_point(landmarks, index):
    landmark = landmarks[index]
    visibility = getattr(landmark, "visibility", 0.0)
    return {
        "x": round(float(landmark.x), 4),
        "y": round(float(landmark.y), 4),
        "confidence": round(float(visibility), 4),
    }


def extract_mediapipe(video_path: Path, action_type: str, handedness: str, sample_every: int, model_asset_path: Path):
    if importlib.util.find_spec("mediapipe") is None:
        raise RuntimeError(
            "mediapipe is not installed. Install it first or run with --provider stub."
        )

    import mediapipe as mp
    from mediapipe.tasks.python import BaseOptions
    from mediapipe.tasks.python import vision

    if not model_asset_path or not model_asset_path.exists():
        raise RuntimeError(
            "A valid pose landmarker model is required for mediapipe provider. "
            "Pass --model-asset-path /absolute/or/relative/path/to/pose_landmarker.task"
        )

    capture = get_video_capture(video_path)
    fps = capture.get(cv2.CAP_PROP_FPS) or 30.0
    session_id = video_path.stem
    frames = []
    frame_index = 0

    options = vision.PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(model_asset_path)),
        running_mode=vision.RunningMode.VIDEO,
        num_poses=1,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        min_tracking_confidence=0.5,
        output_segmentation_masks=False,
    )
    landmarker = vision.PoseLandmarker.create_from_options(options)

    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break

            if frame_index % sample_every != 0:
                frame_index += 1
                continue

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            result = landmarker.detect_for_video(mp_image, int((frame_index / fps) * 1000))
            keypoints = {}

            if result.pose_landmarks:
                pose_landmarks = result.pose_landmarks[0]
                for name, index in LANDMARK_MAP.items():
                    keypoints[name] = landmark_to_point(pose_landmarks, index)

            frames.append(
                {
                    "frame_index": frame_index,
                    "timestamp": round(frame_index / fps, 4),
                    "keypoints": keypoints,
                }
            )
            frame_index += 1
    finally:
        landmarker.close()
        capture.release()

    return build_pose_document(session_id, action_type, handedness, round(fps, 4), frames)


def main():
    parser = argparse.ArgumentParser(description="Extract pose keypoints from a tennis video.")
    parser.add_argument("--input-video", required=True, help="Path to the source video.")
    parser.add_argument("--output", help="Output pose JSON path.")
    parser.add_argument(
        "--provider",
        choices=["mediapipe", "stub"],
        default="stub",
        help="Pose extraction backend. Use stub to scaffold the pipeline without pose estimation.",
    )
    parser.add_argument(
        "--model-asset-path",
        help="Path to pose_landmarker.task when using the mediapipe provider.",
    )
    parser.add_argument(
        "--action-type",
        choices=["serve", "forehand", "backhand", "forehand_slice", "backhand_slice", "volley", "other"],
        default="other",
        help="Action type to store in the pose file.",
    )
    parser.add_argument(
        "--handedness",
        choices=["right", "left"],
        default="right",
        help="Player handedness.",
    )
    parser.add_argument(
        "--sample-every",
        type=int,
        default=1,
        help="Keep every Nth frame in the pose output.",
    )
    args = parser.parse_args()

    video_path = Path(args.input_video)
    if not video_path.exists():
        raise SystemExit(f"Input video was not found: {video_path}")
    if args.sample_every < 1:
        raise SystemExit("--sample-every must be >= 1")

    output_path = Path(args.output) if args.output else video_path.with_name(video_path.stem + "-pose.json")
    model_asset_path = Path(args.model_asset_path) if args.model_asset_path else None

    if args.provider == "mediapipe":
        pose_data = extract_mediapipe(video_path, args.action_type, args.handedness, args.sample_every, model_asset_path)
    else:
        pose_data = extract_stub(video_path, args.action_type, args.handedness, args.sample_every)

    save_json(output_path, pose_data)
    print(f"Pose data written to: {output_path}")


if __name__ == "__main__":
    main()
