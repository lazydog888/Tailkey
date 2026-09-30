@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv-webrtc\Scripts\python.exe" (
  call setup-webrtc.cmd
  if errorlevel 1 exit /b 1
)
".venv-webrtc\Scripts\python.exe" webrtc\broker.py %*
if errorlevel 1 pause
