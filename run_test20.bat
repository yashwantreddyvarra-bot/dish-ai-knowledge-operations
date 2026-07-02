@echo off
cd /d "%~dp0"
python -m pip install openai flask pillow playwright reportlab imageio imageio-ffmpeg --break-system-packages >nul 2>&1
python -m playwright install chromium >nul 2>&1
echo ===========================================================
echo  20-QUESTION FULL CHECK (steps + PDF screenshots + video)
echo  Product questions are built LIVE with that product first.
echo  Takes a while (a few live captures) - let it finish.
echo ===========================================================
python -m tools.test_20
echo.
echo Done. Report: output\test20_results.txt
pause
