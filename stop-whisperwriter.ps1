# Stops WhisperWriter.
# Matches only the python process running src\main.py from this folder, so other
# Python programs on the machine are never touched.
# Tries a graceful close first (works when the main window is on screen); falls
# back to a forced kill when the app sits in the tray with no visible window.

# Matched on this script's own folder rather than a hardcoded project name,
# so a clone in any directory is found and another checkout is left alone.
# The folder is compared as a whole path, never as a substring of the command
# line: with the project in a drive root that substring is just "C:\", which
# every Python on the drive contains.
$root = $PSScriptRoot.TrimEnd('\') + '\'
$venv = $root + 'venv\'
$script = $root + 'src\main.py'

$all = Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' }

# Ours: the interpreter is this project's venv and runs main.py, or any
# interpreter was given this project's main.py by full path.
$procs = @($all | Where-Object {
    $_.CommandLine -and $_.CommandLine -like '*main.py*' -and (
        ($_.ExecutablePath -and $_.ExecutablePath.StartsWith($venv, [StringComparison]::OrdinalIgnoreCase)) -or
        $_.CommandLine.IndexOf($script, [StringComparison]::OrdinalIgnoreCase) -ge 0)
})
# The venv's pythonw.exe is only a launcher: it starts the base interpreter as
# a child, whose command line carries the relative src\main.py and no folder.
$ids = $procs | ForEach-Object { $_.ProcessId }
$procs += @($all | Where-Object { $ids -contains $_.ParentProcessId -and $ids -notcontains $_.ProcessId })

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
