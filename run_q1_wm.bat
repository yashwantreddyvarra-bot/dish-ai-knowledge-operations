@echo off
cd /d "%~dp0"
python -m pip install openai flask pillow playwright reportlab imageio imageio-ffmpeg --break-system-packages >nul 2>&1
python -m playwright install chromium >nul 2>&1
echo Building Question 1: add a watermelon lemonade as a drink for 4.25
python -m tools.build_tailored "Watermelon Lemonade" 4.25
echo.
echo Done.
pause
