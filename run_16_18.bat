@echo off
cd /d "%~dp0"
echo Rebuilding Q16-Q18 (fixed navigation + Add buttons) with vision verify...
python -m pip install openai >nul 2>&1
python -m playwright install chromium >nul 2>&1
for %%Q in (16 17 18) do (
  echo ----- QUESTION %%Q -----
  python -m capture.engine --qid %%Q
  python -m generate.doc_generator %%Q
  python -m intelligence.verify %%Q
)
echo.
echo DONE Q16-Q18.
start "" "%~dp0output\docs"
pause
