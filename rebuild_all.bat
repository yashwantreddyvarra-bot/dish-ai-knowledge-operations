@echo off
cd /d "%~dp0"
echo ===========================================================
echo  FULL REBUILD FROM SCRATCH  (all 25 guides)
echo  Run this AFTER deleting output\docs, output\videos, output\vframes.
echo  Re-captures every guide live from the (fixed) recipes, rebuilds
echo  PDF + video, then scores PDF / Video / Steps for each.
echo  This is long on an older laptop - let it finish.
echo ===========================================================
python -m pip install openai flask pillow playwright reportlab imageio imageio-ffmpeg pdfplumber --break-system-packages >nul 2>&1
python -m playwright install chromium >nul 2>&1
for %%Q in (1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25) do (
  echo ----- BUILDING QUESTION %%Q -----
  python -m capture.engine --qid %%Q
  python -m generate.doc_generator %%Q
)
echo.
echo ===== SCORING ALL 25 (PDF / Video / Steps) =====
python -m tools.evaluate_docs
echo.
echo ===========================================================
echo  Rebuild complete. Scoreboard: output\doc_evaluation.txt
echo ===========================================================
pause
