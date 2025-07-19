@echo off
:: Stop Live Scraping Process
:: Run this script in another terminal to stop live scraping gracefully

echo ========================================
echo   Stop Live Scraping Process
echo ========================================
echo.

echo Looking for running Python scraper processes...
tasklist /FI "IMAGENAME eq python.exe" /FO TABLE | findstr "python.exe"

if errorlevel 1 (
    echo No Python processes found running.
    echo Live scraping may have already stopped.
) else (
    echo.
    echo Found Python processes. Attempting to stop gracefully...
    
    :: Send Ctrl+C signal to all Python processes
    for /f "tokens=2" %%i in ('tasklist /FI "IMAGENAME eq python.exe" /FO CSV ^| findstr "python.exe"') do (
        echo Stopping process ID: %%i
        taskkill /PID %%i /T
    )
    
    echo.
    echo Live scraping processes have been stopped.
)

echo.
echo Note: If you're still in the menu, you should see the process return to menu.
echo.
pause
