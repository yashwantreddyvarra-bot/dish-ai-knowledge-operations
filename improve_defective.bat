@echo off
cd /d "%~dp0"
echo ===========================================================
echo  SAFE AUTO-IMPROVE (accept-if-better) on the 16 defective docs
echo  Re-captures live and keeps a result ONLY if its score rises.
echo  Long run on an older laptop - please let it finish.
echo ===========================================================
python -m pip install openai flask pillow playwright --break-system-packages >nul 2>&1
python -m playwright install chromium >nul 2>&1
python -m intelligence.improve 3 4 5 7 8 9 12 14 15 16 17 20 21 22 23 24
echo.
echo ===========================================================
echo  Done. Scores updated in output\verify_qNN.json
echo ===========================================================
pause
