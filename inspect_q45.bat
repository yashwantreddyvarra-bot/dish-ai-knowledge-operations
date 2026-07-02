@echo off
cd /d "%~dp0"
echo Inspecting DISH POS selectors for Q4 (composites) + Q5 (search/filter)...
python -m tools.inspect_q45
echo Done.
pause
