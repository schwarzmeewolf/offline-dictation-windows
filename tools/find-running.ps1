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
# The backslash is trimmed only after resolving: "C:\" trimmed first is "C:",
# which Windows reads as the current folder on drive C, not as its root.
$root = (Resolve-Path -LiteralPath $Root.Trim('"')).Path.TrimEnd('\') + '\'
$venv = $root + 'venv\'
$script = $root + 'src\main.py'

# Compared as a whole path, never as a substring of the command line: with the
# project in a drive root that substring would be "C:\", matching any Python.
$running = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -like 'python*' -and
    $_.CommandLine -and
    $_.CommandLine -like '*main.py*' -and (
        ($_.ExecutablePath -and $_.ExecutablePath.StartsWith($venv, [StringComparison]::OrdinalIgnoreCase)) -or
        $_.CommandLine.IndexOf($script, [StringComparison]::OrdinalIgnoreCase) -ge 0)
}

if ($running) { exit 1 } else { exit 0 }
