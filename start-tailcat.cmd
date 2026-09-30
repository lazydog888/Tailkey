@echo off
setlocal
cd /d "%~dp0"
call start-webrtc.cmd --tailcat %*
