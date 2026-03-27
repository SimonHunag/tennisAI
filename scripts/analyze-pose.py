import argparse
import json
from datetime import datetime
from math import acos, degrees, sqrt
from pathlib import Path


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def get_point(frame, name):
    return frame.get("keypoints", {}).get(name)


def valid_point(point):
    return bool(point) and point.get("confidence", 0) > 0.3


def midpoint(a, b):
    return {"x": (a["x"] + b["x"]) / 2.0, "y": (a["y"] + b["y"]) / 2.0}


def distance(a, b):
    return sqrt((a["x"] - b["x"]) ** 2 + (a["y"] - b["y"]) ** 2)


def joint_angle(a, b, c):
    ab = (a["x"] - b["x"], a["y"] - b["y"])
    cb = (c["x"] - b["x"], c["y"] - b["y"])
    ab_len = sqrt(ab[0] ** 2 + ab[1] ** 2)
    cb_len = sqrt(cb[0] ** 2 + cb[1] ** 2)
    if ab_len == 0 or cb_len == 0:
        return None
    cosine = (ab[0] * cb[0] + ab[1] * cb[1]) / (ab_len * cb_len)
    cosine = max(-1.0, min(1.0, cosine))
    return degrees(acos(cosine))


def detect_contact_frame(frames, wrist_name):
    best_index = 0
    best_y = None
    for index, frame in enumerate(frames):
        wrist = get_point(frame, wrist_name)
        if not valid_point(wrist):
            continue
        if best_y is None or wrist["y"] < best_y:
            best_y = wrist["y"]
            best_index = index
    return best_index


def signed_cross_body_offset(wrist, center, handedness):
    if wrist is None or center is None:
        return None
    if handedness == "right":
        return round(center["x"] - wrist["x"], 4)
    return round(wrist["x"] - center["x"], 4)


