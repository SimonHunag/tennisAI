param(
    [string]$AnalysisDir = "analysis",
    [string]$OutputPath = "analysis\training-summary.md",
    [string]$JsonOutputPath,
    [string]$CsvOutputPath,
    [string[]]$ActionType,
    [string[]]$Athlete,
    [string]$DateFrom,
    [string]$DateTo
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [string]$Content
    )

    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    $parent = Split-Path -Parent $Path
    if ($parent -and -not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    [System.IO.File]::WriteAllText($Path, $Content, $utf8NoBom)
}

function Get-ScoreAverage {
    param(
        [object[]]$Values
    )

    if ($null -eq $Values) {
        return "n/a"
    }

    $numericValues = @($Values | Where-Object { $_ -is [int] -or $_ -is [long] -or $_ -is [double] -or $_ -is [decimal] })
    if (-not $numericValues.Count) {
        return "n/a"
    }

    return [Math]::Round((($numericValues | Measure-Object -Average).Average), 2)
}

function Convert-ToNullableDate {
    param(
        [string]$Value,
        [string]$FieldName
    )

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return $null
    }

    try {
        return [datetime]::ParseExact($Value, "yyyy-MM-dd", $null)
    }
    catch {
        throw "$FieldName must use yyyy-MM-dd format."
    }
}

function Join-OrDash {
    param(
        [object[]]$Values
    )

    $items = @($Values | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) })
    if (-not $items.Count) {
        return "-"
    }

    return ($items -join ", ")
}

function Join-OrEmpty {
    param(
        [object[]]$Values
    )

    $items = @($Values | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) })
    if (-not $items.Count) {
        return ""
    }

    return ($items -join "; ")
}

function Get-DefaultSiblingPath {
    param(
        [string]$BasePath,
        [string]$Extension
    )

    return [System.IO.Path]::ChangeExtension($BasePath, $Extension)
}

function Get-AutoAnalysisSummary {
    param(
        [Parameter(Mandatory = $true)]
        [string]$AnalysisDir,
        [Parameter(Mandatory = $true)]
        [string]$SessionId
    )

    $analysisPath = Join-Path $AnalysisDir "$SessionId-analysis.json"
    if (-not (Test-Path -LiteralPath $analysisPath -PathType Leaf)) {
        return $null
    }

    $item = Get-Content -LiteralPath $analysisPath -Raw -Encoding UTF8 | ConvertFrom-Json
    return [PSCustomObject]@{
        phases = $item.phases
        metrics = $item.metrics
        issues = @($item.issues)
        strengths = @($item.strengths)
        next_focus = @($item.next_focus)
    }
}

function Get-ServeReportSummary {
    param(
        [Parameter(Mandatory = $true)]
        [string]$AnalysisDir,
        [Parameter(Mandatory = $true)]
        [string]$AthleteId,
        [Parameter(Mandatory = $true)]
        [string]$ActionType,
        [Parameter(Mandatory = $true)]
        [string]$SessionId
    )

    $serveReportJson = Join-Path $AnalysisDir $AthleteId
    $serveReportJson = Join-Path $serveReportJson $ActionType
    $serveReportJson = Join-Path $serveReportJson $SessionId
    $serveReportJson = Join-Path $serveReportJson "$SessionId-serve-report.json"
    if (-not (Test-Path -LiteralPath $serveReportJson -PathType Leaf)) {
        return $null
    }

    return Get-Content -LiteralPath $serveReportJson -Raw -Encoding UTF8 | ConvertFrom-Json
}

$parsedDateFrom = Convert-ToNullableDate -Value $DateFrom -FieldName "DateFrom"
$parsedDateTo = Convert-ToNullableDate -Value $DateTo -FieldName "DateTo"

if ([string]::IsNullOrWhiteSpace($JsonOutputPath)) {
    $JsonOutputPath = Get-DefaultSiblingPath -BasePath $OutputPath -Extension "json"
}

if ([string]::IsNullOrWhiteSpace($CsvOutputPath)) {
    $CsvOutputPath = Get-DefaultSiblingPath -BasePath $OutputPath -Extension "csv"
}

$resolvedAnalysisDir = (Resolve-Path -LiteralPath $AnalysisDir).Path
$metadataFiles = Get-ChildItem -LiteralPath $resolvedAnalysisDir -Recurse -File -Filter "*.json" |
    Where-Object {
        $_.Name -ne "metadata-template.json" -and
        $_.Name -ne "pose-template.json" -and
        $_.Name -ne "auto-analysis-template.json" -and
        $_.Name -notlike "*-analysis.json" -and
        $_.Name -notlike "*-pose.json" -and
        $_.Name -ne "training-summary.json" -and
        $_.Name -notlike "*-batch-analysis.json" -and
        $_.Name -notlike "*-clips.json" -and
        $_.Name -notlike "*-segments.json" -and
        $_.Name -notlike "*-serve-report.json" -and
        $_.Name -notlike "*-comparison.json"
    }

