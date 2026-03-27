#!/usr/bin/env python3
"""Extract clip videos from pose-based serve segments and analyze each segment."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_command(args):
    result = subprocess.run(args, cwd=ROOT, check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def extract_clip(video_path: Path, fps: float, segment: dict, output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    start_time = max(0.0, float(segment["frame_start"]) / fps)
    duration = max(0.1, (float(segment["frame_end"]) - float(segment["frame_start"])) / fps)
    run_command(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            str(round(start_time, 3)),
            "-i",
            str(video_path),
            "-t",
            str(round(duration, 3)),
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            "-y",
            str(output_path),
        ]
    )


def main():
    parser = argparse.ArgumentParser(description="Process serve clips based on pose-detected segments.")
    parser.add_argument("--video", required=True, help="Original full video.")
    parser.add_argument("--pose", required=True, help="Full pose JSON for the original video.")
    parser.add_argument("--segments", required=True, help="Segments JSON from detect-serve-segments.py.")
    parser.add_argument("--clips-dir", required=True, help="Output directory for extracted clip videos.")
    parser.add_argument("--analysis-dir", required=True, help="Output directory for clip analysis JSON files.")
    args = parser.parse_args()

    video_path = Path(args.video)
    pose_path = Path(args.pose)
    segments_path = Path(args.segments)
    clips_dir = Path(args.clips_dir)
    analysis_dir = Path(args.analysis_dir)

    for path in [video_path, pose_path, segments_path]:
        if not path.exists():
            raise SystemExit(f"Required file not found: {path}")

    pose_data = load_json(pose_path)
    segments_data = load_json(segments_path)
    fps = pose_data.get("fps", 30.0) or 30.0
    session_id = pose_data.get("session_id", video_path.stem)
    segments = segments_data.get("segments", [])
    if not segments:
        raise SystemExit("No segments found in pose segments JSON.")

    analysis_dir.mkdir(parents=True, exist_ok=True)
    processed = []
    for index, segment in enumerate(segments, start=1):
        clip_id = f"{session_id}-poseclip-{index:03d}"
        clip_video = clips_dir / f"{clip_id}.mp4"
        extract_clip(video_path, fps, segment, clip_video)

        analysis_path = analysis_dir / f"{clip_id}-analysis.json"
        run_command(
            [
                sys.executable,
                str(ROOT / "scripts" / "analyze-pose.py"),
                "--input",
                str(pose_path),
                "--output",
                str(analysis_path),
                "--frame-start",
                str(segment["frame_start"]),
                "--frame-end",
                str(segment["frame_end"]),
            ]
        )

        processed.append(
            {
                "clip_id": clip_id,
                "clip_video": str(clip_video).replace("\\", "/"),
                "pose_json": str(pose_path).replace("\\", "/"),
                "analysis_json": str(analysis_path).replace("\\", "/"),
                "frame_start": segment["frame_start"],
                "frame_end": segment["frame_end"],
                "frame_offset": segment["frame_start"],
                "time_start": round(segment["frame_start"] / fps, 3),
                "time_end": round(segment["frame_end"] / fps, 3),
                "duration_seconds": round((segment["frame_end"] - segment["frame_start"]) / fps, 3),
            }
        )

    summary_path = analysis_dir / f"{session_id}-poseclip-batch-analysis.json"
    save_json(
        summary_path,
        {
            "video_file": str(video_path).replace("\\", "/"),
            "provider": "pose_segments",
            "clip_count": len(processed),
            "clips": processed,
        },
    )
    print(f"Pose-segment batch analysis written to: {summary_path}")


if __name__ == "__main__":
    main()
