@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo =================================================================
echo [INFO] DANG KIEM TRA MOI TRUONG PYTHON...
echo =================================================================

REM 1. Thu python truoc, neu khong duoc thi thu py -3
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
    echo =================================================================
    echo [LOI] Khong tim thay Python tren may tinh cua ban!
    echo =================================================================
    echo Nguyen nhan thuong gap:
    echo 1. Ban chua cai Python:
    echo    Vui long vao https://www.python.org/downloads/ de tai Python.
    echo    Luu y: Trong man hinh cai dat dau tien, hay TICH CHON:
    echo           [v] Add python.exe to PATH
    echo.
    echo 2. Ban da cai Python nhung chua tick Add to PATH:
    echo    Hay go "Manage App Execution Aliases" tren Windows de kiem tra,
    echo    hoac chay lai bo cai Python, chon "Modify" va tick "Add to PATH".
    echo =================================================================
    echo.
    pause
    exit /b 1
)

echo [OK] Da tim thay: %PY_CMD%
%PY_CMD% --version
echo.

REM 2. Tao moi truong ao .venv
if not exist ".venv" (
    echo [INFO] Dang tao moi truong ao .venv...
    %PY_CMD% -m venv .venv
    if %ERRORLEVEL% NEQ 0 (
        echo [LOI] Khong the tao thu muc .venv!
        pause
        exit /b 1
    )
    echo [OK] Da tao xong moi truong ao .venv.
) else (
    echo [INFO] Moi truong ao .venv da ton tai san.
)

REM 3. Kich hoat moi truong ao
if not exist ".venv\Scriptsctivate.bat" (
    echo [LOI] Khong tim thay file .venv\Scriptsctivate.bat!
    pause
    exit /b 1
)

echo [INFO] Dang kich hoat .venv...
call .venv\Scriptsctivate.bat

REM 4. Nang cap pip
echo.
echo [INFO] Dang nang cap pip...
python -m pip install --upgrade pip

REM 5. Cai dat dependencies tu requirements.txt
echo.
echo [INFO] Dang cai dat thu vien tu requirements.txt (Co the mat 2-5 phut)...
pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [CANH BAO] Cai dat bang PyPI mac dinh gap loi (thuong do mang hoac PyTorch).
    echo Dang thu cai PyTorch CPU nhe (~200MB) truoc...
    pip install torch --index-url https://download.pytorch.org/whl/cpu
    pip install -r requirements.txt
)

REM 6. Health check kiem tra import
echo.
echo =================================================================
echo [INFO] Kiem tra cac thu vien da cai dat...
echo =================================================================
python -c "import httpx, bs4, docx, pypdf, pdfplumber, markdown_it, numpy, torch, transformers; print('[OK] TAT CA THU VIEN DA SAN SANG!')"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [CANH BAO] Co thu vien chua load duoc. Ban hay xem loi o tren.
    pause
    exit /b 1
)

echo.
echo =================================================================
echo [THANH CONG] CAI DAT HOAN TAT TREN WINDOWS!
echo =================================================================
echo Ban co the click dup vao file 'run.bat' de bat dau chay crawler.
echo =================================================================
echo.
pause
