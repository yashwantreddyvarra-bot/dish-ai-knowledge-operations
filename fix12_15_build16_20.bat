@echo off
cd /d "%~dp0"
python -m pip install openai >nul 2>&1
python -m playwright install chromium >nul 2>&1
echo ===== SAFE FIX: Q12, Q14, Q15 (accept-if-better) =====
python -m intelligence.improve 12 14 15
echo.
echo ===== BUILD: Q16-Q20 (capture + build + vision verify) =====
for %%Q in (16 17 18 19 20) do (
  echo ----- QUESTION %%Q -----
  python -m capture.engine --qid %%Q
  python -m generate.doc_generator %%Q
  python -m intelligence.verify %%Q
)
echo.
echo ALL DONE.  Reports in output\verify_qNN.json
start "" "%~dp0output\docs"
pause