def estimate_metrics(pose_data):
    frames = pose_data.get("frames", [])
    handedness = pose_data.get("handedness", "right")
    wrist_name = f"{handedness}_wrist"
    shoulder_name = f"{handedness}_shoulder"
    elbow_name = f"{handedness}_elbow"
    hip_name = f"{handedness}_hip"
    knee_name = f"{handedness}_knee"
    ankle_name = f"{handedness}_ankle"

    if not frames:
        raise ValueError("Pose data contains no frames.")

    contact_index = detect_contact_frame(frames, wrist_name)
    ready_frame = frames[0]["frame_index"]
    finish_frame = frames[-1]["frame_index"]

    wrist_y_values = []
    hip_center_start = None
    hip_center_end = None
    knee_angles = []

    for index, frame in enumerate(frames):
        wrist = get_point(frame, wrist_name)
        if valid_point(wrist):
            wrist_y_values.append(wrist["y"])

        left_hip = get_point(frame, "left_hip")
        right_hip = get_point(frame, "right_hip")
        if valid_point(left_hip) and valid_point(right_hip):
            center = midpoint(left_hip, right_hip)
            if hip_center_start is None:
                hip_center_start = center
            hip_center_end = center

        shoulder = get_point(frame, shoulder_name)
        hip = get_point(frame, hip_name)
        knee = get_point(frame, knee_name)
        ankle = get_point(frame, ankle_name)
        if valid_point(shoulder) and valid_point(hip) and valid_point(knee):
            angle = joint_angle(shoulder, hip, knee)
            if angle is not None:
                knee_angles.append(angle)
        elif valid_point(hip) and valid_point(knee) and valid_point(ankle):
            angle = joint_angle(hip, knee, ankle)
            if angle is not None:
                knee_angles.append(angle)

    contact_frame = frames[contact_index]
    finish_pose_frame = frames[-1]
    contact_wrist = get_point(contact_frame, wrist_name)
    contact_elbow = get_point(contact_frame, elbow_name)
    contact_shoulder = get_point(contact_frame, shoulder_name)
    contact_hip = get_point(contact_frame, hip_name)
    left_hip = get_point(contact_frame, "left_hip")
    right_hip = get_point(contact_frame, "right_hip")
    hip_center_contact = midpoint(left_hip, right_hip) if valid_point(left_hip) and valid_point(right_hip) else None

    finish_wrist = get_point(finish_pose_frame, wrist_name)
    finish_elbow = get_point(finish_pose_frame, elbow_name)
    finish_shoulder = get_point(finish_pose_frame, shoulder_name)
    finish_left_hip = get_point(finish_pose_frame, "left_hip")
    finish_right_hip = get_point(finish_pose_frame, "right_hip")
    hip_center_finish = midpoint(finish_left_hip, finish_right_hip) if valid_point(finish_left_hip) and valid_point(finish_right_hip) else None

    contact_wrist_height = None
    contact_wrist_forward_offset = None
    contact_elbow_angle = None
    contact_shoulder_angle = None
    if valid_point(contact_wrist):
        contact_wrist_height = round(contact_wrist["y"], 4)
        if hip_center_contact is not None:
            contact_wrist_forward_offset = round(contact_wrist["x"] - hip_center_contact["x"], 4)
    if valid_point(contact_shoulder) and valid_point(contact_elbow) and valid_point(contact_wrist):
        contact_elbow_angle = joint_angle(contact_shoulder, contact_elbow, contact_wrist)
        if contact_elbow_angle is not None:
            contact_elbow_angle = round(contact_elbow_angle, 2)
    if valid_point(contact_hip) and valid_point(contact_shoulder) and valid_point(contact_wrist):
        contact_shoulder_angle = joint_angle(contact_hip, contact_shoulder, contact_wrist)
        if contact_shoulder_angle is not None:
            contact_shoulder_angle = round(contact_shoulder_angle, 2)

    hip_shift = None
    if hip_center_start is not None and hip_center_end is not None:
        hip_shift = round(hip_center_end["x"] - hip_center_start["x"], 4)

    average_knee_flexion = round(sum(knee_angles) / len(knee_angles), 2) if knee_angles else None
    wrist_vertical_range = round(max(wrist_y_values) - min(wrist_y_values), 4) if wrist_y_values else None
    finish_elbow_angle = None
    finish_wrist_shoulder_offset = None
    follow_through_drop = None
    finish_cross_body_offset = None
    if valid_point(finish_shoulder) and valid_point(finish_elbow) and valid_point(finish_wrist):
        finish_elbow_angle = joint_angle(finish_shoulder, finish_elbow, finish_wrist)
        if finish_elbow_angle is not None:
            finish_elbow_angle = round(finish_elbow_angle, 2)
    if valid_point(finish_wrist) and valid_point(finish_shoulder):
        finish_wrist_shoulder_offset = round(finish_wrist["y"] - finish_shoulder["y"], 4)
    if valid_point(contact_wrist) and valid_point(finish_wrist):
        follow_through_drop = round(finish_wrist["y"] - contact_wrist["y"], 4)
    if valid_point(finish_wrist) and hip_center_finish is not None:
        finish_cross_body_offset = signed_cross_body_offset(finish_wrist, hip_center_finish, handedness)

    return {
        "phases": {
            "ready_frame": ready_frame,
            "contact_frame": frames[contact_index]["frame_index"],
            "finish_frame": finish_frame,
        },
        "metrics": {
            "contact_wrist_height": contact_wrist_height,
            "contact_wrist_forward_offset": contact_wrist_forward_offset,
            "contact_elbow_angle": contact_elbow_angle,
            "contact_shoulder_angle": contact_shoulder_angle,
            "hip_shift": hip_shift,
            "average_knee_flexion": average_knee_flexion,
            "wrist_vertical_range": wrist_vertical_range,
            "finish_elbow_angle": finish_elbow_angle,
            "finish_wrist_shoulder_offset": finish_wrist_shoulder_offset,
            "follow_through_drop": follow_through_drop,
            "finish_cross_body_offset": finish_cross_body_offset,
        },
    }


