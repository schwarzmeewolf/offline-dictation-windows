@echo off
rem Double-click to install. The work is in tools\install.ps1; this file only
rem exists because a .bat opens on a double-click and a .ps1 does not.
rem
rem ExecutionPolicy Bypass applies to this one run only and changes nothing in
rem the system's settings. The pause keeps the window open long enough to read
rem the result; any key closes it.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\install.ps1" %*
echo.
pause
