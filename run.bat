@echo off
title WW AutoTool Launcher

REM 1. Check Git Update
set "NEED_PIP=0"
if exist ".git" (
    echo [*] Checking updates from GitHub...
    for /f "tokens=*" %%i in ('git pull origin main 2^>^&1') do (
        echo %%i
        echo %%i | findstr /V /C:"Already up to date." >nul && set "NEED_PIP=1"
    )
) else (
    echo [i] No .git folder found. Skipping online update.
)

REM 2. Check Virtual Environment
if not exist "venv\Scripts\python.exe" (
    echo [*] Creating virtual environment...
    python -m venv venv
    set "NEED_PIP=1"
)

REM 3. Install Requirements if updated
if "%NEED_PIP%"=="1" (
    if exist "requirements.txt" (
        echo [*] Installing or updating dependencies...
        "venv\Scripts\python.exe" -m pip install -r requirements.txt
    )
)

REM 4. Launch GUI
echo [*] Starting main_gui.py...
start "" "venv\Scripts\pythonw.exe" main_gui.py

exit