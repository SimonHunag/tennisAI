#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PS_SCRIPT="$SCRIPT_DIR/start-analysis.ps1"

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  echo "Usage:"
  echo "  start-analysis.sh INPUT_VIDEO SESSION_NAME ACTION_TYPE ATHLETE_NAME ATHLETE_ID [DATE] [PROVIDER] [HANDEDNESS] [SAMPLE_EVERY] [SERVE_PRE_SECONDS] [SERVE_POST_SECONDS] [MODEL_ASSET_PATH]"
  echo
  echo "Example:"
  echo "  ./start-analysis.sh \"/d/videos/serve-1.mp4\" \"basket-serve\" \"serve\" \"Simon\" \"simon\" \"2026-03-27\" \"mediapipe\" \"right\" \"2\" \"1.4\" \"1.5\" \"assets/models/pose_landmarker.task\""
  exit 0
fi

if [[ ! -f "$PS_SCRIPT" ]]; then
  echo "Could not find $PS_SCRIPT" >&2
  exit 1
fi

INPUT_VIDEO="${1:-}"
SESSION_NAME="${2:-}"
ACTION_TYPE="${3:-}"
ATHLETE_NAME="${4:-}"
ATHLETE_ID="${5:-}"
DATE_VALUE="${6:-}"
PROVIDER="${7:-}"
HANDEDNESS="${8:-}"
SAMPLE_EVERY="${9:-}"
SERVE_PRE_SECONDS="${10:-}"
SERVE_POST_SECONDS="${11:-}"
MODEL_ASSET_PATH="${12:-}"
INTERACTIVE_MODE=0
if [[ -z "$INPUT_VIDEO" ]]; then
  INTERACTIVE_MODE=1
fi

prompt_if_empty() {
  local var_name="$1"
  local label="$2"
  local current_value="${!var_name:-}"
  if [[ -z "$current_value" ]]; then
    read -r -p "$label" current_value
    printf -v "$var_name" '%s' "$current_value"
  fi
}

if [[ -z "$INPUT_VIDEO" ]]; then
  echo
  echo "TennisAI video analysis launcher"
  echo
fi

prompt_if_empty INPUT_VIDEO "Input video path: "
prompt_if_empty SESSION_NAME "Session name: "
prompt_if_empty ACTION_TYPE "Action type: "
prompt_if_empty ATHLETE_NAME "Athlete name: "
prompt_if_empty ATHLETE_ID "Athlete id: "
if [[ "$INTERACTIVE_MODE" == "1" ]]; then
  prompt_if_empty DATE_VALUE "Date [optional]: "
  prompt_if_empty PROVIDER "Provider [optional]: "
  prompt_if_empty HANDEDNESS "Handedness [optional]: "
  prompt_if_empty SAMPLE_EVERY "Sample every [optional]: "
  prompt_if_empty SERVE_PRE_SECONDS "Serve pre seconds [optional]: "
  prompt_if_empty SERVE_POST_SECONDS "Serve post seconds [optional]: "
  prompt_if_empty MODEL_ASSET_PATH "Model asset path [optional]: "
fi

POWERSHELL_BIN="powershell"
if command -v pwsh >/dev/null 2>&1; then
  POWERSHELL_BIN="pwsh"
elif command -v powershell.exe >/dev/null 2>&1; then
  POWERSHELL_BIN="powershell.exe"
fi

cmd=(
  "$POWERSHELL_BIN"
  -NoProfile
  -ExecutionPolicy
  Bypass
  -File
  "$PS_SCRIPT"
  -InputVideo
  "$INPUT_VIDEO"
  -SessionName
  "$SESSION_NAME"
  -ActionType
  "$ACTION_TYPE"
  -AthleteName
  "$ATHLETE_NAME"
  -AthleteId
  "$ATHLETE_ID"
)

if [[ -n "$DATE_VALUE" ]]; then
  cmd+=(-Date "$DATE_VALUE")
fi
if [[ -n "$PROVIDER" ]]; then
  cmd+=(-Provider "$PROVIDER")
fi
if [[ -n "$HANDEDNESS" ]]; then
  cmd+=(-Handedness "$HANDEDNESS")
fi
if [[ -n "$SAMPLE_EVERY" ]]; then
  cmd+=(-SampleEvery "$SAMPLE_EVERY")
fi
if [[ -n "$SERVE_PRE_SECONDS" ]]; then
  cmd+=(-ServePreSeconds "$SERVE_PRE_SECONDS")
fi
if [[ -n "$SERVE_POST_SECONDS" ]]; then
  cmd+=(-ServePostSeconds "$SERVE_POST_SECONDS")
fi
if [[ -n "$MODEL_ASSET_PATH" ]]; then
  cmd+=(-ModelAssetPath "$MODEL_ASSET_PATH")
fi

echo
echo "Running analysis..."
"${cmd[@]}"
