@echo off
cd /d "%~dp0"
echo Inspecting DISH POS sidebar General + Send selectors...
python -m tools.inspect_general
echo Done.
type "%~dp0output\general_inspect.txt"
pause
