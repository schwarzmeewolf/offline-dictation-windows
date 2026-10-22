<#
.SYNOPSIS
    Install WhisperWriter for someone who has never used a command line.

.DESCRIPTION
    Run through install.bat in the project root, which is what a person
    double-clicks. Checks for Python 3.11, builds the venv, installs the
    requirements, offers GPU support when an NVIDIA card is present, and puts
    a shortcut in the Start menu - optionally in Startup too.

    Safe to run again: an existing venv is reused and pip only fills in what is
    missing. Every message is printed in English and Russian.

    The shortcuts start the app through tools\launch-hidden.vbs, so no console
    window flashes up when it is started.

.PARAMETER Unattended
    Ask nothing: no GPU support, no autostart, no launch at the end. For
    testing, and for anyone scripting the install.

.PARAMETER ShortcutName
    Name of the Start menu shortcut. Defaults to WhisperWriter.
#>
param(
    [switch]$Unattended,
    [string]$ShortcutName = 'WhisperWriter'
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Venv = Join-Path $Root 'venv'
$Python = Join-Path $Venv 'Scripts\python.exe'

function Say([string]$English, [string]$Russian) {
    Write-Host $English
    Write-Host $Russian -ForegroundColor DarkGray
}

function Ask([string]$English, [string]$Russian, [bool]$Default) {
    if ($Unattended) { return $false }
    $hint = if ($Default) { '[Y/n]' } else { '[y/N]' }
    Write-Host ''
    Write-Host "$English $hint"
    Write-Host $Russian -ForegroundColor DarkGray
    $answer = (Read-Host '>').Trim().ToLower()
    if ($answer -eq '') { return $Default }
    return $answer -in @('y', 'yes', 'д', 'да')
}

function Fail([string]$English, [string]$Russian) {
    Write-Host ''
    Write-Host $English -ForegroundColor Red
    Write-Host $Russian -ForegroundColor Red
    exit 1
}

function New-Shortcut([string]$Path) {
    $shell = New-Object -ComObject WScript.Shell
    $link = $shell.CreateShortcut($Path)
    $link.TargetPath = Join-Path $env:WINDIR 'System32\wscript.exe'
    $link.Arguments = '"' + (Join-Path $Root 'tools\launch-hidden.vbs') + '"'
    $link.WorkingDirectory = $Root
    $link.IconLocation = Join-Path $Root 'assets\ww-logo.ico'
    $link.Description = 'WhisperWriter - offline dictation'
    $link.Save()
}

Say 'WhisperWriter setup' 'Установка WhisperWriter'
Say "Folder: $Root" "Папка: $Root"
Write-Host ''

# 1. Python 3.11, through the py launcher every python.org installer brings.
#    Other versions are not interchangeable: the pinned packages ship wheels
#    for 3.11, and on 3.12 or 3.13 pip would try to build some from source.
#    py reports a missing version on stderr, which Windows PowerShell turns into
#    a terminating error under 'Stop' - hence the local 'Continue'.
$found = $false
if (Get-Command py -ErrorAction SilentlyContinue) {
    $ErrorActionPreference = 'Continue'
    & py -3.11 -c 'import sys' 2>$null | Out-Null
    $found = ($LASTEXITCODE -eq 0)
    $ErrorActionPreference = 'Stop'
}
if (-not $found) {
    Fail ("Python 3.11 was not found. Download the Windows installer (64-bit) from`n" +
          "  https://www.python.org/downloads/release/python-3119/`n" +
          "run it, leave 'py launcher' ticked, and start install.bat again.") `
         ("Python 3.11 не найден. Скачайте установщик для Windows (64-bit) отсюда:`n" +
          "  https://www.python.org/downloads/release/python-3119/`n" +
          "запустите его, не снимайте галочку 'py launcher' и снова запустите install.bat.")
}
Say 'Python 3.11: found.' 'Python 3.11: найден.'

# 2. Somewhere pip can write. Windows refuses paths over 260 characters unless
#    long paths are switched on, and PyQt5 alone puts a file about 105
#    characters deep inside the venv. Past that, pip fails half-way with an
#    OSError that reads like anything but "your folder is too deep".
$longPaths = (Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' `
              -Name LongPathsEnabled -ErrorAction SilentlyContinue).LongPathsEnabled
