@echo off
title Attendance System Auto Setup
color 0A

echo ==========================================
echo   Attendance System - Auto Setup & Run
echo ==========================================
echo.

cd /d %~dp0

echo [1] Checking Python 3.10...
py -3.10 --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo ❌ Python 3.10 غير موجود
    echo الرجاء تثبيته ثم إعادة المحاولة
    pause
    exit
)
echo ✔ Python 3.10 موجود
echo.

echo [2] Creating virtual environment...
IF NOT EXIST venv (
    py -3.10 -m venv venv
    echo ✔ تم إنشاء venv
) ELSE (
    echo ✔ venv موجود مسبقاً
)
echo.

echo [3] Activating environment...
call venv\Scripts\activate
echo ✔ تم تفعيل البيئة
echo.

echo [4] Updating pip...
python -m pip install --upgrade pip >nul
echo ✔ تم تحديث pip
echo.

echo [5] Installing dependencies...
pip install -r requirements.txt

echo.
echo [6] Checking dlib...
pip install dlib --only-binary=:all: >nul 2>&1
echo ✔ تم فحص dlib
echo.

echo [7] Running Application...
python main.py

echo.
echo ==========================================
echo   Application Closed
echo ==========================================
pause