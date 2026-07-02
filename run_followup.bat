@echo off
cd /d "%~dp0"
python -m pip install openai flask --break-system-packages >nul 2>&1
python -m tools.test_followup
echo.
pause