def add_issue(issues, code, severity, message, recommendations):
    issues.append(
        {
            "issue_code": code,
            "severity": severity,
            "message": message,
            "recommendations": recommendations,
        }
    )


def evaluate_serve(metrics):
    issues = []
    strengths = []
    next_focus = []

    height = metrics.get("contact_wrist_height")
    forward = metrics.get("contact_wrist_forward_offset")
    elbow_angle = metrics.get("contact_elbow_angle")
    shoulder_angle = metrics.get("contact_shoulder_angle")
    hip_shift = metrics.get("hip_shift")
    knee = metrics.get("average_knee_flexion")
    follow_through_drop = metrics.get("follow_through_drop")
    finish_cross_body_offset = metrics.get("finish_cross_body_offset")

    if height is not None and height > 0.28:
        add_issue(issues, 'low_contact_point', 'medium', 'Contact height looks low for a serve.', [
            'Reach higher through contact.',
            'Stabilize the toss so the ball stays above the hitting shoulder longer.',
            'Pause at trophy position and rehearse upward extension.'
        ])
        next_focus.append('Raise contact point.')
    else:
        strengths.append('Contact height is within a useful serve range.')

    if forward is not None and forward < 0.03:
        add_issue(issues, 'contact_too_far_back', 'medium', 'The contact point appears too close to or behind the hip line.', [
            'Place the toss slightly more in front.',
            'Start the upward swing earlier.',
            'Check if the shoulders open too late before contact.'
        ])
        next_focus.append('Move contact slightly more in front.')
    else:
        strengths.append('Contact point is reasonably forward of the hips.')

    if hip_shift is not None and hip_shift < 0.03:
        add_issue(issues, 'limited_weight_transfer', 'medium', 'Forward hip shift is limited during the serve.', [
            'Drive the hips forward before contact.',
            'Practice stepping into the court after the toss.',
            'Use shadow serves to exaggerate weight transfer.'
        ])
        next_focus.append('Improve forward hip shift.')
    else:
        strengths.append('Hip shift suggests useful forward momentum.')

    if knee is not None and knee > 155:
        add_issue(issues, 'limited_leg_drive', 'low', 'Leg loading looks shallow, which may reduce upward drive.', [
            'Allow a deeper knee bend before the upward swing.',
            'Practice loading and exploding upward without hitting a ball.',
            'Check balance before the toss to avoid staying too upright.'
        ])
        next_focus.append('Add more leg drive.')

    if elbow_angle is not None and elbow_angle < 150:
        add_issue(issues, 'contact_arm_not_extended', 'medium', 'The hitting arm looks too bent at contact.', [
            'Reach into contact with a longer hitting arm.',
            'Use shadow serves to feel the elbow extending up to the ball.',
            'Check whether the toss location is forcing the arm to stay cramped.'
        ])
        next_focus.append('Extend the hitting arm more at contact.')
    else:
        strengths.append('Arm extension at contact looks reasonably complete.')

    if shoulder_angle is not None and shoulder_angle < 100:
        add_issue(issues, 'contact_angle_too_closed', 'medium', 'Shoulder-to-arm angle at contact looks closed.', [
            'Reach up and out instead of contacting too close to the head.',
            'Let the chest rise more before contact.',
            'Use pause drills at trophy position and rehearse an upward strike path.'
        ])
        next_focus.append('Open the shoulder-arm angle at contact.')
    else:
        strengths.append('Contact angle suggests a useful upward hitting line.')

    if follow_through_drop is not None and follow_through_drop < 0.08:
        add_issue(issues, 'incomplete_follow_through', 'low', 'The follow-through looks short after contact.', [
            'Let the arm continue naturally after contact instead of stopping the swing early.',
            'Practice full shadow serves with a complete finish.',
            'Check whether tension in the shoulder is cutting off the finish.'
        ])
        next_focus.append('Finish the serve with a fuller follow-through.')
    else:
        strengths.append('Follow-through drops naturally after contact.')

    if finish_cross_body_offset is not None and finish_cross_body_offset < 0.02:
        add_issue(issues, 'finish_not_across_body', 'low', 'The finish does not travel clearly across the body.', [
            'Allow the arm and racket path to continue across after contact.',
            'Avoid trying to stop the motion right after hitting.',
            'Film a few relaxed shadow serves and compare the finish position.'
        ])
        next_focus.append('Let the finish travel more across the body.')
    else:
        strengths.append('Finish position travels across the body with useful flow.')

    return issues, strengths, next_focus


