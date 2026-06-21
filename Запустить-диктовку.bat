@echo off
rem Launcher for WhisperWriter (local Russian dictation)
cd /d "C:\dev\whisper-writer"
set HF_HUB_DISABLE_SYMLINKS_WARNING=1
start "" "C:\dev\whisper-writer\venv\Scripts\pythonw.exe" "src\main.py"
