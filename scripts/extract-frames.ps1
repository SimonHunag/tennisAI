param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$InputVideo,

    [string]$OutputDir,

    [ValidateRange(1, 3600)]
    [int]$Interval = 1,

    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Resolve-RequiredFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Input video does not exist: $Path"
    }

    return (Resolve-Path -LiteralPath $Path).Path
}

function Get-FfmpegCommand {
    $command = Get-Command ffmpeg -ErrorAction SilentlyContinue
    if (-not $command) {
        throw "ffmpeg was not found. Install ffmpeg and make sure it is available in PATH."
    }

    return $command.Source
}

$inputVideoPath = Resolve-RequiredFile -Path $InputVideo
$videoName = [System.IO.Path]::GetFileNameWithoutExtension($inputVideoPath)

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $OutputDir = Join-Path "frames" $videoName
}

if (Test-Path -LiteralPath $OutputDir) {
    $existingFiles = Get-ChildItem -LiteralPath $OutputDir -File -ErrorAction SilentlyContinue
    if ($existingFiles -and -not $Force) {
        throw "Output directory '$OutputDir' already contains files. Use a new directory or pass -Force."
    }
}
else {
    New-Item -ItemType Directory -Path $OutputDir | Out-Null
}

$ffmpegPath = Get-FfmpegCommand
$resolvedOutputDir = (Resolve-Path -LiteralPath $OutputDir).Path
$outputPattern = Join-Path $resolvedOutputDir "${videoName}_%03d.jpg"

if ($Force) {
    Get-ChildItem -LiteralPath $resolvedOutputDir -File -Filter "${videoName}_*.jpg" -ErrorAction SilentlyContinue |
        Remove-Item -Force
}

Write-Host "Starting frame extraction"
Write-Host "Input video: $inputVideoPath"
Write-Host "Output dir: $resolvedOutputDir"
Write-Host "Interval: $Interval second(s)"
Write-Host "ffmpeg: $ffmpegPath"

& $ffmpegPath -hide_banner -loglevel error -i $inputVideoPath -vf "fps=1/$Interval" -q:v 2 $outputPattern

if ($LASTEXITCODE -ne 0) {
    throw "ffmpeg failed with exit code: $LASTEXITCODE"
}

$frameCount = (Get-ChildItem -LiteralPath $resolvedOutputDir -File -Filter "${videoName}_*.jpg" -ErrorAction SilentlyContinue).Count
Write-Host "Finished. Generated $frameCount frame(s)."
