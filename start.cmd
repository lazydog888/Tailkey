@echo off
setlocal
cd /d "%~dp0"

if exist "%~dp0tailkey.local.cmd" call "%~dp0tailkey.local.cmd"

where python.exe >nul 2>nul
if not errorlevel 1 (
  python.exe server.py
  exit /b
)

where py.exe >nul 2>nul
if not errorlevel 1 (
  py.exe -3 server.py
  exit /b
)

set "BUNDLED_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%BUNDLED_PYTHON%" (
  "%BUNDLED_PYTHON%" server.py
  exit /b
)

echo Python 3 was not found. Install Python 3 or add it to PATH, then run this file again.
pause
