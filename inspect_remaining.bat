@echo off
cd /d "%~dp0"
echo Inspecting filter panel / product-group edit / menu edit forms...
python -m tools.inspect_remaining
echo.
echo Saved to output\remaining_forms.txt
pause
