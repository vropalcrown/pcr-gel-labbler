@echo off
title Super Lab Suite - Create Desktop Shortcut
cd /d "%~dp0"
echo Creating Desktop shortcut for Super Lab Suite on this computer...
python create_shortcut.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [NOTE] If Python is not installed yet, please install Python 3.10+ from python.org
    echo and ensure "Add Python to PATH" is checked during setup.
    echo.
)
pause
