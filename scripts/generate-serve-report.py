#!/usr/bin/env python3
"""Generate a readable Chinese markdown report for multi-clip serve analysis."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any


ISSUE_LABELS = {
    "low_contact_point": "击球点偏低",
    "contact_too_far_back": "击球点偏靠后",
    "limited_weight_transfer": "重心前送不足",
    "limited_leg_drive": "蹬地发力不足",
    "contact_arm_not_extended": "击球时手臂伸展不足",
    "contact_angle_too_closed": "击球角度偏收",
    "incomplete_follow_through": "收拍不完整",
    "finish_not_across_body": "收拍没有自然过身",
}

ISSUE_EXPLANATIONS = {
    "low_contact_point": "触球时手臂向上延伸不够，容易让发球高度和压迫感下降。",
    "contact_too_far_back": "击球发生在身体侧后方，容易导致发力传递不顺和控球不稳定。",
    "limited_weight_transfer": "身体没有明显向前送入场内，力量链条会断在中段。",
    "limited_leg_drive": "屈膝加载和向上蹬伸不够，发球会更像手臂在打。",
    "contact_arm_not_extended": "触球瞬间手臂没有充分伸展，会限制击球高度和力量释放。",
    "contact_angle_too_closed": "击球时肩臂夹角偏小，容易让击球线路偏挤、向上发力不充分。",
    "incomplete_follow_through": "击球后收拍过早停止，动作链条容易断掉。",
    "finish_not_across_body": "收拍没有自然走到身体对侧，说明随挥流动性不足。",
}

ISSUE_TRAINING = {
    "low_contact_point": "先练抛球后向上完全伸展，宁可先慢一点，也要把触球点抬高。",
    "contact_too_far_back": "把抛球放到身体前上方一点，并提前启动上挥，让击球发生在身体前方。",
    "limited_weight_transfer": "做无球影子发球，刻意把髋部和身体重心送进场内。",
    "limited_leg_drive": "单独练屈膝加载和蹬伸，建立从下往上的发力顺序。",
    "contact_arm_not_extended": "多做向上够球的影子发球，建立击球瞬间完整伸臂的感觉。",
    "contact_angle_too_closed": "练习抛球后向上向前击球，打开肩臂夹角，不要把球挤在头顶旁边。",
    "incomplete_follow_through": "练习完整随挥，不要击球后立刻刹车。",
    "finish_not_across_body": "让收拍自然走到对侧，建立更完整的动作收尾。",
}

STRENGTH_TRANSLATIONS = {
    "Contact height is within a useful serve range.": "击球高度整体还在可用范围内。",
    "Contact point is reasonably forward of the hips.": "击球点相对髋部的位置还算靠前。",
    "Hip shift suggests useful forward momentum.": "髋部前送有一定基础，说明向前发力并不是完全缺失。",
    "Arm extension at contact looks reasonably complete.": "击球瞬间手臂伸展还算完整。",
    "Contact angle suggests a useful upward hitting line.": "击球角度整体有一定向上击打的基础。",
    "Follow-through drops naturally after contact.": "击球后的下落和随挥还算自然。",
    "Finish position travels across the body with useful flow.": "收拍有一定过身流动性。",
}

FOCUS_TRANSLATIONS = {
    "Raise contact point.": "优先抬高击球点。",
    "Move contact slightly more in front.": "把击球点再放到身体更前方。",
    "Improve forward hip shift.": "增强髋部和重心向前的输送。",
    "Add more leg drive.": "补足屈膝加载和向上蹬地。",
    "Extend the hitting arm more at contact.": "击球时把手臂伸得更完整。",
    "Open the shoulder-arm angle at contact.": "打开击球时的肩臂夹角。",
    "Finish the serve with a fuller follow-through.": "把收拍做完整。",
    "Let the finish travel more across the body.": "让收拍更自然地过身。",
}


@dataclass
class ClipReport:
    clip_id: str
    time_start: float
    time_end: float
    duration_seconds: float
    metrics: dict[str, Any]
    issue_codes: list[str]
    strengths: list[str]
    next_focus: list[str]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def format_seconds(value: float) -> str:
    minutes = int(value // 60)
    seconds = value - minutes * 60
    if minutes:
        return f"{minutes}:{seconds:04.1f}"
    return f"{seconds:.1f}s"


def format_metric(name: str, value: Any) -> str:
    if value is None:
        return "未稳定识别"
    if name in {"contact_wrist_height", "contact_wrist_forward_offset", "hip_shift", "wrist_vertical_range", "finish_wrist_shoulder_offset", "follow_through_drop", "finish_cross_body_offset"}:
        return f"{value:.3f}"
    if name in {"average_knee_flexion", "contact_elbow_angle", "contact_shoulder_angle", "finish_elbow_angle"}:
        return f"{value:.1f}"
    return str(value)


def translate_strength(text: str) -> str:
    return STRENGTH_TRANSLATIONS.get(text, text).rstrip(".。 ")


def translate_focus(text: str) -> str:
    return FOCUS_TRANSLATIONS.get(text, text).rstrip(".。 ")


def build_overall_assessment(issue_counter: Counter[str]) -> str:
    if not issue_counter:
        return "这组发球暂时没有命中明显的规则问题，但仍建议结合视频做人工复核。"

    top_issue, top_count = issue_counter.most_common(1)[0]
    label = ISSUE_LABELS.get(top_issue, top_issue)
    if top_count >= 4:
        return f"这组发球里最稳定暴露的问题是“{label}”，已经在大多数片段中重复出现，值得优先处理。"
    if top_count >= 2:
        return f"这组发球里最常见的问题是“{label}”，但不同片段之间还有一定波动。"
    return "这组发球的问题分布比较分散，建议优先结合最差片段做针对性修正。"


def choose_training_priorities(issue_counter: Counter[str]) -> list[str]:
    ordered = [code for code, _ in issue_counter.most_common(3)]
    return [ISSUE_TRAINING[code] for code in ordered if code in ISSUE_TRAINING]


def build_report_payload(batch_data: dict[str, Any]) -> dict[str, Any]:
    clip_reports: list[ClipReport] = []
    issue_counter: Counter[str] = Counter()
    focus_counter: Counter[str] = Counter()
    strength_counter: Counter[str] = Counter()
    metric_values: dict[str, list[float]] = defaultdict(list)

    for clip in batch_data["clips"]:
        analysis_path = Path(clip["analysis_json"])
        analysis_data = load_json(analysis_path)
        issue_codes = [item.get("issue_code") for item in analysis_data.get("issues", []) if item.get("issue_code")]
        for code in issue_codes:
            issue_counter[code] += 1
        for text in analysis_data.get("next_focus", []):
            focus_counter[translate_focus(text)] += 1
        for text in analysis_data.get("strengths", []):
            strength_counter[translate_strength(text)] += 1
        for key, value in analysis_data.get("metrics", {}).items():
            if value is not None:
                metric_values[key].append(value)

        clip_reports.append(
            ClipReport(
                clip_id=clip["clip_id"],
                time_start=clip["time_start"],
                time_end=clip["time_end"],
                duration_seconds=clip["duration_seconds"],
                metrics=analysis_data.get("metrics", {}),
                issue_codes=issue_codes,
                strengths=analysis_data.get("strengths", []),
                next_focus=analysis_data.get("next_focus", []),
            )
        )

    metric_order = [
        "contact_wrist_height",
        "contact_wrist_forward_offset",
        "contact_elbow_angle",
        "contact_shoulder_angle",
        "hip_shift",
        "average_knee_flexion",
        "wrist_vertical_range",
        "finish_elbow_angle",
        "finish_wrist_shoulder_offset",
        "follow_through_drop",
        "finish_cross_body_offset",
    ]

    return {
        "video_file": batch_data["video_file"],
        "provider": batch_data.get("provider", "unknown"),
        "clip_count": batch_data["clip_count"],
        "overall_assessment": build_overall_assessment(issue_counter),
        "common_issues": [
            {
                "code": code,
                "label": ISSUE_LABELS.get(code, code),
                "count": count,
                "explanation": ISSUE_EXPLANATIONS.get(code, ""),
                "training": ISSUE_TRAINING.get(code, ""),
            }
            for code, count in issue_counter.most_common()
        ],
        "priority_focus": [
            {"name": text, "count": count}
            for text, count in focus_counter.most_common(3)
        ],
        "training_priorities": choose_training_priorities(issue_counter),
        "strengths": [
            {"name": text, "count": count}
            for text, count in strength_counter.most_common(3)
        ],
        "metric_overview": [
            {"name": key, "average": round(mean(metric_values[key]), 3)}
            for key in metric_order
            if metric_values.get(key)
        ],
        "clips": [
            {
                "clip_id": clip.clip_id,
                "time_start": clip.time_start,
                "time_end": clip.time_end,
                "duration_seconds": clip.duration_seconds,
                "issues": [
                    {"code": code, "label": ISSUE_LABELS.get(code, code)}
                    for code in clip.issue_codes
                ],
                "next_focus": [translate_focus(text) for text in clip.next_focus],
                "strengths": [translate_strength(text) for text in clip.strengths],
                "metrics": clip.metrics,
            }
            for clip in clip_reports
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a Chinese markdown report from multi-clip serve analysis."
    )
    parser.add_argument(
        "--batch-analysis",
        required=True,
        help="Path to the batch analysis JSON generated by process-serve-video.py.",
    )
    parser.add_argument(
        "--output",
        help="Optional markdown output path. Defaults to analysis/<video>-serve-report.md",
    )
    parser.add_argument(
        "--json-output",
        help="Optional JSON output path. Defaults to analysis/<video>-serve-report.json",
    )
    args = parser.parse_args()

    batch_path = Path(args.batch_analysis)
    batch_data = load_json(batch_path)
    if not batch_data.get("clips"):
        raise SystemExit("Batch analysis file does not contain any clips.")

    output_path = (
        Path(args.output)
        if args.output
        else batch_path.with_name(batch_path.stem.replace("-batch-analysis", "") + "-serve-report.md")
    )
    json_output_path = (
        Path(args.json_output)
        if args.json_output
        else batch_path.with_name(batch_path.stem.replace("-batch-analysis", "") + "-serve-report.json")
    )
    report_payload = build_report_payload(batch_data)
    clip_reports = [
        ClipReport(
            clip_id=item["clip_id"],
            time_start=item["time_start"],
            time_end=item["time_end"],
            duration_seconds=item["duration_seconds"],
            metrics=item["metrics"],
            issue_codes=[issue["code"] for issue in item["issues"]],
            strengths=item["strengths"],
            next_focus=item["next_focus"],
        )
        for item in report_payload["clips"]
    ]
    issue_counter = Counter({item["code"]: item["count"] for item in report_payload["common_issues"]})
    focus_counter = Counter({item["name"]: item["count"] for item in report_payload["priority_focus"]})
    strength_counter = Counter({item["name"]: item["count"] for item in report_payload["strengths"]})
    metric_overview = {item["name"]: item["average"] for item in report_payload["metric_overview"]}

    lines: list[str] = []
    lines.append("# 发球视频自动分析报告")
    lines.append("")
    lines.append(f"- 原始视频: `{batch_data['video_file']}`")
    lines.append(f"- 分析模型: `{batch_data.get('provider', 'unknown')}`")
    lines.append(f"- 识别片段数: `{batch_data['clip_count']}`")
    lines.append("")
    lines.append("## 整体判断")
    lines.append("")
    lines.append(report_payload["overall_assessment"])
    lines.append("")

    if issue_counter:
        lines.append("## 共性问题")
        lines.append("")
        for code, count in issue_counter.most_common():
            label = ISSUE_LABELS.get(code, code)
            explanation = ISSUE_EXPLANATIONS.get(code, "")
            lines.append(f"- `{label}`: 出现 `{count}` 次。{explanation}")
        lines.append("")

    if focus_counter:
        lines.append("## 优先调整")
        lines.append("")
        for text, count in focus_counter.most_common(3):
            lines.append(f"- {text} 出现 `{count}` 次，建议优先练。")
        lines.append("")

    if report_payload["training_priorities"]:
        lines.append("## 训练建议")
        lines.append("")
        for item in report_payload["training_priorities"]:
            lines.append(f"- {item}")
        lines.append("")

    if strength_counter:
        lines.append("## 当前基础")
        lines.append("")
        for text, count in strength_counter.most_common(3):
            lines.append(f"- {text} 出现 `{count}` 次。")
        lines.append("")

    if metric_overview:
        lines.append("## 指标概览")
        lines.append("")
        for key, value in metric_overview.items():
            lines.append(f"- `{key}` 平均值: `{value:.3f}`")
        lines.append("")

    lines.append("## 分段结果")
    lines.append("")
    for clip in clip_reports:
        lines.append(f"### {clip.clip_id}")
        lines.append("")
        lines.append(
            f"- 时间范围: `{format_seconds(clip.time_start)} - {format_seconds(clip.time_end)}`，时长 `{clip.duration_seconds:.1f}s`"
        )
        if clip.issue_codes:
            labels = "，".join(ISSUE_LABELS.get(code, code) for code in clip.issue_codes)
            lines.append(f"- 命中问题: {labels}")
        else:
            lines.append("- 命中问题: 暂未识别到明确规则问题")
        if clip.next_focus:
            focus_text = "，".join(translate_focus(text) for text in clip.next_focus)
            lines.append(f"- 下次重点: {focus_text}")
        if clip.strengths:
            strengths = "，".join(translate_strength(text) for text in clip.strengths)
            lines.append(f"- 相对较好: {strengths}")
        lines.append("- 关键指标:")
        for key in [
            "contact_wrist_height",
            "contact_wrist_forward_offset",
            "contact_elbow_angle",
            "contact_shoulder_angle",
            "hip_shift",
            "average_knee_flexion",
            "wrist_vertical_range",
            "finish_elbow_angle",
            "finish_wrist_shoulder_offset",
            "follow_through_drop",
            "finish_cross_body_offset",
        ]:
            lines.append(f"  - `{key}`: `{format_metric(key, clip.metrics.get(key))}`")
        lines.append("")

    output_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    json_output_path.write_text(json.dumps(report_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Serve report written to: {output_path}")
    print(f"Serve report data written to: {json_output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
