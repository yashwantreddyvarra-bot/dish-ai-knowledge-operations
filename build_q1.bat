@echo off
cd /d "%~dp0"
echo Rebuilding Q1 PDF + video from the existing live screenshots...
python -m generate.doc_generator 1
echo Done. Opening output folder...
start "" "%~dp0output\docs"
pause
