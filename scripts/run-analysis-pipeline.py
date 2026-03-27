import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def run_command(args):
    result = subprocess.run(args, cwd=ROOT, check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def has_session_metadata():
    analysis_dir = ROOT / "analysis"
    if not analysis_dir.exists():
        return False

    for path in analysis_dir.rglob("*.json"):
        name = path.name
        if (
            name != "metadata-template.json"
            and name != "pose-template.json"
            and name != "auto-analysis-template.json"
            and name != "training-summary.json"
            and not name.endswith("-batch-analysis.json")
            and not name.endswith("-clips.json")
            and not name.endswith("-serve-report.json")
            and not name.endswith("-pose.json")
            and not name.endswith("-analysis.json")
        ):
            return True
    return False


def main():
    parser = argparse.ArgumentParser(
        description="Run the TennisAI backend pipeline: extract pose, analyze pose, and optionally rebuild summaries."
    )
    parser.add_argument("--input-video", required=True, help="Path to the source video.")
    parser.add_argument(
        "--provider",
        choices=["stub", "mediapipe"],
        default="stub",
        help="Pose extraction provider.",
    )
    parser.add_argument(
        "--action-type",
        choices=["serve", "forehand", "backhand", "forehand_slice", "backhand_slice", "volley", "other"],
        default="other",
        help="Action type for the current session.",
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
    parser.add_argument("--model-asset-path", help="Path to pose_landmarker.task for mediapipe provider.")
    parser.add_argument("--pose-output", help="Optional path for the pose JSON output.")
    parser.add_argument("--analysis-output", help="Optional path for the analysis JSON output.")
    parser.add_argument(
        "--detect-serve-segments",
        action="store_true",
        help="When action-type is serve, detect repeated serve clips and analyze each segment separately.",
    )
    parser.add_argument(
        "--skip-summary",
        action="store_true",
        help="Skip rebuilding training-summary outputs after analysis.",
    )
    args = parser.parse_args()

    input_video = Path(args.input_video)
    if not input_video.exists():
        raise SystemExit(f"Input video was not found: {input_video}")

    default_pose_output = Path("analysis") / f"{input_video.stem}-pose.json"
    default_analysis_output = Path("analysis") / f"{input_video.stem}-analysis.json"
    pose_output = Path(args.pose_output) if args.pose_output else default_pose_output
    analysis_output = Path(args.analysis_output) if args.analysis_output else default_analysis_output

    extract_cmd = [
        sys.executable,
        str(ROOT / "scripts" / "extract-pose.py"),
        "--input-video",
        str(input_video),
        "--provider",
        args.provider,
        "--action-type",
        args.action_type,
        "--handedness",
        args.handedness,
        "--sample-every",
        str(args.sample_every),
        "--output",
        str(pose_output),
    ]
    if args.model_asset_path:
        extract_cmd.extend(["--model-asset-path", args.model_asset_path])

    analyze_cmd = [
        sys.executable,
        str(ROOT / "scripts" / "analyze-pose.py"),
        "--input",
        str(pose_output),
        "--output",
        str(analysis_output),
    ]

    print("Step 1/3: extracting pose data...")
    run_command(extract_cmd)

    if args.detect_serve_segments and args.action_type == "serve":
        segments_output = Path("analysis") / f"{input_video.stem}-segments.json"
        segment_cmd = [
            sys.executable,
            str(ROOT / "scripts" / "detect-serve-segments.py"),
            "--input",
            str(pose_output),
            "--output",
            str(segments_output),
            "--action-type",
            "serve",
        ]

        print("Step 2/4: detecting repeated serve segments...")
        run_command(segment_cmd)

        import json

        segments_data = json.loads((ROOT / segments_output).read_text(encoding="utf-8"))
        segments = segments_data.get("segments", [])
        if not segments:
            print("No serve segments were detected. Falling back to whole-video analysis.")
            print("Step 3/4: generating rule-based analysis...")
            run_command(analyze_cmd)
        else:
            print(f"Step 3/4: generating rule-based analysis for {len(segments)} serve segments...")
            for index, segment in enumerate(segments, start=1):
                segment_output = Path("analysis") / f"{input_video.stem}-segment-{index:03d}-analysis.json"
                run_command(
                    [
                        sys.executable,
                        str(ROOT / "scripts" / "analyze-pose.py"),
                        "--input",
                        str(pose_output),
                        "--output",
                        str(segment_output),
                        "--frame-start",
                        str(segment["frame_start"]),
                        "--frame-end",
                        str(segment["frame_end"]),
                    ]
                )
            print(f"Segment index written to: {segments_output}")
    else:
        print("Step 2/3: generating rule-based analysis...")
        run_command(analyze_cmd)

    if not args.skip_summary and has_session_metadata():
        print("Step 4/4: rebuilding training summaries..." if args.detect_serve_segments and args.action_type == "serve" else "Step 3/3: rebuilding training summaries...")
        run_command(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(ROOT / "scripts" / "build-training-summary.ps1"),
            ]
        )
    elif not args.skip_summary:
        print("Step 4/4: skipped summary rebuild because no session metadata JSON was found." if args.detect_serve_segments and args.action_type == "serve" else "Step 3/3: skipped summary rebuild because no session metadata JSON was found.")
    else:
        print("Step 4/4: skipped summary rebuild." if args.detect_serve_segments and args.action_type == "serve" else "Step 3/3: skipped summary rebuild.")

    print("Pipeline completed successfully.")
    print(f"Pose output: {pose_output}")
    print(f"Analysis output: {analysis_output}")


if __name__ == "__main__":
    main()
