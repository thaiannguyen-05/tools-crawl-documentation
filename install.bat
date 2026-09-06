@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo =================================================================
echo    TOOL CRAWL & RAG TRAINING DATA - WINDOWS INSTALLER
echo =================================================================
echo.

REM 1. Kiem tra Python
echo [BUOC 1/4] Kiem tra Python...
set "PY_CMD="
python --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "PY_CMD=python"
) else (
    py -3 --version >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        set "PY_CMD=py -3"
    )
)

if "%PY_CMD%"=="" (
    echo.
    echo ❌ [LOI] Khong tim thay Python!
    echo Vui long tai Python >= 3.10 tu https://www.python.org/downloads/
    echo Nho tick chon: [v] Add python.exe to PATH
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('%PY_CMD% --version') do set PY_VER=%%i
echo ✅ Phat hien: %PY_VER%
echo.

REM 2. Tao moi truong ao
echo [BUOC 2/4] Khoi tao moi truong ao .venv...
if not exist ".venv" (
    %PY_CMD% -m venv .venv
    if %ERRORLEVEL% NEQ 0 (
        echo ❌ Loi khi tao .venv
        pause
        exit /b 1
    )
    echo ✅ Da tao xong thu muc .venv
) else (
    echo ✅ Môi trường ảo .venv da co san
)

REM 3. Kich hoat .venv
call .venv\Scripts\activate.bat
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Khong kich hoat duoc .venv\Scripts\activate.bat
    pause
    exit /b 1
)

echo.
echo [BUOC 3/4] Cai dat thu vien crawl & xu ly tai lieu...
python -m pip install --upgrade pip --quiet
pip install httpx beautifulsoup4 tqdm pypdf pdfplumber python-docx markdown-it-py numpy pandas python-dotenv
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ⚠️ Buoc cai dat thu vien gap loi!
    pause
    exit /b 1
)
echo ✅ Da cai dat xong cac thu vien co ban.

echo.
echo [BUOC 4/4] Cai dat PyTorch & PhoBERT (Ban nhe CPU ~180MB, tai nhanh)...
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install transformers
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ⚠️ Cai dat PyTorch/Transformers gap loi!
    pause
    exit /b 1
)
echo ✅ Da cai dat xong PyTorch va PhoBERT.

echo.
echo =================================================================
echo [KIEM TRA] Kiem tra import tat ca cac thu vien...
echo =================================================================
python -c "import httpx, bs4, docx, pypdf, pdfplumber, markdown_it, numpy, torch, transformers, pandas; print('>>> TAT CA THU VIEN DA SAN SANG 100% <<<')"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ Kiem tra import gap loi.
    pause
    exit /b 1
)

echo.
echo =================================================================
echo 🎉 CHUC MUNG! CAI DAT THANH CONG TREN WINDOWS!
echo =================================================================
echo Ban co the click dup vao file 'run.bat' de bat dau chay crawler!
echo =================================================================
echo.
pause
