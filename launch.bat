@echo off
title Super Lab Suite - Gel Genie ^& AI Colony Counter
cd /d "%~dp0"

echo ========================================================
echo   Launching Super Lab Suite...
echo ========================================================

python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Python is not installed on this computer.
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    echo (Make sure to check "Add Python to PATH" during installation)
    echo.
    pause
    exit /b 1
)

python -c "import PyQt6, cv2, pptx, PIL" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Missing required libraries detected on this computer.
    echo Automatically installing required libraries (PyQt6, OpenCV, PPTX, Pillow)...
    pip install -r requirements.txt
    if %ERRORLEVEL% NEQ 0 (
        echo.
        echo [ERROR] Could not install dependencies automatically.
        pause
        exit /b 1
    )
)

python run.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo An unexpected error occurred while running the application.
    pause
)
