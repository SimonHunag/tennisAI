param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$InputVideo,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$SessionName,

    [Parameter(Mandatory = $true)]
    [ValidateSet("serve", "forehand", "backhand", "forehand_slice", "backhand_slice", "volley", "other")]
    [string]$ActionType,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$AthleteName,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$AthleteId,

    [string]$Date = (Get-Date -Format "yyyy-MM-dd"),

    [ValidateSet("mediapipe", "stub")]
    [string]$Provider = "mediapipe",

    [ValidateSet("right", "left")]
    [string]$Handedness = "right",

    [int]$SampleEvery = 2,

    [double]$ServePreSeconds = 1.4,

    [double]$ServePostSeconds = 1.5,

    [string]$ModelAssetPath = "assets/models/pose_landmarker.task"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Invoke-Step {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Label,
        [Parameter(Mandatory = $true)]
        [string[]]$Command
    )

    Write-Host ""
    Write-Host "==> $Label"
    & $Command[0] $Command[1..($Command.Count - 1)]
    if ($LASTEXITCODE -ne 0) {
        throw "Step failed: $Label"
    }
}

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [string]$Content
    )

    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Content, $utf8NoBom)
}

function Run-SingleVideoPipeline {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Root,
        [Parameter(Mandatory = $true)]
        [string]$VideoPath,
        [Parameter(Mandatory = $true)]
        [string]$ActionType,
        [Parameter(Mandatory = $true)]
        [string]$Provider,
        [Parameter(Mandatory = $true)]
        [string]$Handedness,
        [Parameter(Mandatory = $true)]
        [int]$SampleEvery,
        [Parameter(Mandatory = $true)]
        [string]$ArtifactDir,
        [string]$ModelAssetPath
    )

    $sessionId = [System.IO.Path]::GetFileNameWithoutExtension($VideoPath)
    $poseOutput = Join-Path $ArtifactDir "$sessionId-pose.json"
    $analysisOutput = Join-Path $ArtifactDir "$sessionId-analysis.json"

    $pipelineCommand = @(
        "python",
        (Join-Path $Root "scripts/run-analysis-pipeline.py"),
        "--input-video",
        $VideoPath,
        "--provider",
        $Provider,
        "--action-type",
        $ActionType,
        "--handedness",
        $Handedness,
        "--sample-every",
        $SampleEvery.ToString(),
        "--pose-output",
        $poseOutput,
        "--analysis-output",
        $analysisOutput,
        "--skip-summary"
    )
    if (-not [string]::IsNullOrWhiteSpace($ModelAssetPath)) {
        $pipelineCommand += @("--model-asset-path", $ModelAssetPath)
    }
    Invoke-Step -Label "Running single-video analysis" -Command $pipelineCommand
}

