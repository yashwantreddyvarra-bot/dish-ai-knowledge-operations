@echo off
cd /d "%~dp0"
python -m pip install openai flask pillow playwright --break-system-packages >nul 2>&1
echo ===== Re-capture + re-verify Q07 (exact product-form selectors) =====
python -m capture.engine --qid 7
python -m generate.doc_generator 7
python -m intelligence.verify 7
echo.
echo DONE Q07.
pause
