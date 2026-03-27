#!/usr/bin/env python3
"""Render feedback videos for each clip in a serve batch analysis."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description="Render per-clip feedback videos from a batch analysis JSON.")
    parser.add_argument("--batch-analysis", required=True, help="Path to the batch analysis JSON.")
    parser.add_argument("--suffix", default="-feedback-lite.mp4", help="Suffix for rendered feedback videos.")
    args = parser.parse_args()

    batch_path = Path(args.batch_analysis)
    if not batch_path.exists():
        raise SystemExit(f"Batch analysis file not found: {batch_path}")

    batch = load_json(batch_path)
    clips = batch.get("clips", [])
    if not clips:
        raise SystemExit("No clips found in batch analysis JSON.")

    for clip in clips:
        clip_video = Path(clip["clip_video"])
        pose_json = Path(clip["pose_json"])
        analysis_json = Path(clip["analysis_json"])
        frame_offset = int(clip.get("frame_offset", 0))
        output_path = analysis_json.with_name(analysis_json.stem.replace("-analysis", args.suffix.replace(".mp4", "")) + ".mp4")

        cmd = [
            sys.executable,
            str(ROOT / "scripts" / "render-feedback-video.py"),
            "--video",
            str(clip_video),
            "--pose",
            str(pose_json),
            "--analysis",
            str(analysis_json),
            "--output",
            str(output_path),
            "--frame-offset",
            str(frame_offset),
        ]
        subprocess.run(cmd, cwd=ROOT, check=True)
        print(f"Rendered: {output_path}")


if __name__ == "__main__":
    main()
