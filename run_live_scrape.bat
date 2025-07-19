@echo off
:: Game Agent Data Scraper - Live Mode
:: This script runs continuous live scraping (press Ctrl+C to stop)

echo ========================================
echo Game Agent Data Scraper - Live Mode
echo ========================================
echo.
echo This will start continuous live scraping.
echo Press Ctrl+C at any time to stop.
echo.

:: Activate virtual environment
call "%~dp0venv_aipredict\Scripts\activate.bat"

if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment!
    echo Please make sure venv_aipredict exists and is properly configured.
    pause
    exit /b 1
)

:: Run live scraping
echo Starting live scraping...
echo.
python "%~dp0scraper_shell.py" --mode live

:: Check exit code
if errorlevel 1 (
    echo.
    echo ERROR: Live scraping failed!
) else (
    echo.
    echo Live scraping stopped.
)

echo.
echo Press any key to exit...
pause >nul
