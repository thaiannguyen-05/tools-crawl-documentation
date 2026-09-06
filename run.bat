@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    echo [THÔNG BÁO] Chưa tìm thấy môi trường ảo .venv. Đang tiến hành cài đặt...
    call install.bat
    if %ERRORLEVEL% NEQ 0 (
        echo [LỖI] Cài đặt thất bại.
        pause
        exit /b %ERRORLEVEL%
    )
)

call .venv\Scripts\activate.bat
python crawl.py -i
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Chương trình kết thúc với lỗi.
    pause
)
