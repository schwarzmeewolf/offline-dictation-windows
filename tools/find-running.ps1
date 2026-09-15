<#
.SYNOPSIS
    Exit 1 when WhisperWriter is already running from the given folder, else 0.

.DESCRIPTION
    Matching is on the interpreter's path, which carries the project folder,
    rather than on a hardcoded project name - so a clone in any directory is
    recognised, and a copy running from somewhere else is not mistaken for
    this one.
#>
param([Parameter(Mandatory = $true)][string]$Root)

# Defensive against a caller that passes a trailing backslash or a stray quote:
# both are easy to produce from a .bat and fail confusingly here.
$root = (Resolve-Path -LiteralPath $Root.Trim('"').TrimEnd('\')).Path.TrimEnd('\')

$running = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -like 'python*' -and
    $_.CommandLine -and
    $_.CommandLine.Contains($root) -and
    $_.CommandLine -like '*main.py*'
}

if ($running) { exit 1 } else { exit 0 }
