@echo off
rem Launcher for WhisperWriter. Paths are derived from this file's own location,
rem so the project can live anywhere and a desktop shortcut still works.
cd /d "%~dp0"
set HF_HUB_DISABLE_SYMLINKS_WARNING=1

rem Usually bound to a hotkey, so it may be pressed while the app is already in
rem the tray. Match on this folder rather than on a fixed name, and exit quietly
rem instead of starting a second copy.
rem %~dp0 ends in a backslash, which would escape the closing quote and hand
rem PowerShell a path with a quote stuck on the end. Trim it before passing.
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%\tools\find-running.ps1" -Root "%ROOT%"
if errorlevel 1 exit /b 0

rem Without the venv, Windows would put up "cannot find ...pythonw.exe" and
rem leave the person guessing. Say what is actually missing, in both languages.
rem The message lives in a .ps1: cmd loses its place in a .bat that holds
rem non-ASCII text, so this file must stay pure ASCII.
if not exist "%~dp0venv\Scripts\pythonw.exe" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\not-installed.ps1"
    pause
    exit /b 1
)

start "" "%~dp0venv\Scripts\pythonw.exe" "src\main.py"
