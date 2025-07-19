@echo off
:: Game Agent Data Scraper - Bulk Mode
:: This script runs a one-time bulk scraping operation

echo ========================================
echo Game Agent Data Scraper - Bulk Mode
echo ========================================
echo.

:: Activate virtual environment
call "%~dp0venv_aipredict\Scripts\activate.bat"

if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment!
    echo Please make sure venv_aipredict exists and is properly configured.
    pause
    exit /b 1
)

:: Run bulk scraping
echo Starting bulk scraping...
echo.
python "%~dp0scraper_shell.py" --mode bulk

:: Check exit code
if errorlevel 1 (
    echo.
    echo ERROR: Bulk scraping failed!
) else (
    echo.
    echo SUCCESS: Bulk scraping completed!
)

echo.
echo Press any key to exit...
pause >nul
