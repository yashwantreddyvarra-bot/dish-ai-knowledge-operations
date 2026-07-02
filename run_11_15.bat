@echo off
cd /d "%~dp0"
echo Building Q11-Q15 (live capture w/ model-pick + self-check, then vision verify)
python -m pip install openai >nul 2>&1
python -m playwright install chromium >nul 2>&1
for %%Q in (11 12 13 14 15) do (
  echo ===== QUESTION %%Q =====
  python -m capture.engine --qid %%Q
  python -m generate.doc_generator %%Q
  python -m intelligence.verify %%Q
)
echo.
echo ALL DONE Q11-Q15.  Reports in output\verify_qNN.json
start "" "%~dp0output\docs"
pause
