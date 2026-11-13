@echo off
cd /d "%~dp0"
start "" pythonw run.py 2>nul
if %ERRORLEVEL% NEQ 0 (
    python run.py
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Python is not found in PATH.
        pause
    )
)
