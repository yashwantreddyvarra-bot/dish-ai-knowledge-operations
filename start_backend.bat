@echo off
title DISH Backend for Streamlit
cd /d "%~dp0"

echo ============================================================
echo   DISH Backend - connects Streamlit Cloud to this PC
echo ============================================================
echo.

if not exist "venv\Scripts\python.exe" (
  echo ERROR: venv not found. Run: python -m venv venv
  echo        then: venv\Scripts\pip install -r requirements.txt
  echo        then: venv\Scripts\playwright install chromium
  pause
  exit /b 1
)

echo [1/2] Starting server.py on port 5000...
start "DISH server.py" cmd /k "cd /d %~dp0 && venv\Scripts\activate && python server.py"

timeout /t 4 /nobreak >nul

echo [2/2] Starting tunnel (Cloudflare)...
echo.
echo COPY the https://....trycloudflare.com URL below
echo and paste it in Streamlit Secrets as:
echo.
echo   BACKEND_URL = "https://YOUR-URL-HERE"
echo.
echo Then reboot your Streamlit app.
echo.
echo KEEP THIS WINDOW OPEN while people use the chatbot.
echo ============================================================
echo.

where cloudflared >nul 2>&1
if %errorlevel%==0 (
  cloudflared tunnel --url http://localhost:5000
) else (
  echo cloudflared not installed.
  echo Download from: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
  echo Or use ngrok:  ngrok http 5000
  echo.
  pause
)
