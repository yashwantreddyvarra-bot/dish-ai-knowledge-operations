@echo off
cd /d "%~dp0"
echo ===========================================================
echo  FINAL TESTS  (run AFTER rebuild_all.bat has finished)
echo  1) the original 25 questions
echo  2) the 100 random questions (covers all 25, fresh wordings)
echo  Both report routing + PDF / Video / Steps scores.
echo ===========================================================
python -m pip install openai flask --break-system-packages >nul 2>&1
echo.
echo ===== TEST 1: ORIGINAL 25 =====
python -m tools.test_originals
echo.
echo ===== TEST 2: 100 RANDOM (representative of a larger batch) =====
python -m tools.chat_smoketest3
echo.
echo ===========================================================
echo  Done. Reports: output\test_originals_results.txt
echo                 output\test100_results.txt
echo ===========================================================
pause
