@echo off
REM Virtual Arduino Simulatörü Başlatma Scripti

echo ========================================
echo Virtual Arduino Telemetri Simulatörü
echo ========================================
echo.

REM Virtual environment kontrolü
if exist "telemetri_env\Scripts\activate.bat" (
    echo Virtual environment aktif ediliyor...
    call telemetri_env\Scripts\activate.bat
) else (
    echo Not: Virtual environment bulunamadi, sistem Python kullaniliyor...
)

REM Python'u tespit et
python --version >nul 2>&1
if errorlevel 1 (
    py --version >nul 2>&1
    if errorlevel 1 (
        echo HATA: Python bulunamadi!
        pause
        exit /b 1
    ) else (
        set PYTHON_CMD=py
    )
) else (
    set PYTHON_CMD=python
)

echo.
echo Simulatör başlatılıyor...
echo.
echo Telemetri arayüzünde:
echo   1. "Portları Yenile" butonuna basın
echo   2. "Virtual Arduino Simulator" portunu seçin
echo   3. "Bağlan" butonuna basın
echo.
echo Durdurmak için: Ctrl+C
echo.
echo ========================================
echo.

%PYTHON_CMD% virtual_arduino.py tcp

if errorlevel 1 (
    echo.
    echo Simulatör hatası oluştu!
    pause
)