@echo off
echo ==========================================
echo      Game Agent Data Scraper v2.0
echo      Unified Control Center
echo ==========================================
echo.
echo ** SCRAPING OPERATIONS:
echo [1] Bulk Scraping           - One-time historical data collection
echo [2] Live Scraping           - Continuous real-time monitoring
echo [3] Live + AI Analysis      - Live scraping with Gemini AI
echo.
echo ** SETUP MAINTENANCE:
echo [4] Initial Setup           - Install dependencies and environment
echo [5] Set Credentials         - Update phone number and password
echo [6] Test Environment        - Validate setup and credentials
echo.
echo ** AI ANALYSIS:
echo [7] Gemini AI Test          - Test AI prediction capabilities
echo [8] Analyze Existing Data   - Run AI analysis on saved data
echo.
echo ** DATA UTILITIES:
echo [9] Fetch External Data     - Download data from custom URL
echo [10] View Current Data      - Display recent scraping results
echo [11] Backup Data            - Create data backup
echo.
echo ** HELP INFO:
echo [12] Show Help              - Detailed usage information
echo [13] View Logs              - Check recent activity logs
echo [14] System Status          - Environment and dependency status
echo.
echo [0] Exit
echo.
echo System ready! You can now:
echo - Run bulk scraping: python scraper_shell.py --mode bulk --phone YOUR_PHONE
echo - Run live scraping: python scraper_shell.py --mode live --phone YOUR_PHONE
echo - Run AI analysis: python scraper_shell.py --mode live --phone YOUR_PHONE --model gemini-2.0-flash-exp
echo.
echo For interactive menu, please run this file in Command Prompt.
echo In PowerShell, use: cmd /c start.bat
pause
