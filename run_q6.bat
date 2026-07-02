@echo off
cd /d "%~dp0"
echo DISH Docs - LIVE capture + build for QUESTION 6 (Allergens and additives)
python -m pip install -r requirements.txt >nul 2>&1
python -m playwright install chromium >nul 2>&1
python -m capture.engine --qid 6
python -m generate.doc_generator 6
start "" "%~dp0output\docs"
pause
