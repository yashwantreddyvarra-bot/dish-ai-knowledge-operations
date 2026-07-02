@echo off
cd /d "%~dp0"
echo ===========================================================
echo  EVALUATING all 25 documents /100 (vision check every frame)
echo  This calls GPT-4o per step - on an older laptop it can take
echo  several minutes. Please let it finish.
echo ===========================================================
python -m pip install openai flask pillow --break-system-packages >nul 2>&1
python -m tools.evaluate_docs
echo.
echo ===========================================================
echo  Done. Report: output\doc_evaluation.txt
echo ===========================================================
pause
