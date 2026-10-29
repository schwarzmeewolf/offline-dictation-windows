@echo off
rem Stops WhisperWriter. Usually bound to a hotkey via a desktop shortcut.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop-whisperwriter.ps1"
