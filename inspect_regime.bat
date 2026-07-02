@echo off
cd /d "%~dp0"
echo Inspecting General / Stores / Regime Forfettario location...
python -m tools.inspect_regime
echo Done.
pause
