# Stops WhisperWriter.
# Matches only the python process running src\main.py from this folder, so other
# Python programs on the machine are never touched.
# Tries a graceful close first (works when the main window is on screen); falls
# back to a forced kill when the app sits in the tray with no visible window.

# Matched on this script's own folder rather than a hardcoded project name,
# so a clone in any directory is found and another checkout is left alone.
$root = $PSScriptRoot.TrimEnd('')

$procs = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -like 'python*' -and
    $_.CommandLine -and
    $_.CommandLine.Contains($root) -and
    $_.CommandLine -like '*main.py*'
}

if (-not $procs) {
    Write-Output 'WhisperWriter is not running.'
    exit 0
}

foreach ($p in $procs) {
    $proc = Get-Process -Id $p.ProcessId -ErrorAction SilentlyContinue
    if ($null -eq $proc) { continue }

    $closed = $false
    if ($proc.MainWindowHandle -ne 0) {
        [void]$proc.CloseMainWindow()
        $closed = $proc.WaitForExit(3000)
    }

    if ($closed) {
        Write-Output ('closed gracefully: pid ' + $proc.Id)
    } else {
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        Write-Output ('killed: pid ' + $proc.Id)
    }
}
