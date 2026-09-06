@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    echo =================================================================
    echo [THONG BAO] Chua thay thu muc .venv. Dang chuyen sang cai dat...
    echo =================================================================
    call install.bat
    if %ERRORLEVEL% NEQ 0 (
        echo [LOI] Cai dat khong thanh cong.
        pause
        exit /b %ERRORLEVEL%
    )
)

echo [INFO] Dang kich hoat moi truong ao .venv...
call .venv\Scripts\activate.bat

echo [INFO] Khoi chay Document Crawler...
python crawl.py -i
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [THONG BAO] Chuong trinh da ket thuc voi ma loi: %ERRORLEVEL%
    pause
)
