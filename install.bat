@echo off
REM ==============================================================================
REM Script Cai Dat Toan Bo Dependencies Cho Tools Scrawl Documentation & RAG Pipeline
REM Ho tro: Windows
REM ==============================================================================
chcp 65001 >nul
echo =================================================================
echo [INFO] BAT DAU CAI DAT MOI TRUONG VA DEPENDENCIES TRUONG WINDOWS
echo =================================================================

REM 1. Kiem tra Python
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Khong tim thay Python! Vui long cai dat Python >= 3.10 va tick vao "Add Python to PATH".
    pause
    exit /b 1
)

echo [OK] Da tim thay Python.

REM 2. Tao Virtual Environment
if not exist ".venv" (
    echo [INFO] Dang tao virtual environment tai .venv...
    python -m venv .venv
    echo [OK] Da tao virtual environment.
) else (
    echo [INFO] Virtual environment .venv da ton tai.
)

REM 3. Kich hoat Virtual Environment
call .venv\Scripts\activate.bat

REM 4. Nang cap pip
echo [INFO] Nang cap pip...
python -m pip install --upgrade pip

REM 5. Cai dat dependencies
echo [INFO] Dang cai dat thu vien tu requirements.txt...
pip install -r requirements.txt

REM 6. Kiem tra import
echo.
echo [INFO] Dang kiem tra import cac thu vien cot loi...
python -c "import httpx, bs4, docx, pypdf, pdfplumber, markdown_it, numpy, torch, transformers; print('[OK] Moi thu vien da san sang!')"

echo.
echo =================================================================
echo [SUCCESS] CAI DAT HOAN TAT THANH CONG!
echo =================================================================
echo De su dung, hay kich hoat moi truong:
echo    .venv\Scripts\activate
echo.
echo Sau do chay:
echo    python crawl.py -i
echo =================================================================
pause
