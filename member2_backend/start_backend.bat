@echo off
title Ticket Management Backend API
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
) else (
    set "PYTHON=python"
)

echo ==============================================
echo Ticket Management Backend API
echo ==============================================
echo Documentation: http://127.0.0.1:8001/docs
echo Health check:  http://127.0.0.1:8001/health
echo.
echo Member 3's AI service should be running on port 8000.
echo The backend still accepts tickets if it is not.
echo.

"%PYTHON%" -m uvicorn api.main:app --host 127.0.0.1 --port 8001

echo.
echo Backend API has stopped.
pause
