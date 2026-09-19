@echo off
title Gel Labeler - One-Click Dependency Installer
cd /d "%~dp0"
echo ========================================================
echo   Gel Labeler - Installing Required Libraries
echo ========================================================
echo.
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not added to your Windows PATH.
    echo Please download and install Python from https://www.python.org/downloads/
    echo IMPORTANT: Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

echo Installing PyQt6, OpenCV, Pillow, Python-PPTX, NumPy, and PyFlakes...
python -m pip install -r requirements.txt

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================================
    echo   [SUCCESS] All dependencies installed successfully!
    echo   You can now run launch.bat or use your Desktop shortcut.
    echo ========================================================
) else (
    echo.
    echo [ERROR] Failed to install dependencies. Check your internet connection.
)
echo.
pause
