@echo off
setlocal
cd /d "%~dp0"
if exist "dist\Tailkey\Tailkey.exe" (
  "dist\Tailkey\Tailkey.exe" %*
  exit /b
)
if not exist ".venv-webrtc\Scripts\python.exe" (
  call setup-webrtc.cmd
  if errorlevel 1 exit /b 1
)
".venv-webrtc\Scripts\python.exe" launcher.py %*
