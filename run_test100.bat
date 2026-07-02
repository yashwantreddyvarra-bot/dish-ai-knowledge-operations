@echo off
cd /d "%~dp0"
echo ===========================================================
echo  100-QUESTION generalization + quality test (all 25 guides)
echo  Unrecognised wordings fall through to the GPT tier, so this
echo  may take a few minutes on an older laptop.
echo ===========================================================
python -m pip install openai flask --break-system-packages >nul 2>&1
python -m tools.chat_smoketest3
echo.
echo ===========================================================
echo  Done. Full transcript: output\test100_results.txt
echo ===========================================================
pause
