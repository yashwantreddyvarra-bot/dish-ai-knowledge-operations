@echo off
cd /d "%~dp0"
python -m pip install openai flask pillow playwright reportlab imageio imageio-ffmpeg --break-system-packages >nul 2>&1
python -m playwright install chromium >nul 2>&1
echo Running 10-question MODE B test (live builds, ~20 min on this laptop)...
python -m tools.test_modeB
echo.
echo Done. Proof images in output\ (proofB_*.png)
pause
