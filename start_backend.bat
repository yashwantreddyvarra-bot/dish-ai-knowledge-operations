@echo off
title DISH Backend for Streamlit
cd /d "%~dp0"

echo ============================================================
echo   DISH Backend - connects Streamlit to this PC
echo ============================================================

if not exist "venv\Scripts\python.exe" (
  echo Run setup_windows.bat first.
  pause
  exit /b 1
)

echo [1/2] Starting server.py ...
start "DISH server.py" cmd /k "cd /d %~dp0 && call venv\Scripts\activate && python server.py"

timeout /t 5 /nobreak >nul

echo [2/2] Starting tunnel ...
echo.
echo >>> COPY the https URL below into Streamlit Secrets as BACKEND_URL <<<
echo.

if exist "%~dp0cloudflared.exe" (
  "%~dp0cloudflared.exe" tunnel --url http://localhost:5000
) else if exist "%LOCALAPPDATA%\Microsoft\WinGet\Links\cloudflared.exe" (
  cloudflared tunnel --url http://localhost:5000
) else (
  where cloudflared >nul 2>&1
  if %errorlevel%==0 (
    cloudflared tunnel --url http://localhost:5000
  ) else (
    echo cloudflared not found. Download cloudflared.exe into this folder:
    echo https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
    echo.
    echo OR use ngrok:  ngrok http 5000
    pause
  )
)
