@echo off
chcp 65001 >nul
title 鳴潮體力監控工具

echo ==========================================
echo       鳴潮體力監控工具 - 啟動中
echo ==========================================

:: 1. 檢查並拉取 GitHub 更新
set "NEED_PIP=0"
if exist ".git" (
    echo [*] 正在檢查 GitHub 更新...
    for /f "tokens=*" %%i in ('git pull origin main 2^>^&1') do (
        echo %%i
        echo %%i | findstr /V /C:"Already up to date." >nul && set "NEED_PIP=1"
    )
) else (
    echo [i] 未偵測到 Git 倉庫，略過更新。
)

echo.

:: 2. 檢查或建立虛擬環境
if not exist "venv\Scripts\python.exe" (
    echo [*] 首次執行，正在建立虛擬環境 venv...
    python -m venv venv
    set "NEED_PIP=1"
)

:: 3. 只有在首次建立環境 或 程式碼有更新時才檢查套件
if "%NEED_PIP%"=="1" (
    if exist "requirements.txt" (
        echo [*] 偵測到新版本或新環境，正在安裝/更新套件...
        "venv\Scripts\python.exe" -m pip install -r requirements.txt
    )
)

echo.
echo [*] 正在啟動主程式並關閉控制台視窗...

:: 4. 背景啟動 GUI 並立即關閉 CMD
start "" "venv\Scripts\pythonw.exe" main_gui.py

exit