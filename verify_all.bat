@echo off
REM Self-check every built question and print a quality score + flagged steps.
cd /d "%~dp0"
for /L %%Q in (1,1,25) do python -m intelligence.verify %%Q
echo.
echo Reports written to output\verify_qNN.json
pause
