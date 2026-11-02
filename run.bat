@echo off
setlocal
cd /d "%~dp0"
title CrowdPlay Arcade
where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher not found. Install Python 3.10 or newer from https://www.python.org/downloads/windows/
  echo During setup, select "Add Python to PATH".
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  echo Setting up CrowdPlay Arcade for first use...
  py -3 -m venv .venv
  if errorlevel 1 goto failed
)
if not exist ".venv\Scripts\flask.exe" (
  echo Installing required packages. Internet is needed for this first setup.
  ".venv\Scripts\python.exe" -m pip install --upgrade pip
  if errorlevel 1 goto failed
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 goto failed
)
if not exist ".env" copy ".env.example" ".env" >nul
echo.
echo Starting CrowdPlay Arcade. Keep this window open while you play.
echo Browser opens at http://127.0.0.1:5055/
echo Press Ctrl+C here to stop the server.
echo.
".venv\Scripts\python.exe" app.py
if errorlevel 1 goto failed
exit /b 0
:failed
echo.
echo Setup or startup failed. Read the message above, then try run.bat again.
pause
exit /b 1
