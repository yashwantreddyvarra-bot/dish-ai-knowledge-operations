@echo off
cd /d "%~dp0"
python -m pip install openai flask pillow playwright reportlab imageio imageio-ffmpeg --break-system-packages >nul 2>&1
python -m playwright install chromium >nul 2>&1
echo ===== Re-capturing Q1 (dropdown-select fix) as the standard reference =====
python -m tools.build_tailored "Sparkling Water" 3.50
echo ===== Verifying Q1 =====
python -m intelligence.verify 1
echo.
echo ===== Re-running the 50-question content check from #1 =====
python -m tools.test_50_content
echo.
pause
