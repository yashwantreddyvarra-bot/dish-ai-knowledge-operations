@echo off
cd /d "%~dp0"
echo Vision self-review of Q1-Q10 (uses gpt-4o)...
python -m pip install openai >nul 2>&1
for /L %%Q in (1,1,10) do python -m intelligence.verify %%Q
echo.
echo Done. Reports written to output\verify_qNN.json
pause
