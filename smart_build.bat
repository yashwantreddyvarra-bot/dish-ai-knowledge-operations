@echo off
REM Usage:  smart_build.bat <qid> <path-to-official-pdf>
REM   Plans the steps from the PDF, captures live, builds PDF+video, and self-checks.
cd /d "%~dp0"
if "%~2"=="" (
  echo Usage: smart_build.bat ^<qid^> ^<path-to-official-pdf^>
  pause & exit /b 1
)
python -m pip install -r requirements.txt >nul 2>&1
python -m playwright install chromium >nul 2>&1
python -m intelligence.orchestrator %1 "%~2"
echo.
echo Self-check report: output\verify_q%1.json
start "" "%~dp0output\docs"
pause
