@echo off
:: Set Environment Variables for Game Agent Data Scraper
:: This script sets up your credentials as environment variables

echo Setting up environment variables for Game Agent Data Scraper...
echo.

:: Set environment variables for current session
set PHONE_NUMBER=82284608240
set PASSWORD=Dh4910va
set GEMINI_API_KEY=AIzaSyDykHVvf8UFWXyotZDPE6tgFQ7OuTfesuQ

:: Set persistent environment variables (user-level)
setx PHONE_NUMBER "82284608240" >nul 2>&1
setx PASSWORD "Dh4910va" >nul 2>&1
setx GEMINI_API_KEY "AIzaSyDykHVvf8UFWXyotZDPE6tgFQ7OuTfesuQ" >nul 2>&1

if errorlevel 1 (
    echo WARNING: Could not set persistent environment variables.
    echo Variables are set for current session only.
) else (
    echo Environment variables set successfully!
    echo.
    echo PHONE_NUMBER: 82284608240
    echo PASSWORD: [HIDDEN]
    echo GEMINI_API_KEY: [HIDDEN]
)

echo.
echo These credentials will now be used automatically when running:
echo - run_bulk_scrape.bat
echo - run_live_scrape.bat
echo - run_scraper.bat (without --phone and --password arguments)
echo.
echo Note: You may need to restart your command prompt for persistent variables to take effect.
echo.
pause
