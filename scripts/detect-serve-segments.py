import argparse
import json
from pathlib import Path


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def get_point(frame, name):
    return frame.get("keypoints", {}).get(name)


def valid_point(point):
    return bool(point) and point.get("confidence", 0) > 0.3


def is_in_frame(point, min_x: float = 0.12, max_x: float = 0.88):
    return valid_point(point) and min_x <= point.get("x", -1) <= max_x


def is_valid_serve_contact(frame, handedness: str, min_contact_lift: float):
    wrist = get_point(frame, f"{handedness}_wrist")
    shoulder = get_point(frame, f"{handedness}_shoulder")
    hip = get_point(frame, f"{handedness}_hip")
    opposite_shoulder = get_point(frame, "left_shoulder" if handedness == "right" else "right_shoulder")
    opposite_hip = get_point(frame, "left_hip" if handedness == "right" else "right_hip")
    if not all(valid_point(point) for point in [wrist, shoulder, hip, opposite_shoulder, opposite_hip]):
        return False
    if not all(is_in_frame(point) for point in [wrist, shoulder, hip, opposite_shoulder, opposite_hip]):
        return False
    return wrist["y"] <= shoulder["y"] - min_contact_lift


def build_segments(
    pose_data,
    action_type: str,
    min_gap_frames: int,
    pre_frames: int,
    post_frames: int,
    min_contact_lift: float,
):
    if action_type != "serve":
        raise ValueError("Segment detection is currently implemented for serve videos only.")

    frames = pose_data.get("frames", [])
    handedness = pose_data.get("handedness", "right")
    wrist_name = f"{handedness}_wrist"

    wrist_points = []
    for frame in frames:
        wrist = get_point(frame, wrist_name)
        if valid_point(wrist):
            wrist_points.append(
                {
                    "frame_index": frame["frame_index"],
                    "timestamp": frame["timestamp"],
                    "y": wrist["y"],
                }
            )

    if len(wrist_points) < 5:
        return []

    contacts = []
    frames_by_index = {frame["frame_index"]: frame for frame in frames}

    for index in range(2, len(wrist_points) - 2):
        current = wrist_points[index]
        neighbors = wrist_points[index - 2:index] + wrist_points[index + 1:index + 3]
        if all(current["y"] < item["y"] for item in neighbors):
            neighbor_avg = sum(item["y"] for item in neighbors) / len(neighbors)
            prominence = neighbor_avg - current["y"]
            if prominence >= 0.01:
                frame = frames_by_index.get(current["frame_index"], {})
                if not is_valid_serve_contact(frame, handedness, min_contact_lift):
                    continue
                if not contacts or current["frame_index"] - contacts[-1]["contact_frame"] >= min_gap_frames:
                    contacts.append(
                        {
                            "contact_frame": current["frame_index"],
                            "contact_timestamp": current["timestamp"],
                        }
                    )

    if not contacts:
        return []

    segments = []
    first_frame = frames[0]["frame_index"]
    last_frame = frames[-1]["frame_index"]

    for item in contacts:
        frame_start = max(first_frame, item["contact_frame"] - pre_frames)
        frame_end = min(last_frame, item["contact_frame"] + post_frames)
        if segments and frame_start <= segments[-1]["frame_end"]:
            segments[-1]["frame_end"] = max(segments[-1]["frame_end"], frame_end)
            segments[-1]["contact_frames"].append(item["contact_frame"])
            continue

        segments.append(
            {
                "segment_id": f"{pose_data.get('session_id', 'session')}-segment-{len(segments) + 1:03d}",
                "frame_start": frame_start,
                "frame_end": frame_end,
                "contact_frames": [item["contact_frame"]],
            }
        )

    return segments


def main():
    parser = argparse.ArgumentParser(description="Detect repeated serve segments from pose data.")
    parser.add_argument("--input", required=True, help="Input pose JSON file.")
    parser.add_argument("--output", help="Output segments JSON file.")
    parser.add_argument("--action-type", default="serve", help="Currently only serve is supported.")
    parser.add_argument("--min-gap-seconds", type=float, default=1.2, help="Minimum separation between serve contacts.")
    parser.add_argument("--pre-seconds", type=float, default=1.4, help="Frames to include before detected contact.")
    parser.add_argument("--post-seconds", type=float, default=1.5, help="Frames to include after detected contact.")
    parser.add_argument("--min-contact-lift", type=float, default=0.015, help="Minimum vertical margin by which wrist must be above the hitting shoulder at contact.")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise SystemExit(f"Input pose file was not found: {input_path}")

    pose_data = load_json(input_path)
    fps = pose_data.get("fps", 30) or 30
    min_gap_frames = max(1, int(round(args.min_gap_seconds * fps)))
    pre_frames = max(1, int(round(args.pre_seconds * fps)))
    post_frames = max(1, int(round(args.post_seconds * fps)))

    segments = build_segments(
        pose_data,
        args.action_type,
        min_gap_frames,
        pre_frames,
        post_frames,
        args.min_contact_lift,
    )
    output_path = Path(args.output) if args.output else input_path.with_name(input_path.stem.replace("-pose", "") + "-segments.json")

    save_json(
        output_path,
        {
            "session_id": pose_data.get("session_id", ""),
            "action_type": args.action_type,
            "fps": fps,
            "segments": segments,
        },
    )
    print(f"Serve segments written to: {output_path}")


if __name__ == "__main__":
    main()
