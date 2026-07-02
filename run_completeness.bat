@echo off
cd /d "%~dp0"
python -m pip install openai flask --break-system-packages >nul 2>&1
echo Running completeness test (polish ON, checks all steps kept)...
python -m tools.test_completeness
echo.
echo Done. Report: output\completeness_results.txt
pause
