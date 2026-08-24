@echo off
rem Debug launcher for WhisperWriter (local Russian dictation).
rem Differs from the normal shortcut in three ways:
rem   * python.exe instead of pythonw.exe, so a crash on start leaves a traceback;
rem   * stdout/stderr go to ww_out.log / ww_err.log (both covered by .gitignore);
rem   * the console stays open and shows stderr plus the tail of stdout on exit.
rem Live output is not shown while running - read the logs for that.
chcp 65001 > nul
cd /d "C:\dev\whisper-writer"
set HF_HUB_DISABLE_SYMLINKS_WARNING=1
set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1

echo Starting WhisperWriter (debug). Logs: ww_out.log / ww_err.log
"C:\dev\whisper-writer\venv\Scripts\python.exe" "src\main.py" 1> ww_out.log 2> ww_err.log
set CODE=%ERRORLEVEL%

echo.
echo ==== exited with code %CODE% ====
echo ---- ww_err.log ----
type ww_err.log
echo ---- ww_out.log (last 30 lines) ----
powershell -NoProfile -Command "if (Test-Path ww_out.log) { Get-Content ww_out.log -Tail 30 }"
echo.
pause
