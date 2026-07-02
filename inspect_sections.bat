@echo off
cd /d "%~dp0"
echo Inspecting French menus / Periods / Promotions (nav + Add buttons)...
python -m tools.inspect_sections
echo.
type "%~dp0output\sections_inspect.txt"
echo.
pause
