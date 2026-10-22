<#
.SYNOPSIS
    Build the Windows archive: unpack, double-click WhisperWriter.exe, dictate.

.DESCRIPTION
    Makes a CPU-only build in a separate environment (build-venv, so the GPU
    libraries of a development venv cannot leak in), runs PyInstaller with
    tools\WhisperWriter.spec, puts assets and the documents next to the exe,
    and zips the folder as dist\WhisperWriter-<version>-windows-x64.zip.

    The speech model is not in the archive. The app downloads it at the
    first start, as it always has - 460 MB for `small` - into the user's
    Hugging Face cache.

.PARAMETER SkipInstall
    Reuse build-venv as it is. For rebuilding after a code change.
#>
param(
    [switch]$SkipInstall
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Venv = Join-Path $Root 'build-venv'
$Python = Join-Path $Venv 'Scripts\python.exe'
$Dist = Join-Path $Root 'dist'
$Out = Join-Path $Dist 'WhisperWriter'

$version = (Select-String -Path (Join-Path $Root 'src\version.py') -Pattern "__version__ = '([^']+)'").Matches[0].Groups[1].Value
Write-Host "Building WhisperWriter $version"

if (-not (Test-Path $Python)) {
    Write-Host 'Creating build-venv (CPU only)...'
    & py -3.11 -m venv $Venv
}
# pip and PyInstaller both write ordinary progress to stderr, and Windows
# PowerShell under 'Stop' treats the first such line as a fatal error. Let
# them talk; the exit code is what says whether they failed.
$ErrorActionPreference = 'Continue'
if (-not $SkipInstall) {
    Write-Host 'Installing requirements and PyInstaller...'
    & $Python -m pip install --disable-pip-version-check -q -r (Join-Path $Root 'requirements.txt') pyinstaller
    if ($LASTEXITCODE -ne 0) { throw 'pip failed' }
}

# The PyQt5 wheel ships its own Visual C++ runtime (msvcp140.dll 14.26 and
# friends) in Qt5\bin. onnxruntime needs a newer one, and PyInstaller's
# analysis imports PyQt5 first of all, so with those copies in place its
# probe process dies with an access violation and the build ends. Remove
# them: the system's runtime (Python itself needs it, so it is there) serves
# both, and the bundle then carries one consistent copy instead of two.
$qtBin = Join-Path $Venv 'Lib\site-packages\PyQt5\Qt5\bin'
Get-ChildItem $qtBin -Include 'msvcp140*.dll', 'vcruntime140*.dll', 'concrt140.dll' -Recurse |
    Remove-Item -Force

# Everything PyInstaller says goes to build\pyinstaller.log - the full INFO
# stream, not the WARN subset, because a crash in its analysis subprocess
# names the module only in the full traceback. On failure the tail is shown.
$Build = Join-Path $Root 'build'
New-Item -ItemType Directory -Force $Build | Out-Null
$log = Join-Path $Build 'pyinstaller.log'
Write-Host "Running PyInstaller (log: $log)..."
& $Python -m PyInstaller --noconfirm --clean --log-level INFO `
    --distpath $Dist --workpath $Build `
    (Join-Path $Root 'tools\WhisperWriter.spec') *> $log
if ($LASTEXITCODE -ne 0) {
    Get-Content $log -Tail 40
    throw "PyInstaller failed - full log: $log"
}
$ErrorActionPreference = 'Stop'

# The app looks for assets, src\config.yaml and .env relative to its own
# folder, and writes its logs there. Everything a user reads goes there too.
Copy-Item (Join-Path $Root 'assets') (Join-Path $Out 'assets') -Recurse -Force
foreach ($doc in 'README.md', 'DISCLAIMER.md', 'LICENSE', 'CHANGELOG.md') {
    Copy-Item (Join-Path $Root $doc) $Out -Force
}
New-Item -ItemType Directory -Force (Join-Path $Out 'src') | Out-Null

$zip = Join-Path $Dist "WhisperWriter-$version-windows-x64.zip"
if (Test-Path $zip) { Remove-Item $zip }
Write-Host 'Zipping...'
& tar -a -cf $zip -C $Dist 'WhisperWriter'
if ($LASTEXITCODE -ne 0) { throw 'zip failed' }

$mb = [int]((Get-Item $zip).Length / 1MB)
Write-Host "Done: $zip ($mb MB)"
