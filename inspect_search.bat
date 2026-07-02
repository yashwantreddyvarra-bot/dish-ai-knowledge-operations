@echo off
cd /d "%~dp0"
python -m tools.inspect_search
echo.
type "%~dp0output\search_inspect.txt"
echo.
pause
