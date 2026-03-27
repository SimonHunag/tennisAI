import argparse
import json
from pathlib import Path

import cv2
import numpy as np


def save_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def detect_motion_segments(video_path: Path, sample_every: int, threshold_scale: float, min_active_samples: int, merge_gap_samples: int):
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    prev = None
    scores = []
    frame_indices = []
    index = 0

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if index % sample_every != 0:
                index += 1
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.resize(gray, (160, 90))
            if prev is None:
                score = 0.0
            else:
                score = float(cv2.absdiff(gray, prev).mean())

            scores.append(score)
            frame_indices.append(index)
            prev = gray
            index += 1
    finally:
        cap.release()

    if not scores:
        return fps, [], {"threshold": 0.0, "scores": []}

    arr = np.array(scores, dtype=float)
    kernel = np.ones(9) / 9.0
    smooth = np.convolve(arr, kernel, mode="same")
    threshold = max(3.0, float(smooth.mean() + smooth.std() * threshold_scale))
    active = smooth > threshold

    raw_segments = []
    start = None
    for i, flag in enumerate(active):
        if flag and start is None:
            start = i
        elif not flag and start is not None:
            end = i - 1
            if end - start + 1 >= min_active_samples:
                raw_segments.append([start, end])
            start = None
    if start is not None:
        end = len(active) - 1
        if end - start + 1 >= min_active_samples:
            raw_segments.append([start, end])

    merged = []
    for start, end in raw_segments:
        if not merged:
            merged.append([start, end])
        elif start - merged[-1][1] <= merge_gap_samples:
            merged[-1][1] = end
        else:
            merged.append([start, end])

    segments = []
    for idx, (start_sample, end_sample) in enumerate(merged, start=1):
        frame_start = frame_indices[start_sample]
        frame_end = frame_indices[end_sample]
        segments.append(
            {
                "clip_id": f"{video_path.stem}-clip-{idx:03d}",
                "frame_start": frame_start,
                "frame_end": frame_end,
                "time_start": round(frame_start / fps, 3),
                "time_end": round(frame_end / fps, 3),
                "duration_seconds": round((frame_end - frame_start) / fps, 3),
            }
        )

    return fps, segments, {"threshold": round(threshold, 4), "scores": [round(x, 4) for x in smooth.tolist()]}


def main():
    parser = argparse.ArgumentParser(description="Detect repeated serve practice clips from a full training video.")
    parser.add_argument("--input-video", required=True, help="Path to the source video.")
    parser.add_argument("--output", help="Output clip summary JSON path.")
    parser.add_argument("--sample-every", type=int, default=3, help="Process every Nth frame.")
    parser.add_argument("--threshold-scale", type=float, default=0.8, help="Sensitivity multiplier for motion threshold.")
    parser.add_argument("--min-active-samples", type=int, default=8, help="Minimum active samples to form one clip.")
    parser.add_argument("--merge-gap-samples", type=int, default=10, help="Merge nearby motion bursts within this sample gap.")
    args = parser.parse_args()

    video_path = Path(args.input_video)
    if not video_path.exists():
        raise SystemExit(f"Input video was not found: {video_path}")
    if args.sample_every < 1:
        raise SystemExit("--sample-every must be >= 1")

    fps, segments, debug = detect_motion_segments(
        video_path,
        sample_every=args.sample_every,
        threshold_scale=args.threshold_scale,
        min_active_samples=args.min_active_samples,
        merge_gap_samples=args.merge_gap_samples,
    )

    output_path = Path(args.output) if args.output else Path("analysis") / f"{video_path.stem}-clips.json"
    save_json(
        output_path,
        {
            "video_file": str(video_path).replace("\\", "/"),
            "fps": round(fps, 4),
            "sample_every": args.sample_every,
            "clip_count": len(segments),
            "clips": segments,
            "debug": {"threshold": debug["threshold"]},
        },
    )
    print(f"Serve clip summary written to: {output_path}")
    print(f"Detected clip count: {len(segments)}")


if __name__ == "__main__":
    main()
