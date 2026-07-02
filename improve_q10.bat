@echo off
cd /d "%~dp0"
echo Closing the loop on Q10: verify -> re-capture (gpt-4o fills missing boxes) -> re-verify
python -m pip install openai >nul 2>&1
python -m intelligence.improve 10
echo.
pause
