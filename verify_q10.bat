@echo off
cd /d "%~dp0"
echo Running vision self-check on Q10 (uses gpt-4o)...
python -m pip install openai >nul 2>&1
python -m intelligence.verify 10
echo.
pause
