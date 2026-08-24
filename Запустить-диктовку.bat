@echo off
rem Launcher for WhisperWriter (local Russian dictation)
cd /d "C:\dev\whisper-writer"
set HF_HUB_DISABLE_SYMLINKS_WARNING=1

rem Bound to a hotkey via the desktop shortcut, so it may be pressed while the
rem app is already in the tray. Exit quietly instead of starting a second copy.
powershell -NoProfile -Command "if (Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and $_.CommandLine -like '*whisper-writer*main.py*' }) { exit 1 } else { exit 0 }"
if errorlevel 1 exit /b 0

start "" "C:\dev\whisper-writer\venv\Scripts\pythonw.exe" "src\main.py"
