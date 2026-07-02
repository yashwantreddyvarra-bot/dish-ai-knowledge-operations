@echo off
cd /d "%~dp0"
echo DISH Docs - LIVE capture + build for QUESTION 10 (Managing and adding products)
python -m pip install -r requirements.txt >nul 2>&1
python -m playwright install chromium >nul 2>&1
python -m capture.engine --qid 10
python -m generate.doc_generator 10
start "" "%~dp0output\docs"
pause
