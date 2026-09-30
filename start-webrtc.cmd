@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv-webrtc\Scripts\python.exe" (
  call setup-webrtc.cmd
  if errorlevel 1 exit /b 1
)
".venv-webrtc\Scripts\python.exe" webrtc\app.py %*
if errorlevel 1 (
  echo Tailkey WebRTC could not start. See the message above for details.
  pause
)
