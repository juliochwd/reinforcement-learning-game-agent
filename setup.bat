@echo off
:: Quick Setup Script for Game Agent Data Scraper
:: This script sets up the virtual environment and installs dependencies

echo ========================================
echo Game Agent Data Scraper - Quick Setup
echo ========================================
echo.

echo Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH!
    echo Please install Python 3.12.6 and try again.
    pause
    exit /b 1
)

echo Python found. Checking for Python 3.12...
py -3.12 --version >nul 2>&1
if errorlevel 1 (
    echo WARNING: Python 3.12 not found. Using default Python version...
    set PYTHON_CMD=python
) else (
    echo Python 3.12 found. Using Python 3.12...
    set PYTHON_CMD=py -3.12
)

echo.
echo Creating virtual environment 'venv_aipredict'...
%PYTHON_CMD% -m venv venv_aipredict

if errorlevel 1 (
    echo ERROR: Failed to create virtual environment!
    pause
    exit /b 1
)

echo.
echo Activating virtual environment...
call venv_aipredict\Scripts\activate.bat

echo.
echo Upgrading pip...
python -m pip install --upgrade pip

echo.
echo Installing required packages...
pip install selenium webdriver-manager pandas PyYAML selenium-wire customtkinter cryptography setuptools PyQt5 "blinker<1.8.0"

if errorlevel 1 (
    echo ERROR: Failed to install packages!
    pause
    exit /b 1
)

echo.
echo ========================================
echo Setup completed successfully!
echo ========================================
echo.
echo You can now run the scraper using:
echo   run_bulk_scrape.bat   - For one-time bulk scraping
echo   run_live_scrape.bat   - For continuous live scraping
echo   run_scraper.bat       - For advanced usage with arguments
echo.
echo Or use PowerShell:
echo   .\run_scraper.ps1 -Mode bulk
echo   .\run_scraper.ps1 -Mode live
echo.
pause
