@echo off
cd /d "%~dp0"
echo ===========================================================
echo  DISH chatbot end-to-end smoke test (50 questions via /api/chat)
echo ===========================================================
python -m pip install flask --break-system-packages >nul 2>&1
python -m tools.chat_smoketest
echo.
echo ===========================================================
echo  Done. Full transcript: output\chat_smoketest_results.txt
echo ===========================================================
pause
