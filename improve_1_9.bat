@echo off
cd /d "%~dp0"
echo Closed-loop improvement for Q1-Q9 (verify -> re-capture w/ model-pick -> re-verify)
python -m pip install openai >nul 2>&1
python -m playwright install chromium >nul 2>&1
python -m intelligence.improve 1-9
echo.
echo Done. Per-step reports in output\verify_qNN.json
pause
