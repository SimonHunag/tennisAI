param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$SessionName,

    [ValidateSet("serve", "forehand", "backhand", "forehand_slice", "backhand_slice", "volley", "other")]
    [string]$ActionType = "other",

    [string]$Date = (Get-Date -Format "yyyy-MM-dd"),

    [string]$AthleteName = "",

    [string]$AthleteId = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$safeAthleteId = $AthleteId.Trim().ToLowerInvariant()
if ([string]::IsNullOrWhiteSpace($safeAthleteId)) {
    $source = if (-not [string]::IsNullOrWhiteSpace($AthleteName)) { $AthleteName } else { "unassigned" }
    $safeAthleteId = ($source.ToLowerInvariant() -replace "[^a-z0-9]+", "-").Trim("-")
    if ([string]::IsNullOrWhiteSpace($safeAthleteId)) {
        $safeAthleteId = "unassigned"
    }
}

$actionFamily = switch ($ActionType) {
    "forehand_slice" { "forehand" }
    "backhand_slice" { "backhand" }
    default { $ActionType }
}

$sessionId = "$Date-$SessionName"
$videoDir = Join-Path $root (Join-Path "videos" (Join-Path $safeAthleteId (Join-Path $ActionType $sessionId)))
$frameDir = Join-Path $root (Join-Path "frames" (Join-Path $safeAthleteId (Join-Path $ActionType $sessionId)))
$reportDir = Join-Path $root (Join-Path "analysis" (Join-Path $safeAthleteId $ActionType))
$reportPath = Join-Path $reportDir "$sessionId.md"
$metadataPath = Join-Path $reportDir "$sessionId.json"
$templatePath = Join-Path $root (Join-Path "analysis" "template.md")
$metadataTemplatePath = Join-Path $root (Join-Path "analysis" "metadata-template.json")

if ((Test-Path -LiteralPath $reportPath) -or (Test-Path -LiteralPath $metadataPath)) {
    throw "Session '$sessionId' already exists. Choose a different SessionName or Date."
}

New-Item -ItemType Directory -Path $videoDir -Force | Out-Null
New-Item -ItemType Directory -Path $frameDir -Force | Out-Null
New-Item -ItemType Directory -Path $reportDir -Force | Out-Null

$template = Get-Content -LiteralPath $templatePath -Raw
$template = $template.Replace("{{DATE}}", $Date)
$template = $template.Replace("{{VIDEO_FILE}}", "videos/$safeAthleteId/$ActionType/$sessionId/$sessionId.mp4")
$template = $template.Replace("{{ACTION_TYPE}}", $ActionType)
$template = $template.Replace("{{REFERENCE_VIDEO}}", "")
$template = $template.Replace("{{FRAME_PATH}}", "../../../frames/$safeAthleteId/$ActionType/$sessionId/frame_001.jpg")
$template = $template.Replace("**Athlete:** ", "**Athlete:** $AthleteName")
Set-Content -LiteralPath $reportPath -Value $template -Encoding UTF8

if (-not (Test-Path -LiteralPath $metadataTemplatePath -PathType Leaf)) {
    throw "Metadata template not found: $metadataTemplatePath"
}

$metadata = Get-Content -LiteralPath $metadataTemplatePath -Raw | ConvertFrom-Json
$metadata.session_id = $sessionId
$metadata.session_name = $SessionName
$metadata.date = $Date
$metadata.athlete = $AthleteName
$metadata.athlete_id = $safeAthleteId
$metadata.action_type = $ActionType
$metadata.action_family = $actionFamily
$metadata.video_dir = "videos/$safeAthleteId/$ActionType/$sessionId"
$metadata.frame_dir = "frames/$safeAthleteId/$ActionType/$sessionId"
$metadata.report_path = "analysis/$safeAthleteId/$ActionType/$sessionId.md"
$metadata.source_video = "videos/$safeAthleteId/$ActionType/$sessionId/$sessionId.mp4"
$metadata.reference_video = ""

$metadata | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $metadataPath -Encoding UTF8

Write-Host "Created analysis session: $sessionId"
Write-Host "Video dir: $videoDir"
Write-Host "Frame dir: $frameDir"
Write-Host "Report file: $reportPath"
Write-Host "Metadata file: $metadataPath"
