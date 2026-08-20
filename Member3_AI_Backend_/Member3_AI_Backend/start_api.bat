@echo off
title AI Customer Support Ticket API
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
) else (
    set "PYTHON=python"
)

echo ==============================================
echo AI Customer Support Ticket API
echo ==============================================
echo Documentation: http://127.0.0.1:8000/docs
echo Health check:  http://127.0.0.1:8000/health
echo.

"%PYTHON%" -m uvicorn api.main:app --host 127.0.0.1 --port 8000

echo.
echo API server has stopped.
pause
