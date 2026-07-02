@echo off
cd /d "%~dp0"
echo ===========================================================
echo  DISH chatbot ROUND 2 (50 fresh questions + PDF/video checks)
echo ===========================================================
python -m pip install flask openai --break-system-packages >nul 2>&1
python -m tools.chat_smoketest2
echo.
echo ===========================================================
echo  Done. Transcript: output\chat_smoketest2_results.txt
echo ===========================================================
pause
