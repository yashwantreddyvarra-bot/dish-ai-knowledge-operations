@echo off
cd /d "%~dp0"
python -m pip install openai flask pillow playwright --break-system-packages >nul 2>&1
echo ===== Dump product-edit form (for Q07 fix) =====
python -m tools.inspect_product
echo.
echo ===== Re-capture + re-verify Q22 (fixed highlights) =====
python -m capture.engine --qid 22
python -m generate.doc_generator 22
python -m intelligence.verify 22
echo.
echo DONE.
pause
