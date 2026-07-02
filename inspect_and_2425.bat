@echo off
cd /d "%~dp0"
python -m pip install openai >nul 2>&1
echo ===== INSPECT Facilities / Packaging =====
python -m tools.inspect_fac_pkg
echo.
type "%~dp0output\facpkg_inspect.txt"
echo.
echo ===== BUILD Q24, Q25 =====
for %%Q in (24 25) do (
  echo ----- QUESTION %%Q -----
  python -m capture.engine --qid %%Q
  python -m generate.doc_generator %%Q
  python -m intelligence.verify %%Q
)
echo.
echo DONE.
pause
