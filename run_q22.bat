@echo off
cd /d "%~dp0"
python -m pip install openai >nul 2>&1
echo Rebuilding Q22 (exact Menu-tab selector)...
python -m capture.engine --qid 22
python -m generate.doc_generator 22
python -m intelligence.verify 22
echo.
echo DONE Q22.
pause
