@echo off
:: Game Agent Data Scraper - Advanced Usage
:: This script allows running with command line arguments

echo ========================================
echo Game Agent Data Scraper - Advanced Mode
echo ========================================
echo.
echo Usage examples:
echo   %~nx0 bulk                    - Run bulk scraping (will prompt for credentials)
echo   %~nx0 live                    - Run live scraping (will prompt for credentials)
echo   %~nx0 bulk --phone 1234567890 - Run bulk with phone number (will prompt for password)
echo.

if "%1"=="" (
    echo ERROR: Please specify mode (bulk or live)
    echo.
    goto :usage
)

if "%1"=="help" goto :usage
if "%1"=="-h" goto :usage
if "%1"=="--help" goto :usage

:: Activate virtual environment
call "%~dp0venv_aipredict\Scripts\activate.bat"

if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment!
    echo Please make sure venv_aipredict exists and is properly configured.
    pause
    exit /b 1
)

:: Run scraping with all arguments
echo Starting scraping in %1 mode...
echo.
python "%~dp0scraper_shell.py" --mode %1 %2 %3 %4 %5 %6 %7 %8 %9

:: Check exit code
if errorlevel 1 (
    echo.
    echo ERROR: Scraping failed!
) else (
    echo.
    echo SUCCESS: Scraping completed!
)

echo.
echo Press any key to exit...
pause >nul
exit /b 0

:usage
echo.
echo Available modes:
echo   bulk  - One-time bulk scraping of historical data
echo   live  - Continuous live scraping (press Ctrl+C to stop)
echo.
echo Optional arguments:
echo   --phone PHONE_NUMBER    - Login phone number
echo   --password PASSWORD     - Login password
echo.
echo Environment variables (alternative to arguments):
echo   PHONE_NUMBER - Login phone number
echo   PASSWORD     - Login password
echo.
echo Examples:
echo   %~nx0 bulk
echo   %~nx0 live
echo   %~nx0 bulk --phone 1234567890
echo   %~nx0 live --phone 1234567890 --password mypassword
echo.
pause
