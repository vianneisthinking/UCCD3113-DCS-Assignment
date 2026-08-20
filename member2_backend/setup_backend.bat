@echo off
title Set Up Ticket Management Backend API
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

if not exist ".env" (
    echo Creating .env from .env.example...
    copy ".env.example" ".env" >nul
)

echo.
echo Loading sample data...
python seed.py

echo.
echo Setup completed.
echo Run start_backend.bat to start the backend API.
pause
