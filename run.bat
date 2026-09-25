@echo off
chcp 65001 >nul
title 鳴潮體力監控助手 - 環境檢查與啟動器

echo ======================================================
echo    正在檢測本機 Python 環境與套件依賴...
echo ======================================================

:: 1. 檢測電腦是否安裝 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [警告] 尚未檢測到 Python 環境！
    echo 正在自動開啟瀏覽器前往 Python 3.11 官方下載頁面...
    start https://www.python.org/downloads/release/python-3118/
    echo.
    echo 請在安裝時務必勾選【Add python.exe to PATH】選項！
    echo 安裝完成後，請重新雙擊此 run.bat 啟動。
    pause
    exit /b
)

:: 2. 檢測虛擬環境 (venv)，沒有就自動建立
if not exist "venv\" (
    echo [首次運行] 正在為本專案建立獨立虛擬環境 (venv)...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [錯誤] 虛擬環境建立失敗！請確認 Python 支援 venv。
        pause
        exit /b
    )
)

:: 3. 啟用獨立虛擬環境
call venv\Scripts\activate.bat

:: 4. 檢查並自動安裝 PyTorch (CPU 穩定版)
python -c "import torch" >nul 2>&1
if %errorlevel% neq 0 (
    echo [安裝中] 正在下載並安裝 PyTorch (約 150MB，請稍候)...
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
)

:: 5. 檢查並自動安裝其餘必要套件
python -c "import easyocr, pyautogui, pygetwindow, requests, PIL" >nul 2>&1
if %errorlevel% neq 0 (
    echo [安裝中] 正在安裝其餘相依套件 (EasyOCR, PyAutoGUI, 等)...
    pip install -r requirements.txt
)

echo ======================================================
echo    環境檢查完成，正在啟動主程式...
echo ======================================================

:: 6. 啟動 GUI 主程式
python main_gui.py

pause