@echo off
cd /d "%~dp0"
python -m pip install openai flask pillow reportlab imageio imageio-ffmpeg --break-system-packages >nul 2>&1
echo Rebuilding Q1 doc with the corrected caption...
python -m generate.doc_generator 1
echo.
echo Re-scoring all 25 with the verifier fixes (intro-step leniency)...
python -m tools.evaluate_docs
echo.
echo Done. Scoreboard: output\doc_evaluation.txt
pause
