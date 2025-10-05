@echo off
REM Arduino Telemetri Arayuzu - Virtual Environment Kurulum Scripti
REM Tum Python versiyonlari icin uyumlu

echo ========================================
echo Arduino Telemetri Arayuzu Kurulum
echo ========================================
echo.

REM Mevcut Python versiyonunu tespit et
python --version >nul 2>&1
if errorlevel 1 (
    py --version >nul 2>&1
    if errorlevel 1 (
        echo HATA: Python bulunamadi!
        echo Lutfen Python yukleyip kurun.
        echo Python indirme: https://python.org/downloads/
        pause
        exit /b 1
    ) else (
        set PYTHON_CMD=py
    )
) else (
    set PYTHON_CMD=python
)

echo Python bulundu:
%PYTHON_CMD% --version
echo.

REM Python versiyonunu kontrol et (minimum 3.7)
for /f "tokens=2 delims= " %%a in ('%PYTHON_CMD% --version 2^>^&1') do set PYTHON_VERSION=%%a
for /f "tokens=1,2 delims=." %%a in ("%PYTHON_VERSION%") do (
    set MAJOR=%%a
    set MINOR=%%b
)

if %MAJOR% LSS 3 (
    echo HATA: Python 3.7+ gereklidir. Mevcut surum: %PYTHON_VERSION%
    pause
    exit /b 1
)

if %MAJOR% EQU 3 if %MINOR% LSS 7 (
    echo HATA: Python 3.7+ gereklidir. Mevcut surum: %PYTHON_VERSION%
    pause
    exit /b 1
)

echo Python %PYTHON_VERSION% uyumlu!
echo.

REM Virtual environment olustur
echo Virtual environment olusturuluyor...
%PYTHON_CMD% -m venv telemetri_env

if not exist "telemetri_env" (
    echo HATA: Virtual environment olusturulamadi!
    pause
    exit /b 1
)

echo Virtual environment basariyla olusturuldu!
echo.

REM Virtual environment'i aktif et
echo Virtual environment aktif ediliyor...
call telemetri_env\Scripts\activate.bat

REM pip'i guncelle
echo pip guncelleniyor...
python -m pip install --upgrade pip

REM Gereksinimleri yukle
echo Gerekli kutuphaneler yukleniyor...
echo Bu islem birkaC dakika surebilir...
echo.

pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo HATA: Bazi kutuphaneler yuklenemedi!
    echo Lutfen internet baglantinizi kontrol edin.
    pause
    exit /b 1
)

echo.
echo ========================================
echo KURULUM TAMAMLANDI!
echo ========================================
echo.
echo Uygulamayi calistirmak icin:
echo 1. run_app.bat dosyasini calistirin
echo    VEYA
echo 2. Asagidaki komutlari manuel olarak calistirin:
echo    telemetri_env\Scripts\activate.bat
echo    python main.py
echo.
echo Sanal ortamdan cikmak icin: deactivate
echo.
pause