function Update-MetadataFromServeReport {
    param(
        [Parameter(Mandatory = $true)]
        [pscustomobject]$Metadata,
        [Parameter(Mandatory = $true)]
        [string]$ServeReportJson,
        [Parameter(Mandatory = $true)]
        [string]$ServeReportMd,
        [Parameter(Mandatory = $true)]
        [string]$MetadataPath,
        [Parameter(Mandatory = $true)]
        [string]$Root
    )

    $report = Get-Content -LiteralPath $ServeReportJson -Raw -Encoding UTF8 | ConvertFrom-Json
    $Metadata.focus_points = @($report.priority_focus | ForEach-Object { $_.name })
    $Metadata.strengths = @($report.strengths | ForEach-Object { $_.name })
    $Metadata.issues = @($report.common_issues | ForEach-Object { $_.label })
    $Metadata.next_steps = @($report.training_priorities)
    $Metadata.report_path = $ServeReportMd.Substring($Root.Length + 1).Replace("\", "/")
    $Metadata | ConvertTo-Json -Depth 8 | ForEach-Object {
        Write-Utf8NoBom -Path $MetadataPath -Content ($_ + [Environment]::NewLine)
    }
}

$root = Split-Path -Parent $PSScriptRoot
$resolvedInputVideo = (Resolve-Path -LiteralPath $InputVideo).Path
$inputVideoInfo = Get-Item -LiteralPath $resolvedInputVideo
$sessionId = "$Date-$SessionName"

$sessionVideoDir = Join-Path $root (Join-Path "videos" (Join-Path $AthleteId (Join-Path $ActionType $sessionId)))
$sessionAnalysisRoot = Join-Path $root (Join-Path "analysis" (Join-Path $AthleteId $ActionType))
$sessionArtifactDir = Join-Path $sessionAnalysisRoot $sessionId
$metadataPath = Join-Path $sessionAnalysisRoot "$sessionId.json"
$targetVideoPath = Join-Path $sessionVideoDir ($sessionId + $inputVideoInfo.Extension.ToLowerInvariant())
$relativeTargetVideo = $targetVideoPath.Substring($root.Length + 1).Replace("\", "/")

if (-not (Test-Path -LiteralPath $metadataPath -PathType Leaf)) {
    Invoke-Step -Label "Creating session scaffold" -Command @(
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        (Join-Path $root "scripts/new-analysis-session.ps1"),
        "-SessionName",
        $SessionName,
        "-ActionType",
        $ActionType,
        "-AthleteName",
        $AthleteName,
        "-AthleteId",
        $AthleteId,
        "-Date",
        $Date
    )
}

New-Item -ItemType Directory -Path $sessionVideoDir -Force | Out-Null
New-Item -ItemType Directory -Path $sessionArtifactDir -Force | Out-Null
Copy-Item -LiteralPath $resolvedInputVideo -Destination $targetVideoPath -Force

$metadata = Get-Content -LiteralPath $metadataPath -Raw -Encoding UTF8 | ConvertFrom-Json
$metadata.source_video = $relativeTargetVideo
$metadata.video_dir = $sessionVideoDir.Substring($root.Length + 1).Replace("\", "/")
$metadata.report_path = if ($ActionType -eq "serve") {
    "analysis/$AthleteId/$ActionType/$sessionId/$sessionId-serve-report.md"
}
else {
    $metadata.report_path
}
$metadata | ConvertTo-Json -Depth 8 | ForEach-Object {
    Write-Utf8NoBom -Path $metadataPath -Content ($_ + [Environment]::NewLine)
}

if ($Provider -eq "mediapipe") {
    $resolvedModelPath = Join-Path $root $ModelAssetPath
    if (-not (Test-Path -LiteralPath $resolvedModelPath -PathType Leaf)) {
        throw "Model file not found: $resolvedModelPath"
    }
}

if ($ActionType -eq "serve") {
    $clipsJson = Join-Path $sessionArtifactDir "$sessionId-clips.json"
    $fullPoseJson = Join-Path $sessionArtifactDir "$sessionId-full-pose.json"
    $poseSegmentsJson = Join-Path $sessionArtifactDir "$sessionId-pose-segments.json"
    $batchJson = Join-Path $sessionArtifactDir "$sessionId-batch-analysis.json"
    $serveReportMd = Join-Path $sessionArtifactDir "$sessionId-serve-report.md"
    $serveReportJson = Join-Path $sessionArtifactDir "$sessionId-serve-report.json"
    $clipsDir = Join-Path $sessionVideoDir "clips"
    $poseClipsDir = Join-Path $sessionVideoDir "pose-clips"
    $poseAnalysisDir = Join-Path $sessionArtifactDir "pose-clips"
    $usedPoseSegmentation = $false

    if ($Provider -eq "mediapipe") {
        Invoke-Step -Label "Extracting full-video pose for serve segmentation" -Command @(
            "python",
            (Join-Path $root "scripts/extract-pose.py"),
            "--input-video",
            $targetVideoPath,
            "--output",
            $fullPoseJson,
            "--provider",
            $Provider,
            "--model-asset-path",
            $resolvedModelPath,
            "--action-type",
            "serve",
            "--handedness",
            $Handedness,
            "--sample-every",
            $SampleEvery.ToString()
        )

        Invoke-Step -Label "Detecting pose-based serve segments" -Command @(
            "python",
            (Join-Path $root "scripts/detect-serve-segments.py"),
            "--input",
            $fullPoseJson,
            "--output",
            $poseSegmentsJson,
            "--action-type",
            "serve",
            "--pre-seconds",
            $ServePreSeconds.ToString([System.Globalization.CultureInfo]::InvariantCulture),
            "--post-seconds",
            $ServePostSeconds.ToString([System.Globalization.CultureInfo]::InvariantCulture)
        )

        $poseSegmentsData = Get-Content -LiteralPath $poseSegmentsJson -Raw -Encoding UTF8 | ConvertFrom-Json
        if (@($poseSegmentsData.segments).Count -gt 0) {
            Invoke-Step -Label "Running pose-segment serve analysis" -Command @(
                "python",
                (Join-Path $root "scripts/process-serve-pose-segments.py"),
                "--video",
                $targetVideoPath,
                "--pose",
                $fullPoseJson,
                "--segments",
                $poseSegmentsJson,
                "--clips-dir",
                $poseClipsDir,
                "--analysis-dir",
                $poseAnalysisDir
            )

            $batchJson = Join-Path $poseAnalysisDir "$sessionId-poseclip-batch-analysis.json"
            Invoke-Step -Label "Generating serve report" -Command @(
                "python",
                (Join-Path $root "scripts/generate-serve-report.py"),
                "--batch-analysis",
                $batchJson,
                "--output",
                $serveReportMd,
                "--json-output",
                $serveReportJson
            )

            Update-MetadataFromServeReport -Metadata $metadata -ServeReportJson $serveReportJson -ServeReportMd $serveReportMd -MetadataPath $metadataPath -Root $root
            $usedPoseSegmentation = $true
        }
    }

    if (-not $usedPoseSegmentation) {

        Invoke-Step -Label "Detecting serve clips" -Command @(
            "python",
            (Join-Path $root "scripts/detect-serve-clips.py"),
            "--input-video",
            $targetVideoPath,
            "--output",
            $clipsJson
        )

        $processCommand = @(
            "python",
            (Join-Path $root "scripts/process-serve-video.py"),
            "--input-video",
            $targetVideoPath,
            "--clips-json",
            $clipsJson,
            "--provider",
            $Provider,
            "--handedness",
            $Handedness,
            "--sample-every",
            $SampleEvery.ToString(),
            "--clips-dir",
            $clipsDir,
            "--analysis-dir",
            $sessionArtifactDir,
            "--skip-summary"
        )
        if ($Provider -eq "mediapipe") {
            $processCommand += @("--model-asset-path", $resolvedModelPath)
        }
        $clipsData = Get-Content -LiteralPath $clipsJson -Raw -Encoding UTF8 | ConvertFrom-Json
        if (@($clipsData.clips).Count -gt 0) {
            Invoke-Step -Label "Running serve batch analysis" -Command $processCommand

            $videoBaseName = [System.IO.Path]::GetFileNameWithoutExtension($targetVideoPath)
            $legacyBatch = Join-Path $sessionArtifactDir ($videoBaseName + "-batch-analysis.json")
            if ((Test-Path -LiteralPath $legacyBatch -PathType Leaf) -and ($legacyBatch -ne $batchJson)) {
                Move-Item -LiteralPath $legacyBatch -Destination $batchJson -Force
            }

            Invoke-Step -Label "Generating serve report" -Command @(
                "python",
                (Join-Path $root "scripts/generate-serve-report.py"),
                "--batch-analysis",
                $batchJson,
                "--output",
                $serveReportMd,
                "--json-output",
                $serveReportJson
            )

            Update-MetadataFromServeReport -Metadata $metadata -ServeReportJson $serveReportJson -ServeReportMd $serveReportMd -MetadataPath $metadataPath -Root $root
        }
        else {
            Run-SingleVideoPipeline -Root $root -VideoPath $targetVideoPath -ActionType $ActionType -Provider $Provider -Handedness $Handedness -SampleEvery $SampleEvery -ArtifactDir $sessionArtifactDir -ModelAssetPath $(if ($Provider -eq "mediapipe") { $resolvedModelPath } else { "" })
            $singleAnalysisPath = Join-Path $sessionArtifactDir "$sessionId-analysis.json"
            if (Test-Path -LiteralPath $singleAnalysisPath -PathType Leaf) {
                $singleAnalysis = Get-Content -LiteralPath $singleAnalysisPath -Raw -Encoding UTF8 | ConvertFrom-Json
                $metadata.focus_points = @($singleAnalysis.next_focus)
                $metadata.strengths = @($singleAnalysis.strengths)
                $metadata.issues = @($singleAnalysis.issues | ForEach-Object { $_.issue_code })
                $metadata.next_steps = @($singleAnalysis.next_focus)
                $metadata.report_path = "analysis/$AthleteId/$ActionType/$sessionId.md"
                $metadata | ConvertTo-Json -Depth 8 | ForEach-Object {
                    Write-Utf8NoBom -Path $metadataPath -Content ($_ + [Environment]::NewLine)
                }
            }
        }
    }
}
else {
    Run-SingleVideoPipeline -Root $root -VideoPath $targetVideoPath -ActionType $ActionType -Provider $Provider -Handedness $Handedness -SampleEvery $SampleEvery -ArtifactDir $sessionArtifactDir -ModelAssetPath $(if ($Provider -eq "mediapipe") { $resolvedModelPath } else { "" })
}

Invoke-Step -Label "Rebuilding training summary" -Command @(
    "powershell",
    "-NoProfile",
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    (Join-Path $root "scripts/build-training-summary.ps1")
)

Write-Host ""
Write-Host "Analysis start script completed."
Write-Host "Session: $sessionId"
Write-Host "Video: $targetVideoPath"
Write-Host "Metadata: $metadataPath"
if ($ActionType -eq "serve") {
    Write-Host "Artifacts: $sessionArtifactDir"
}