if ($Root.Length -gt 140 -and $longPaths -ne 1) {
    Fail ("The folder path is too long for Windows ($($Root.Length) characters; 140 at most).`n" +
          "Move the whisper-writer folder somewhere shorter - C:\WhisperWriter, say - and run install.bat there.") `
         ("Путь к папке слишком длинный для Windows ($($Root.Length) символов, можно не больше 140).`n" +
          "Перенесите папку whisper-writer повыше - например, в C:\WhisperWriter - и запустите install.bat там.")
}

# 3. The venv and the requirements.
if (-not (Test-Path $Python)) {
    Say 'Creating the Python environment...' 'Создаю окружение Python...'
    & py -3.11 -m venv $Venv
    if ($LASTEXITCODE -ne 0) { Fail 'Could not create the environment.' 'Не удалось создать окружение.' }
}
Say 'Installing the components (about 500 MB, a few minutes)...' `
    'Ставлю компоненты (около 500 МБ, несколько минут)...'
& $Python -m pip install --disable-pip-version-check -q -r (Join-Path $Root 'requirements.txt')
if ($LASTEXITCODE -ne 0) {
    Fail 'Installing the components failed - see the messages above. Check the internet connection and run install.bat again.' `
         'Компоненты не установились - причина в сообщениях выше. Проверьте интернет и запустите install.bat ещё раз.'
}
Say 'Components installed.' 'Компоненты установлены.'

# 4. GPU support, only where there is a card to use it.
$nvidia = @(Get-CimInstance Win32_VideoController -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -match 'NVIDIA' })
if ($nvidia) {
    Say "Graphics card: $($nvidia[0].Name)" "Видеокарта: $($nvidia[0].Name)"
    if (Ask 'Install GPU support? Faster and more accurate dictation; about 2 GB more.' `
            'Поставить поддержку видеокарты? Диктовка быстрее и точнее; ещё около 2 ГБ.' $false) {
        & $Python -m pip install --disable-pip-version-check -q -r (Join-Path $Root 'requirements-gpu.txt')
        if ($LASTEXITCODE -ne 0) {
            Say 'GPU support did not install; the program will use the processor.' `
                'Поддержка видеокарты не установилась; программа будет работать на процессоре.'
        } else {
            Say 'GPU support installed. Choose a larger model in Settings to make use of it.' `
                'Поддержка видеокарты установлена. Чтобы ей пользоваться, выберите модель побольше в Настройках.'
        }
    }
}

# 5. Shortcuts.
$startMenu = Join-Path ([Environment]::GetFolderPath('Programs')) "$ShortcutName.lnk"
New-Shortcut $startMenu
Say "Start menu shortcut: $ShortcutName" "Ярлык в меню «Пуск»: $ShortcutName"

if (Ask 'Start WhisperWriter automatically when you sign in to Windows?' `
        'Запускать WhisperWriter автоматически при входе в Windows?' $false) {
    New-Shortcut (Join-Path ([Environment]::GetFolderPath('Startup')) "$ShortcutName.lnk")
    Say 'Autostart is on.' 'Автозапуск включён.'
}

# 6. What happens next.
Write-Host ''
Say 'Done. The first start downloads the speech model (about 460 MB) and opens the settings window.' `
    'Готово. Первый запуск скачает модель распознавания (около 460 МБ) и откроет окно настроек.'
Say 'Then press Pause, speak, and pause: the text is typed where the cursor is.' `
    'Дальше: нажмите Pause, говорите и замолчите - текст напечатается там, где курсор.'
Say 'Before relying on it, read DISCLAIMER.md in this folder.' `
    'Прежде чем на неё полагаться, прочитайте DISCLAIMER.md в этой папке.'

if (Ask 'Start WhisperWriter now?' 'Запустить WhisperWriter сейчас?' $true) {
    Start-Process -FilePath (Join-Path $env:WINDIR 'System32\wscript.exe') `
                  -ArgumentList ('"' + (Join-Path $Root 'tools\launch-hidden.vbs') + '"')
}
exit 0
