@echo off
cd /d "%~dp0"
echo ============================================================
echo   DISH Docs - LIVE capture + build for QUESTION 2
echo   Adjusting product details in the list view
echo ============================================================
python -m pip install -r requirements.txt >nul 2>&1
python -m playwright install chromium >nul 2>&1
echo [capture] logging into DISH POS and screenshotting each step...
python -m capture.engine --qid 2
echo [build] making branded PDF + video...
python -m generate.doc_generator 2
echo Done. Opening output folder...
start "" "%~dp0output\docs"
pause
