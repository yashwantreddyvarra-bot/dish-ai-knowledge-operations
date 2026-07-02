@echo off
cd /d "%~dp0"
python -m pip install openai >nul 2>&1
echo Building Q21-Q23 (Facilities + Packaging, real routes) with vision verify...
for %%Q in (21 22 23) do (
  echo ----- QUESTION %%Q -----
  python -m capture.engine --qid %%Q
  python -m generate.doc_generator %%Q
  python -m intelligence.verify %%Q
)
echo.
echo DONE Q21-Q23.
start "" "%~dp0output\docs"
pause
