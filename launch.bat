@echo off
cd /d "%~dp0"
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not found in PATH. Please run Install_Dependencies.bat first.
    pause
    exit /b 1
)
start "" pythonw run.py

