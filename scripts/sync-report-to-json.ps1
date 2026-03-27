param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$ReportPath,

    [string]$MetadataPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-ListValues {
    param(
        [Parameter(Mandatory = $true)]
        [object[]]$Lines,
        [Parameter(Mandatory = $true)]
        [int]$StartIndex
    )

    $values = New-Object System.Collections.Generic.List[string]
    $normalizedLines = @($Lines | ForEach-Object { [string]$_ })

    for ($i = $StartIndex + 1; $i -lt $normalizedLines.Count; $i++) {
        $line = $normalizedLines[$i].Trim()
        if ($line.StartsWith('**') -or $line.StartsWith('## ')) {
            break
        }

        if ($line.StartsWith('- [ ]')) {
            $item = $line.Substring(5).Trim()
            if (-not [string]::IsNullOrWhiteSpace($item)) {
                $values.Add($item)
            }
            continue
        }

        if ($line.StartsWith('- ')) {
            $item = $line.Substring(2).Trim()
            if (-not [string]::IsNullOrWhiteSpace($item)) {
                $values.Add($item)
            }
        }
    }

    return @($values)
}

function Get-SingleLineField {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Content,
        [Parameter(Mandatory = $true)]
        [string]$FieldName
    )

    $pattern = '(?m)^' + [regex]::Escape('**' + $FieldName + ':**') + '[ \t]*(.*)$'
    $match = [regex]::Match($Content, $pattern, [System.Text.RegularExpressions.RegexOptions]::Multiline)
    if (-not $match.Success) {
        return ''
    }

    return $match.Groups[1].Value.Trim()
}

function Get-MetricValue {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Content,
        [Parameter(Mandatory = $true)]
        [string]$MetricName
    )

    $pattern = '-\s*' + [regex]::Escape($MetricName) + ':\s*(.+)?'
    $match = [regex]::Match($Content, $pattern, [System.Text.RegularExpressions.RegexOptions]::Multiline)
    if (-not $match.Success) {
        return $null
    }

    $rawValue = $match.Groups[1].Value.Trim()
    if ([string]::IsNullOrWhiteSpace($rawValue)) {
        return $null
    }

    $number = 0.0
    if ([double]::TryParse($rawValue, [ref]$number)) {
        return $number
    }

    return $null
}

function Get-SectionListByLabel {
    param(
        [Parameter(Mandatory = $true)]
        [object[]]$Lines,
        [Parameter(Mandatory = $true)]
        [string]$Label
    )

    $target = '**' + $Label + ':**'
    $normalizedLines = @($Lines | ForEach-Object { [string]$_ })
    for ($i = 0; $i -lt $normalizedLines.Count; $i++) {
        if ($normalizedLines[$i].Trim() -eq $target) {
            return @(Get-ListValues -Lines $normalizedLines -StartIndex $i)
        }
    }

    return @()
}

$resolvedReportPath = (Resolve-Path -LiteralPath $ReportPath).Path
if ([string]::IsNullOrWhiteSpace($MetadataPath)) {
    $MetadataPath = [System.IO.Path]::ChangeExtension($resolvedReportPath, '.json')
}

if (-not (Test-Path -LiteralPath $MetadataPath -PathType Leaf)) {
    throw ('Metadata file was not found: ' + $MetadataPath)
}

$content = Get-Content -LiteralPath $resolvedReportPath -Raw
$lines = @(Get-Content -LiteralPath $resolvedReportPath)
$metadata = Get-Content -LiteralPath $MetadataPath -Raw -Encoding UTF8 | ConvertFrom-Json

$metadata.date = Get-SingleLineField -Content $content -FieldName 'Date'
$metadata.source_video = Get-SingleLineField -Content $content -FieldName 'Video'
$metadata.action_type = Get-SingleLineField -Content $content -FieldName 'Action Type'
$metadata.reference_video = Get-SingleLineField -Content $content -FieldName 'Reference Video'
$metadata.athlete = Get-SingleLineField -Content $content -FieldName 'Athlete'
$metadata.coach = Get-SingleLineField -Content $content -FieldName 'Coach'
$metadata.camera_view = Get-SingleLineField -Content $content -FieldName 'Camera View'

$sessionTagsRaw = Get-SingleLineField -Content $content -FieldName 'Session Tags'
$metadata.session_tags = if ([string]::IsNullOrWhiteSpace($sessionTagsRaw)) {
    @()
}
else {
    @($sessionTagsRaw.Split(',') | ForEach-Object { $_.Trim() } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
}

$metadata.focus_points = @(Get-SectionListByLabel -Lines $lines -Label 'Focus Points')
$metadata.strengths = @(Get-SectionListByLabel -Lines $lines -Label 'Strengths')
$metadata.issues = @(Get-SectionListByLabel -Lines $lines -Label 'Issues')
$metadata.next_steps = @(Get-SectionListByLabel -Lines $lines -Label 'Next Steps')
$metadata.notes = @(Get-SectionListByLabel -Lines $lines -Label 'Notes')

$metadata.metrics.consistency_score = Get-MetricValue -Content $content -MetricName 'Consistency Score'
$metadata.metrics.balance_score = Get-MetricValue -Content $content -MetricName 'Balance Score'
$metadata.metrics.timing_score = Get-MetricValue -Content $content -MetricName 'Timing Score'

$metadata | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $MetadataPath -Encoding UTF8

Write-Host ('Metadata updated from report: ' + $MetadataPath)
