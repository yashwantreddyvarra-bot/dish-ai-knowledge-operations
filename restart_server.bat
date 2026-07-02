@echo off
cd /d "%~dp0"
echo Stopping any running server...
taskkill /F /IM python.exe >nul 2>&1
timeout /t 2 >nul
echo Starting DISH chatbot server...
start "DISH chatbot" cmd /k python server.py
echo Server starting in a new window. Open http://127.0.0.1:5000
timeout /t 3 >nul
