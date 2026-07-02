@echo off
cd /d "%~dp0"
echo Dumping real form fields for French menu / period / promotion / packaging...
python -m tools.inspect_forms
echo.
type "%~dp0output\forms_inspect.txt"
echo.
pause
