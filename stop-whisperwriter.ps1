# Stops WhisperWriter.
# Matches only the python process running src\main.py from this folder, so other
# Python programs on the machine are never touched.
# Tries a graceful close first (works when the main window is on screen); falls
# back to a forced kill when the app sits in the tray with no visible window.

$procs = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -like 'python*' -and $_.CommandLine -like '*whisper-writer*main.py*'
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
