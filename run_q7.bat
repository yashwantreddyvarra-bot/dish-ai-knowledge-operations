@echo off
cd /d "%~dp0"
echo DISH Docs - LIVE capture + build for QUESTION 7 (Adjusting product details)
python -m pip install -r requirements.txt >nul 2>&1
python -m playwright install chromium >nul 2>&1
python -m capture.engine --qid 7
python -m generate.doc_generator 7
start "" "%~dp0output\docs"
pause
