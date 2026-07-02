@echo off
cd /d "%~dp0"
echo Safe re-improve of Q5 and Q8 (self-checked picks + accept-if-better)...
python -m pip install openai >nul 2>&1
python -m playwright install chromium >nul 2>&1
python -m intelligence.improve 5 8
echo.
pause