if (-not $metadataFiles) {
    throw "No analysis metadata files were found in $resolvedAnalysisDir"
}

$sessions = @(
    foreach ($file in $metadataFiles) {
        $item = Get-Content -LiteralPath $file.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
        $sessionDate = Convert-ToNullableDate -Value $item.date -FieldName "session date"
        $autoAnalysis = Get-AutoAnalysisSummary -AnalysisDir $resolvedAnalysisDir -SessionId $item.session_id
        $serveReport = Get-ServeReportSummary -AnalysisDir $resolvedAnalysisDir -AthleteId $item.athlete_id -ActionType $item.action_type -SessionId $item.session_id
        $serveReportJsonPath = if ($serveReport) {
            ("analysis/{0}/{1}/{2}/{2}-serve-report.json" -f $item.athlete_id, $item.action_type, $item.session_id).Replace('\', '/')
        }
        else {
            $null
        }
        $focusPoints = if ($serveReport) { @($serveReport.priority_focus | ForEach-Object { $_.name }) } else { @($item.focus_points) }
        $strengths = if ($serveReport) { @($serveReport.strengths | ForEach-Object { $_.name }) } else { @($item.strengths) }
        $issues = if ($serveReport) { @($serveReport.common_issues | ForEach-Object { $_.label }) } else { @($item.issues) }
        $nextSteps = if ($serveReport) { @($serveReport.training_priorities) } else { @($item.next_steps) }

        [PSCustomObject]@{
            SessionId = $item.session_id
            Date = $item.date
            ParsedDate = $sessionDate
            ActionType = $item.action_type
            Athlete = $item.athlete
            AthleteId = $item.athlete_id
            Coach = $item.coach
            CameraView = $item.camera_view
            SessionTags = @($item.session_tags)
            FocusPoints = $focusPoints
            Strengths = $strengths
            Issues = $issues
            NextSteps = $nextSteps
            Consistency = $item.metrics.consistency_score
            Balance = $item.metrics.balance_score
            Timing = $item.metrics.timing_score
            ReportPath = $item.report_path
            ServeReportJson = $serveReportJsonPath
            SourceVideo = $item.source_video
            ReferenceVideo = $item.reference_video
            AutoAnalysis = $autoAnalysis
        }
    }
)

$filteredSessions = @(
    $sessions | Where-Object {
        $matchesAction = if ($ActionType -and $ActionType.Count) {
            $_.ActionType -in $ActionType
        }
        else {
            $true
        }

        $matchesAthlete = if ($Athlete -and $Athlete.Count) {
            $_.AthleteId -in $Athlete -or $_.Athlete -in $Athlete
        }
        else {
            $true
        }

        $matchesFrom = if ($parsedDateFrom) {
            $_.ParsedDate -and $_.ParsedDate -ge $parsedDateFrom
        }
        else {
            $true
        }

        $matchesTo = if ($parsedDateTo) {
            $_.ParsedDate -and $_.ParsedDate -le $parsedDateTo
        }
        else {
            $true
        }

        $matchesAction -and $matchesAthlete -and $matchesFrom -and $matchesTo
    }
)

if (-not $filteredSessions.Count) {
    throw "No sessions matched the current filters."
}

$sortedSessions = @($filteredSessions | Sort-Object Date, SessionId)
$actionBreakdown = @($sortedSessions | Group-Object ActionType | Sort-Object Name)
$focusBreakdown = @(
    $sortedSessions |
        ForEach-Object { $_.FocusPoints } |
        Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
        Group-Object |
        Sort-Object -Property Count, Name -Descending |
        Select-Object -First 5
)
$issueBreakdown = @(
    $sortedSessions |
        ForEach-Object { $_.Issues } |
        Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
        Group-Object |
        Sort-Object -Property Count, Name -Descending |
        Select-Object -First 5
)
$autoIssueBreakdown = @(
    $sortedSessions |
        ForEach-Object {
            if ($_.AutoAnalysis) {
                $_.AutoAnalysis.issues | ForEach-Object { $_.issue_code }
            }
        } |
        Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
        Group-Object |
        Sort-Object -Property Count, Name -Descending |
        Select-Object -First 5
)

$summaryLines = New-Object System.Collections.Generic.List[string]
$summaryLines.Add("# Training Summary")
$summaryLines.Add("")
$summaryLines.Add("Generated on: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")")
$summaryLines.Add("")
$summaryLines.Add("## Active Filters")
$summaryLines.Add("")
$summaryLines.Add("- Action types: $(if ($ActionType -and $ActionType.Count) { $ActionType -join ", " } else { "all" })")
$summaryLines.Add("- Athletes: $(if ($Athlete -and $Athlete.Count) { $Athlete -join ", " } else { "all" })")
$summaryLines.Add("- Date from: $(if ($DateFrom) { $DateFrom } else { "none" })")
$summaryLines.Add("- Date to: $(if ($DateTo) { $DateTo } else { "none" })")
$summaryLines.Add("")
$summaryLines.Add("## Overview")
$summaryLines.Add("")
$summaryLines.Add("- Total sessions: $($sortedSessions.Count)")
$summaryLines.Add("- Average consistency score: $(Get-ScoreAverage -Values $sortedSessions.Consistency)")
$summaryLines.Add("- Average balance score: $(Get-ScoreAverage -Values $sortedSessions.Balance)")
$summaryLines.Add("- Average timing score: $(Get-ScoreAverage -Values $sortedSessions.Timing)")
$summaryLines.Add("")
$summaryLines.Add("## Action Breakdown")
$summaryLines.Add("")

foreach ($group in $actionBreakdown) {
    $summaryLines.Add("- $($group.Name): $($group.Count)")
}

$summaryLines.Add("")
$summaryLines.Add("## Top Focus Points")
$summaryLines.Add("")
if ($focusBreakdown.Count) {
    foreach ($group in $focusBreakdown) {
        $summaryLines.Add("- $($group.Name): $($group.Count)")
    }
}
else {
    $summaryLines.Add("- n/a")
}

$summaryLines.Add("")
$summaryLines.Add("## Top Issues")
$summaryLines.Add("")
if ($issueBreakdown.Count) {
    foreach ($group in $issueBreakdown) {
        $summaryLines.Add("- $($group.Name): $($group.Count)")
    }
}
else {
    $summaryLines.Add("- n/a")
}

$summaryLines.Add("")
$summaryLines.Add("## Top Auto Issues")
$summaryLines.Add("")
if ($autoIssueBreakdown.Count) {
    foreach ($group in $autoIssueBreakdown) {
        $summaryLines.Add("- $($group.Name): $($group.Count)")
    }
}
else {
    $summaryLines.Add("- n/a")
}

$summaryLines.Add("")
$summaryLines.Add("## Sessions")
$summaryLines.Add("")
$summaryLines.Add("| Date | Athlete | Session | Action | Camera | Focus | Issues | Next Steps | Scores |")
$summaryLines.Add("|------|---------|---------|--------|--------|-------|--------|------------|--------|")

foreach ($session in $sortedSessions) {
    $camera = if ([string]::IsNullOrWhiteSpace($session.CameraView)) { "-" } else { $session.CameraView }
    $athleteLabel = if ([string]::IsNullOrWhiteSpace($session.Athlete)) { $session.AthleteId } else { $session.Athlete }
    $scores = "C=$(if ($null -ne $session.Consistency) { $session.Consistency } else { "n/a" }), B=$(if ($null -ne $session.Balance) { $session.Balance } else { "n/a" }), T=$(if ($null -ne $session.Timing) { $session.Timing } else { "n/a" })"
    $summaryLines.Add("| $($session.Date) | $athleteLabel | $($session.SessionId) | $($session.ActionType) | $camera | $(Join-OrDash -Values $session.FocusPoints) | $(Join-OrDash -Values $session.Issues) | $(Join-OrDash -Values $session.NextSteps) | $scores |")
}

$summaryLines.Add("")
$summaryLines.Add("## Notes")
$summaryLines.Add("")
$summaryLines.Add("- Edit the Markdown report first, then run sync-report-to-json.ps1 before rebuilding the summary.")

$dashboardActionTypes = New-Object System.Collections.ArrayList
if ($ActionType -and $ActionType.Count) {
    foreach ($item in $ActionType) {
        [void]$dashboardActionTypes.Add($item)
    }
}

$dashboardAthletes = New-Object System.Collections.ArrayList
if ($Athlete -and $Athlete.Count) {
    foreach ($item in $Athlete) {
        [void]$dashboardAthletes.Add($item)
    }
}

$dashboardFilters = [PSCustomObject]@{
    action_types = $dashboardActionTypes
    athletes = $dashboardAthletes
    date_from = if ($DateFrom) { $DateFrom } else { $null }
    date_to = if ($DateTo) { $DateTo } else { $null }
}

$dashboardOverview = [PSCustomObject]@{
    total_sessions = $sortedSessions.Count
    average_consistency_score = Get-ScoreAverage -Values $sortedSessions.Consistency
    average_balance_score = Get-ScoreAverage -Values $sortedSessions.Balance
    average_timing_score = Get-ScoreAverage -Values $sortedSessions.Timing
}

$dashboardData = [PSCustomObject]@{
    generated_at = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
    filters = $dashboardFilters
    overview = $dashboardOverview
    action_breakdown = @(
        foreach ($group in $actionBreakdown) {
            [PSCustomObject]@{
                action_type = $group.Name
                count = $group.Count
            }
        }
    )
    top_focus_points = @(
        foreach ($group in $focusBreakdown) {
            [PSCustomObject]@{
                name = $group.Name
                count = $group.Count
            }
        }
    )
    top_issues = @(
        foreach ($group in $issueBreakdown) {
            [PSCustomObject]@{
                name = $group.Name
                count = $group.Count
            }
        }
    )
    top_auto_issues = @(
        foreach ($group in $autoIssueBreakdown) {
            [PSCustomObject]@{
                name = $group.Name
                count = $group.Count
            }
        }
    )
    sessions = @(
        foreach ($session in $sortedSessions) {
            [PSCustomObject]@{
                session_id = $session.SessionId
                date = $session.Date
                action_type = $session.ActionType
                athlete = $session.Athlete
                athlete_id = $session.AthleteId
                coach = $session.Coach
                camera_view = $session.CameraView
                session_tags = @($session.SessionTags)
                focus_points = @($session.FocusPoints)
                strengths = @($session.Strengths)
                issues = @($session.Issues)
                next_steps = @($session.NextSteps)
                scores = [PSCustomObject]@{
                    consistency = $session.Consistency
                    balance = $session.Balance
                    timing = $session.Timing
                }
                report_path = $session.ReportPath
                serve_report_json = $session.ServeReportJson
                source_video = $session.SourceVideo
                reference_video = $session.ReferenceVideo
                auto_analysis = if ($session.AutoAnalysis) {
                    [PSCustomObject]@{
                        phases = $session.AutoAnalysis.phases
                        metrics = $session.AutoAnalysis.metrics
                        issues = @($session.AutoAnalysis.issues)
                        strengths = @($session.AutoAnalysis.strengths)
                        next_focus = @($session.AutoAnalysis.next_focus)
                    }
                }
                else {
                    $null
                }
            }
        }
    )
}

$csvRows = @(
    foreach ($session in $sortedSessions) {
        [PSCustomObject]@{
            date = $session.Date
            session_id = $session.SessionId
            action_type = $session.ActionType
            athlete = $session.Athlete
            athlete_id = $session.AthleteId
            coach = $session.Coach
            camera_view = $session.CameraView
            session_tags = Join-OrEmpty -Values $session.SessionTags
            focus_points = Join-OrEmpty -Values $session.FocusPoints
            strengths = Join-OrEmpty -Values $session.Strengths
            issues = Join-OrEmpty -Values $session.Issues
            next_steps = Join-OrEmpty -Values $session.NextSteps
            consistency_score = $session.Consistency
            balance_score = $session.Balance
            timing_score = $session.Timing
            report_path = $session.ReportPath
            source_video = $session.SourceVideo
            reference_video = $session.ReferenceVideo
            auto_issue_codes = if ($session.AutoAnalysis) {
                Join-OrEmpty -Values @($session.AutoAnalysis.issues | ForEach-Object { $_.issue_code })
            }
            else {
                ""
            }
            auto_next_focus = if ($session.AutoAnalysis) {
                Join-OrEmpty -Values $session.AutoAnalysis.next_focus
            }
            else {
                ""
            }
        }
    }
)

Write-Utf8NoBom -Path $OutputPath -Content (($summaryLines -join [Environment]::NewLine) + [Environment]::NewLine)
Write-Utf8NoBom -Path $JsonOutputPath -Content (($dashboardData | ConvertTo-Json -Depth 8) + [Environment]::NewLine)
Write-Utf8NoBom -Path $CsvOutputPath -Content ((($csvRows | ConvertTo-Csv -NoTypeInformation) -join [Environment]::NewLine) + [Environment]::NewLine)

Write-Host "Training summary written to: $OutputPath"
Write-Host "Dashboard JSON written to: $JsonOutputPath"
Write-Host "Dashboard CSV written to: $CsvOutputPath"
