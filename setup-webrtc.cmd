@echo off
setlocal
cd /d "%~dp0"
if exist ".venv-webrtc\Scripts\python.exe" goto install
where python.exe >nul 2>nul
if not errorlevel 1 (
  python.exe -m venv .venv-webrtc
  goto check
)
where py.exe >nul 2>nul
if not errorlevel 1 (
  py.exe -3 -m venv .venv-webrtc
  goto check
)
set "TAILKEY_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%TAILKEY_PYTHON%" (
  "%TAILKEY_PYTHON%" -m venv .venv-webrtc
  goto check
)
echo Python 3.10 or newer is required.
pause
exit /b 1
:check
if not exist ".venv-webrtc\Scripts\python.exe" exit /b 1
:install
".venv-webrtc\Scripts\python.exe" -m pip install -r webrtc\requirements.txt
if errorlevel 1 (
  echo Setup failed. Check your network and Python installation.
  pause
  exit /b 1
)
echo WebRTC prototype is ready. Run start-webrtc.cmd.
