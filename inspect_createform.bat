@echo off
cd /d "%~dp0"
echo Inspecting Add product form dropdowns...
python -m tools.inspect_createform
echo Done.
pause