def evaluate_forehand(metrics):
    issues = []
    strengths = []
    next_focus = []

    forward = metrics.get("contact_wrist_forward_offset")
    hip_shift = metrics.get("hip_shift")
    wrist_range = metrics.get("wrist_vertical_range")

    if forward is not None and forward < 0.02:
        add_issue(issues, 'late_contact', 'medium', 'The hitting hand is not far enough in front at contact.', [
            'Prepare earlier on the unit turn.',
            'Meet the ball farther in front of the body.',
            'Use slow shadow swings to lock in the contact point.'
        ])
        next_focus.append('Move contact point forward.')
    else:
        strengths.append('Contact point is reasonably in front of the body.')

    if hip_shift is not None and hip_shift < 0.02:
        add_issue(issues, 'limited_weight_transfer', 'medium', 'Hip movement suggests limited weight transfer through the shot.', [
            'Push from the back leg into the front leg.',
            'Avoid hitting only with the arm.',
            'Train step-in forehands with a clear finish.'
        ])
        next_focus.append('Transfer weight more clearly.')
    else:
        strengths.append('Hip movement supports the stroke through contact.')

    if wrist_range is not None and wrist_range < 0.08:
        add_issue(issues, 'small_swing_range', 'low', 'The swing path looks compact and may be cutting off follow-through.', [
            'Allow a fuller follow-through.',
            'Relax the hitting arm after contact.',
            'Film a few shadow swings and compare the finish position.'
        ])
        next_focus.append('Increase swing range.')

    return issues, strengths, next_focus


def evaluate_backhand(metrics):
    issues = []
    strengths = []
    next_focus = []

    forward = metrics.get("contact_wrist_forward_offset")
    hip_shift = metrics.get("hip_shift")
    wrist_range = metrics.get("wrist_vertical_range")

    if forward is not None and forward < 0.015:
        add_issue(issues, "late_contact", "medium", "Backhand contact looks too close to the body.", [
            "Prepare the shoulders earlier.",
            "Meet the ball farther in front of the front hip.",
            "Use shadow swings to lock in a clearer contact point."
        ])
        next_focus.append("Move backhand contact farther in front.")
    else:
        strengths.append("Backhand contact point is reasonably in front.")

    if hip_shift is not None and hip_shift < 0.02:
        add_issue(issues, "limited_rotation_transfer", "medium", "Body rotation and weight transfer look limited on the backhand.", [
            "Drive from the outside leg into the shot.",
            "Rotate the trunk through contact instead of arming the swing.",
            "Finish with the chest more open to the target."
        ])
        next_focus.append("Increase trunk rotation through contact.")
    else:
        strengths.append("Hip movement supports the backhand stroke.")

    if wrist_range is not None and wrist_range < 0.07:
        add_issue(issues, "short_follow_through", "low", "The backhand follow-through appears compact.", [
            "Let the finish travel farther through the ball.",
            "Keep the hitting side relaxed after contact.",
            "Film slow shadow backhands and compare the finish height."
        ])
        next_focus.append("Lengthen the backhand follow-through.")

    return issues, strengths, next_focus


