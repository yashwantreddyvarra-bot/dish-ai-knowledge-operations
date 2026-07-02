@echo off
cd /d "%~dp0"
python -m pip install openai flask pillow playwright reportlab imageio imageio-ffmpeg --break-system-packages >nul 2>&1
echo ===== Building Q1 live with "Mojito" =====
python -m tools.build_tailored "Mojito" 6.50
echo ===== Building Q1 live with "Caesar Salad" =====
python -m tools.build_tailored "Caesar Salad" 9.00
echo.
echo Done. Proof images: output\proof_Mojito.png and output\proof_Caesar_Salad.png
pause
