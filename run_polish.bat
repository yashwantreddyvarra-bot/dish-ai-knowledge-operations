@echo off
cd /d "%~dp0"
python -m pip install openai >nul 2>&1
echo Polishing Q16/17/18/23 with precise form-field selectors...
for %%Q in (16 17 18 23) do (
  echo ----- QUESTION %%Q -----
  python -m capture.engine --qid %%Q
  python -m generate.doc_generator %%Q
  python -m intelligence.verify %%Q
)
echo.
echo DONE.
start "" "%~dp0output\docs"
pause
