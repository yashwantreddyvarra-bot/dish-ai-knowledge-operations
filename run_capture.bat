@echo off
cd /d "%~dp0"
set QID=%1
if "%QID%"=="" set QID=1
echo ============================================================
echo   DISH Docs - LIVE capture + build for question %QID%
echo ============================================================
python -m pip install -r requirements.txt >nul 2>&1
python -m playwright install chromium >nul 2>&1
echo [capture] logging into DISH POS and screenshotting each step...
python -m capture.engine --qid %QID%
echo [build] making branded PDF + video...
python -m generate.doc_generator %QID%
echo Done. Opening output folder...
start "" "%~dp0output\docs"
pause
