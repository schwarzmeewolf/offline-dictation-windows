@echo off
rem Stops WhisperWriter. Bound to a hotkey via the desktop shortcut
rem "Diktovka - stop" (Properties -> Shortcut key).
cd /d "C:\dev\whisper-writer"
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\dev\whisper-writer\stop-whisperwriter.ps1"
