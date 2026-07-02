@echo off
cd /d "%~dp0"
python -m pip install openai flask pillow playwright reportlab imageio imageio-ffmpeg --break-system-packages >nul 2>&1
echo ===== Building Q1 live with product = "Burger" (proves it is dynamic) =====
python -m tools.build_tailored "Burger" 7.50
echo.
echo Done. Open the newest Q01 PDF/video - the form should show "Burger".
pause
