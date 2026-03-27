#!/usr/bin/env python3
"""Compare two serve report JSON files and generate a readable diff report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


HIGHER_IS_BETTER = {
    "contact_wrist_height": False,
    "contact_wrist_forward_offset": True,
    "contact_elbow_angle": True,
    "contact_shoulder_angle": True,
    "hip_shift": True,
    "average_knee_flexion": False,
    "wrist_vertical_range": None,
    "finish_elbow_angle": None,
    "finish_wrist_shoulder_offset": None,
    "follow_through_drop": True,
    "finish_cross_body_offset": True,
}


METRIC_LABELS = {
    "contact_wrist_height": "击球高度",
    "contact_wrist_forward_offset": "击球前移量",
    "contact_elbow_angle": "击球肘角",
    "contact_shoulder_angle": "击球肩臂夹角",
    "hip_shift": "重心前送",
    "average_knee_flexion": "平均屈膝角度",
    "wrist_vertical_range": "挥拍垂直变化",
    "finish_elbow_angle": "收拍肘角",
    "finish_wrist_shoulder_offset": "收拍手腕相对肩高差",
    "follow_through_drop": "收拍下落幅度",
    "finish_cross_body_offset": "收拍过身幅度",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def issue_map(report: dict[str, Any]) -> dict[str, int]:
    return {item["code"]: item["count"] for item in report.get("common_issues", [])}


def metric_map(report: dict[str, Any]) -> dict[str, float]:
    return {item["name"]: item["average"] for item in report.get("metric_overview", [])}


def describe_delta(metric_name: str, delta: float) -> str:
    direction = HIGHER_IS_BETTER.get(metric_name)
    label = METRIC_LABELS.get(metric_name, metric_name)
    if abs(delta) < 1e-9:
        return f"{label} 基本持平。"
    if direction is None:
        return f"{label} 变化了 {delta:+.3f}，建议结合视频人工判断这是不是积极变化。"
    if direction:
        return f"{label} {'改善' if delta > 0 else '回落'}了 {abs(delta):.3f}。"
    return f"{label} {'改善' if delta < 0 else '回落'}了 {abs(delta):.3f}。"


def build_payload(baseline: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    baseline_issues = issue_map(baseline)
    target_issues = issue_map(target)
    baseline_metrics = metric_map(baseline)
    target_metrics = metric_map(target)

    all_issue_codes = sorted(set(baseline_issues) | set(target_issues))
    all_metric_names = sorted(set(baseline_metrics) | set(target_metrics))

    issue_deltas = []
    for code in all_issue_codes:
        base_count = baseline_issues.get(code, 0)
        target_count = target_issues.get(code, 0)
        issue_deltas.append(
            {
                "code": code,
                "baseline_count": base_count,
                "target_count": target_count,
                "delta": target_count - base_count,
            }
        )

    metric_deltas = []
    for name in all_metric_names:
        base_value = baseline_metrics.get(name)
        target_value = target_metrics.get(name)
        if base_value is None or target_value is None:
            delta = None
        else:
            delta = round(target_value - base_value, 3)
        metric_deltas.append(
            {
                "name": name,
                "baseline_value": base_value,
                "target_value": target_value,
                "delta": delta,
                "comment": describe_delta(name, delta) if delta is not None else f"{METRIC_LABELS.get(name, name)} 缺少可比数据。",
            }
        )

    improved_issues = [item for item in issue_deltas if item["delta"] < 0]
    worsened_issues = [item for item in issue_deltas if item["delta"] > 0]

    if worsened_issues and not improved_issues:
        overall = "本次对比里，主要规则问题总体有加重趋势，建议先修正问题数量增加最多的环节。"
    elif improved_issues and not worsened_issues:
        overall = "本次对比里，主要规则问题整体在减少，训练方向基本是对的。"
    elif improved_issues or worsened_issues:
        overall = "本次对比里有改善也有波动，说明动作正在变化，但稳定性还不够。"
    else:
        overall = "两次报告命中的主要规则问题接近，短期内动作模式变化不大。"

    return {
        "baseline_video": baseline.get("video_file"),
        "target_video": target.get("video_file"),
        "baseline_clip_count": baseline.get("clip_count"),
        "target_clip_count": target.get("clip_count"),
        "overall_assessment": overall,
        "issue_deltas": issue_deltas,
        "metric_deltas": metric_deltas,
    }


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# 发球报告对比",
        "",
        f"- 基线视频: `{payload.get('baseline_video', '-')}`",
        f"- 对比视频: `{payload.get('target_video', '-')}`",
        f"- 基线片段数: `{payload.get('baseline_clip_count', '-')}`",
        f"- 对比片段数: `{payload.get('target_clip_count', '-')}`",
        "",
        "## 总体判断",
        "",
        payload["overall_assessment"],
        "",
        "## 问题变化",
        "",
    ]

    if payload["issue_deltas"]:
        for item in payload["issue_deltas"]:
            lines.append(
                f"- `{item['code']}`: 基线 `{item['baseline_count']}` 次，对比 `{item['target_count']}` 次，变化 `{item['delta']:+d}`"
            )
    else:
        lines.append("- 暂无问题统计")

    lines.extend(["", "## 指标变化", ""])
    if payload["metric_deltas"]:
        for item in payload["metric_deltas"]:
            if item["delta"] is None:
                lines.append(f"- `{item['name']}`: 缺少可比数据")
            else:
                lines.append(
                    f"- `{item['name']}`: 基线 `{item['baseline_value']:.3f}`，对比 `{item['target_value']:.3f}`，变化 `{item['delta']:+.3f}`。{item['comment']}"
                )
    else:
        lines.append("- 暂无指标统计")

    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare two serve report JSON files.")
    parser.add_argument("--baseline", required=True, help="Baseline serve-report.json path.")
    parser.add_argument("--target", required=True, help="Target serve-report.json path.")
    parser.add_argument("--output", help="Optional markdown output path.")
    parser.add_argument("--json-output", help="Optional JSON output path.")
    args = parser.parse_args()

    baseline_path = Path(args.baseline)
    target_path = Path(args.target)
    if not baseline_path.exists():
        raise SystemExit(f"Baseline report not found: {baseline_path}")
    if not target_path.exists():
        raise SystemExit(f"Target report not found: {target_path}")

    baseline = load_json(baseline_path)
    target = load_json(target_path)
    payload = build_payload(baseline, target)

    default_stem = f"{baseline_path.stem}-vs-{target_path.stem}"
    output_path = Path(args.output) if args.output else baseline_path.with_name(default_stem + ".md")
    json_output_path = Path(args.json_output) if args.json_output else baseline_path.with_name(default_stem + ".json")

    write_markdown(output_path, payload)
    save_json(json_output_path, payload)

    print(f"Comparison report written to: {output_path}")
    print(f"Comparison data written to: {json_output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
