@echo off
chcp 65001 >nul
title 鳴潮體力監控工具 - 啟動中

echo ======================================================
echo           [鳴潮體力小工具] 正在檢查環境與更新
echo ======================================================

:: 1. 檢查並更新 Git 程式碼 (僅在 Git 倉庫環境生效)
if exist ".git" (
    echo [*] 正在檢查 GitHub 版本更新...
    :: 抓取遠端最新資訊
    git fetch origin main >nul 2>&1
    :: 檢查本地與遠端是否有落後
    git status -uno | findstr /C:"Your branch is behind" >nul 2>&1
    if not errorlevel 1 (
        echo [!] 發現新版本！正在自動更新程式碼...
        git pull origin main
        echo [+] 程式碼更新完成！
    ) else (
        echo [+] 程式碼已是最新版本。
    )
) else (
    echo [i] 未偵測到 Git 儲存庫，略過線上更新。
)

echo.

:: 2. 檢查或建立 Python 虛擬環境
if not exist "venv\Scripts\activate.bat" (
    echo [*] 正在建立虛擬環境 venv...
    python -m venv venv
    if errorlevel 1 (
        echo [X] 建立虛擬環境失敗，請確認已安裝 Python！
        pause
        exit /b
    )
)

:: 3. 啟用虛擬環境
call venv\Scripts\activate.bat

:: 4. 自動檢查並補齊缺失的 Python 套件
if exist "requirements.txt" (
    echo [*] 正在檢查套件依賴 (requirements.txt)...
    pip install -r requirements.txt --quiet
)

echo.
echo ======================================================
echo               [啟動成功] 正在開啟主介面...
echo ======================================================
echo.

:: 5. 啟動主程式
python main_gui.py

pause