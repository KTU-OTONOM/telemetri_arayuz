@echo off
REM Arduino Telemetri Arayuzu - Evrensel Calistirma Scripti

echo Arduino Telemetri Arayuzu Baslatiliyor...
echo =========================================

REM Virtual environment var mi kontrol et
if exist "telemetri_env\Scripts\activate.bat" (
    echo Virtual environment bulundu, aktif ediliyor...
    call telemetri_env\Scripts\activate.bat && python main.py
) else (
    echo Virtual environment bulunamadi, sistem Python kullaniliyor...
    echo Not: Daha iyi performans icin setup_env.bat calistirin.
    
    REM Sistem Python'unu tespit et
    python --version >nul 2>&1
    if errorlevel 1 (
        py --version >nul 2>&1
        if errorlevel 1 (
            echo HATA: Python bulunamadi!
            echo Lutfen Python yukleyin veya setup_env.bat calistirin.
            pause
            exit /b 1
        ) else (
            py main.py
        )
    ) else (
        python main.py
    )
)

if %errorlevel% neq 0 (
    echo.
    echo Uygulama calistirilirken hata olustu!
    echo.
    echo Cozum onerileri:
    echo 1. setup_env.bat dosyasini calistirin (onerilir)
    echo 2. Gerekli paketlerin yuklu oldugunu kontrol edin
    echo 3. Python 3.7+ yuklu oldugunu dogrulayin
    echo.
    pause
)