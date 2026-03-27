#!/usr/bin/env python3
"""Render a feedback video with green/red pose landmarks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


SKELETON_EDGES = [
    ("left_shoulder", "right_shoulder"),
    ("left_shoulder", "left_elbow"),
    ("left_elbow", "left_wrist"),
    ("right_shoulder", "right_elbow"),
    ("right_elbow", "right_wrist"),
    ("left_shoulder", "left_hip"),
    ("right_shoulder", "right_hip"),
    ("left_hip", "right_hip"),
    ("left_hip", "left_knee"),
    ("left_knee", "left_ankle"),
    ("right_hip", "right_knee"),
    ("right_knee", "right_ankle"),
]

ISSUE_LABELS = {
    "low_contact_point": "击球点偏低",
    "contact_too_far_back": "击球点偏后",
    "limited_weight_transfer": "重心前送不足",
    "limited_leg_drive": "蹬地不足",
    "contact_arm_not_extended": "击球手臂未伸展",
    "contact_angle_too_closed": "击球角度偏收",
    "incomplete_follow_through": "收拍不完整",
    "finish_not_across_body": "收拍未过身",
}

FONT_CANDIDATES = [
    Path(r"C:\Windows\Fonts\msyh.ttc"),
    Path(r"C:\Windows\Fonts\msyhbd.ttc"),
    Path(r"C:\Windows\Fonts\simhei.ttf"),
]


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_font(size):
    for path in FONT_CANDIDATES:
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def valid_point(point):
    return bool(point) and point.get("confidence", 0.0) > 0.3


def point_to_pixel(point, width, height):
    return int(point["x"] * width), int(point["y"] * height)


def build_pose_lookup(frames):
    pose_by_frame = {}
    for frame in frames:
        pose_by_frame[frame["frame_index"]] = frame
    frame_indices = sorted(pose_by_frame)
    return pose_by_frame, frame_indices


def find_pose_frame(frame_index, pose_by_frame, frame_indices):
    if frame_index in pose_by_frame:
        return pose_by_frame[frame_index]
    candidate = None
    for idx in frame_indices:
        if idx > frame_index:
            break
        candidate = idx
    if candidate is None and frame_indices:
        candidate = frame_indices[0]
    return pose_by_frame.get(candidate) if candidate is not None else None


def collect_issue_windows(analysis):
    phases = analysis.get("phases", {})
    contact = phases.get("contact_frame", 0)
    finish = phases.get("finish_frame", contact)
    return {
        "contact": (max(0, contact - 12), contact + 12),
        "drive": (max(0, contact - 20), contact + 8),
        "finish": (max(0, finish - 18), finish + 2),
    }


def build_issue_joint_map(handedness):
    hitting = {
        "shoulder": f"{handedness}_shoulder",
        "elbow": f"{handedness}_elbow",
        "wrist": f"{handedness}_wrist",
        "hip": f"{handedness}_hip",
        "knee": f"{handedness}_knee",
        "ankle": f"{handedness}_ankle",
    }
    return {
        "low_contact_point": {"window": "contact", "joints": [hitting["wrist"], hitting["elbow"], hitting["shoulder"]]},
        "contact_too_far_back": {"window": "contact", "joints": [hitting["wrist"], hitting["shoulder"], "left_hip", "right_hip"]},
        "limited_weight_transfer": {"window": "drive", "joints": ["left_hip", "right_hip", "left_knee", "right_knee", "left_ankle", "right_ankle"]},
        "limited_leg_drive": {"window": "drive", "joints": ["left_hip", "right_hip", "left_knee", "right_knee", "left_ankle", "right_ankle"]},
        "contact_arm_not_extended": {"window": "contact", "joints": [hitting["shoulder"], hitting["elbow"], hitting["wrist"]]},
        "contact_angle_too_closed": {"window": "contact", "joints": [hitting["hip"], hitting["shoulder"], hitting["wrist"]]},
        "incomplete_follow_through": {"window": "finish", "joints": [hitting["shoulder"], hitting["elbow"], hitting["wrist"]]},
        "finish_not_across_body": {"window": "finish", "joints": [hitting["shoulder"], hitting["elbow"], hitting["wrist"]]},
    }


def issue_active(frame_index, issue_code, issue_map, windows):
    rule = issue_map.get(issue_code)
    if not rule:
        return False
    start, end = windows[rule["window"]]
    return start <= frame_index <= end


def active_red_joints(frame_index, issues, issue_map, windows):
    joints = set()
    active_labels = []
    for issue in issues:
        code = issue.get("issue_code")
        if code and issue_active(frame_index, code, issue_map, windows):
            joints.update(issue_map[code]["joints"])
            active_labels.append(ISSUE_LABELS.get(code, code))
    return joints, active_labels


def draw_overlay(frame, pose_frame, red_joints, active_labels, analysis):
    height, width = frame.shape[:2]
    keypoints = pose_frame.get("keypoints", {}) if pose_frame else {}

    for a, b in SKELETON_EDGES:
        pa = keypoints.get(a)
        pb = keypoints.get(b)
        if valid_point(pa) and valid_point(pb):
            cv2.line(frame, point_to_pixel(pa, width, height), point_to_pixel(pb, width, height), (180, 180, 180), 2)

    for name, point in keypoints.items():
        if not valid_point(point):
            continue
        color = (0, 0, 255) if name in red_joints else (0, 200, 0)
        cv2.circle(frame, point_to_pixel(point, width, height), 6, color, -1)
        cv2.circle(frame, point_to_pixel(point, width, height), 9, (255, 255, 255), 1)

    metrics = analysis.get("metrics", {})
    metric_text = f"肘角 {metrics.get('contact_elbow_angle', 'n/a')}  肩角 {metrics.get('contact_shoulder_angle', 'n/a')}  收拍 {metrics.get('follow_through_drop', 'n/a')}"
    issues_text = "关注: " + ", ".join(active_labels[:2]) if active_labels else "当前帧无重点警示"
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(rgb)
    draw = ImageDraw.Draw(image)
    title_font = load_font(19)
    body_font = load_font(16)

    # Compact top-left status chip.
    draw.rounded_rectangle((18, 18, 260, 82), radius=16, fill=(20, 20, 20, 168), outline=(70, 70, 70))
    draw.text((32, 28), "TennisAI 动作反馈", font=title_font, fill=(255, 255, 255))
    draw.text((32, 55), "绿=稳定  红=当前需关注", font=body_font, fill=(220, 220, 220))

    # Small metric chip on the top-right so it doesn't cover the torso.
    metric_width = min(width - 36, 360)
    metric_left = max(18, width - metric_width - 18)
    draw.rounded_rectangle((metric_left, 18, width - 18, 58), radius=14, fill=(20, 20, 20, 156), outline=(70, 70, 70))
    draw.text((metric_left + 14, 29), metric_text, font=body_font, fill=(200, 230, 255))

    # Bottom hint bar to avoid blocking the hitting zone.
    bar_top = max(18, height - 56)
    draw.rounded_rectangle((18, bar_top, width - 18, height - 18), radius=14, fill=(20, 20, 20, 148), outline=(70, 70, 70))
    draw.text((32, bar_top + 11), issues_text, font=body_font, fill=(110, 220, 255) if active_labels else (120, 220, 120))
    frame[:, :, :] = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)


def main():
    parser = argparse.ArgumentParser(description="Render a feedback video with green/red pose landmarks.")
    parser.add_argument("--video", required=True, help="Source video path.")
    parser.add_argument("--pose", required=True, help="Pose JSON path.")
    parser.add_argument("--analysis", required=True, help="Analysis JSON path.")
    parser.add_argument("--output", help="Output video path.")
    parser.add_argument("--frame-offset", type=int, default=0, help="Offset added to rendered frame indices when matching pose frames.")
    args = parser.parse_args()

    video_path = Path(args.video)
    pose_path = Path(args.pose)
    analysis_path = Path(args.analysis)
    if not video_path.exists():
        raise SystemExit(f"Video not found: {video_path}")
    if not pose_path.exists():
        raise SystemExit(f"Pose JSON not found: {pose_path}")
    if not analysis_path.exists():
        raise SystemExit(f"Analysis JSON not found: {analysis_path}")

    pose = load_json(pose_path)
    analysis = load_json(analysis_path)
    pose_by_frame, frame_indices = build_pose_lookup(pose.get("frames", []))
    handedness = pose.get("handedness", "right")
    issue_map = build_issue_joint_map(handedness)
    windows = collect_issue_windows(analysis)
    issues = analysis.get("issues", [])

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise SystemExit(f"Could not open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or pose.get("fps", 30.0) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    output_path = Path(args.output) if args.output else video_path.with_name(video_path.stem + "-feedback.mp4")
    writer = cv2.VideoWriter(str(output_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    if not writer.isOpened():
        raise SystemExit(f"Could not open video writer: {output_path}")

    frame_index = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            source_frame_index = frame_index + args.frame_offset
            pose_frame = find_pose_frame(source_frame_index, pose_by_frame, frame_indices)
            red_joints, active_labels = active_red_joints(source_frame_index, issues, issue_map, windows)
            draw_overlay(frame, pose_frame, red_joints, active_labels, analysis)
            writer.write(frame)
            frame_index += 1
    finally:
        cap.release()
        writer.release()

    print(f"Feedback video written to: {output_path}")


if __name__ == "__main__":
    main()