def evaluate_volley(metrics):
    issues = []
    strengths = []
    next_focus = []

    forward = metrics.get("contact_wrist_forward_offset")
    hip_shift = metrics.get("hip_shift")
    wrist_range = metrics.get("wrist_vertical_range")

    if forward is not None and forward < 0.025:
        add_issue(issues, "late_contact", "medium", "Volley contact looks slightly late.", [
            "Catch the ball earlier in front of the body.",
            "Keep the racket head set before the split step lands.",
            "Practice compact block volleys with a fixed contact point."
        ])
        next_focus.append("Contact the volley earlier in front.")
    else:
        strengths.append("Volley contact point is reasonably forward.")

    if hip_shift is not None and hip_shift < 0.015:
        add_issue(issues, "limited_forward_move", "low", "There is limited body movement through the volley.", [
            "Step through the volley with better momentum.",
            "Avoid staying flat-footed at contact.",
            "Use split-step to first-step drills before volley feeds."
        ])
        next_focus.append("Move the body forward through the volley.")
    else:
        strengths.append("Body movement supports the volley well.")

    if wrist_range is not None and wrist_range > 0.18:
        add_issue(issues, "too_much_swing", "medium", "Volley swing range appears too large.", [
            "Keep the volley motion compact.",
            "Use the shoulder and body instead of adding extra hand swing.",
            "Think block and guide instead of swing."
        ])
        next_focus.append("Compact the volley swing.")
    else:
        strengths.append("Volley swing range stays compact.")

    return issues, strengths, next_focus


def slice_pose_data(pose_data, frame_start=None, frame_end=None):
    frames = pose_data.get("frames", [])
    sliced_frames = []

    for frame in frames:
        frame_index = frame.get("frame_index", 0)
        if frame_start is not None and frame_index < frame_start:
            continue
        if frame_end is not None and frame_index > frame_end:
            continue
        sliced_frames.append(frame)

    if not sliced_frames:
        raise ValueError("No frames remain after applying the requested frame range.")

    sliced = dict(pose_data)
    sliced["frames"] = sliced_frames
    return sliced


def build_analysis(pose_data):
    result = estimate_metrics(pose_data)
    action_type = pose_data.get("action_type", "other")
    metrics = result["metrics"]
    normalized_action_type = action_type
    if action_type == "forehand_slice":
        normalized_action_type = "forehand"
    elif action_type == "backhand_slice":
        normalized_action_type = "backhand"

    if normalized_action_type == "serve":
        issues, strengths, next_focus = evaluate_serve(metrics)
    elif normalized_action_type == "forehand":
        issues, strengths, next_focus = evaluate_forehand(metrics)
    elif normalized_action_type == "backhand":
        issues, strengths, next_focus = evaluate_backhand(metrics)
    elif normalized_action_type == "volley":
        issues, strengths, next_focus = evaluate_volley(metrics)
    else:
        issues = []
        strengths = []
        next_focus = ['No rule set yet for this action type.']

    return {
        "session_id": pose_data.get("session_id", ""),
        "action_type": action_type,
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "phases": result["phases"],
        "metrics": metrics,
        "issues": issues,
        "strengths": strengths,
        "next_focus": next_focus,
    }


def main():
    parser = argparse.ArgumentParser(description="Analyze pose keypoints and generate rule-based tennis feedback.")
    parser.add_argument("--input", required=True, help="Path to a pose JSON file.")
    parser.add_argument("--output", help="Path to the analysis JSON file.")
    parser.add_argument("--frame-start", type=int, help="Optional starting frame index for segment analysis.")
    parser.add_argument("--frame-end", type=int, help="Optional ending frame index for segment analysis.")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise SystemExit(f"Input pose file was not found: {input_path}")

    output_path = Path(args.output) if args.output else input_path.with_name(input_path.stem.replace("-pose", "") + "-analysis.json")
    pose_data = load_json(input_path)
    pose_data = slice_pose_data(pose_data, args.frame_start, args.frame_end)
    analysis = build_analysis(pose_data)
    if args.frame_start is not None or args.frame_end is not None:
        analysis["source_frame_range"] = {
            "frame_start": args.frame_start if args.frame_start is not None else pose_data["frames"][0]["frame_index"],
            "frame_end": args.frame_end if args.frame_end is not None else pose_data["frames"][-1]["frame_index"],
        }
    save_json(output_path, analysis)
    print(f"Analysis written to: {output_path}")


if __name__ == "__main__":
    main()
