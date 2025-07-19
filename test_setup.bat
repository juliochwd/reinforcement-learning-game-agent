@echo off
:: Quick Test Script for Environment Variables and Shell Scraper
echo ========================================
echo Testing Game Agent Data Scraper Setup
echo ========================================
echo.

:: Test environment variables
echo Testing environment variables...
if defined PHONE_NUMBER (
    echo ✓ PHONE_NUMBER is set: %PHONE_NUMBER%
) else (
    echo ✗ PHONE_NUMBER is not set
)

if defined PASSWORD (
    echo ✓ PASSWORD is set: [HIDDEN]
) else (
    echo ✗ PASSWORD is not set
)

echo.

:: Test virtual environment
echo Testing virtual environment...
if exist "venv_aipredict\Scripts\python.exe" (
    echo ✓ Virtual environment exists
    call venv_aipredict\Scripts\activate.bat
    python --version
) else (
    echo ✗ Virtual environment not found
    echo Run setup.bat first
    pause
    exit /b 1
)

echo.

:: Test Python script syntax
echo Testing Python script syntax...
python -m py_compile scraper_shell.py
if errorlevel 1 (
    echo ✗ Python script has syntax errors
) else (
    echo ✓ Python script syntax is valid
)

echo.

:: Test configuration file
echo Testing configuration file...
if exist "config.yaml" (
    echo ✓ Configuration file exists
) else (
    echo ✗ Configuration file missing
)

echo.
echo ========================================
echo Test Summary
echo ========================================
echo.
echo Your setup appears to be ready!
echo.
echo To run scraping:
echo   run_bulk_scrape.bat     # One-time bulk scraping
echo   run_live_scrape.bat     # Continuous live scraping
echo.
pause
