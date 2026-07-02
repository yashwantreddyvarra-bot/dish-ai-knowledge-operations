@echo off
cd /d "%~dp0"
echo Inspecting Store-edit (Q20) and Facility Menu-tab (Q22) forms...
python -m tools.inspect_q20_q22
echo.
type "%~dp0output\q20_q22_forms.txt"
echo.
pause
