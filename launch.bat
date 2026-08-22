@echo off
title Super Lab Suite - Gel Genie ^& AI Colony Counter
cd /d "%~dp0"
echo Launching Super Lab Suite...
python run.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo An error occurred while launching the application.
    pause
)
