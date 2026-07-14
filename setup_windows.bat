@echo off
title DISH - one-time Windows setup
cd /d "%~dp0"
echo Installing Python packages (first time only, may take a few minutes)...
if not exist "venv\Scripts\python.exe" (
  python -m venv venv
)
call venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
playwright install chromium
echo.
echo ============================================================
echo   Setup complete. Now double-click:  start_backend.bat
echo ============================================================
pause
