@echo off
cd /d "%~dp0"
echo ============================================================
echo   DISH Docs - BULK live capture + build for Q8 through Q25
echo ============================================================
python -m pip install -r requirements.txt >nul 2>&1
python -m playwright install chromium >nul 2>&1
for %%Q in (8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25) do (
  echo.
  echo ===== QUESTION %%Q =====
  python -m capture.engine --qid %%Q
  python -m generate.doc_generator %%Q
)
echo.
echo ALL DONE Q8-Q25.
start "" "%~dp0output\docs"
pause
