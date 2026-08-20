@echo off
title Set Up AI Customer Support Ticket API
cd /d "%~dp0"

echo Creating a local Python environment...
where py >nul 2>&1
if %errorlevel%==0 (
    py -3.11 -m venv .venv
) else (
    python -m venv .venv
)

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo ERROR: The virtual environment could not be created.
    echo Install Python 3.11 and ensure Python is available in PATH.
    pause
    exit /b 1
)

call ".venv\Scripts\activate.bat"

echo Installing required packages...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo.
echo Setup completed.
echo Run start_api.bat to start the AI API.
pause
