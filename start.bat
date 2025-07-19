@echo off
:: Game Agent Data Scraper - Unified Control Center
:: Main launcher with comprehensive menu system

:MAIN_MENU
cls
echo(
echo ==========================================
echo      Game Agent Data Scraper v2.0
echo      Unified Control Center
echo ==========================================
echo(
echo [+] SCRAPING OPERATIONS:
echo [1] Bulk Scraping           - One-time historical data collection
echo [2] Live Scraping           - Continuous real-time monitoring
echo [3] Live + AI Analysis      - Live scraping with Gemini AI
echo(
echo [S] SETUP and MAINTENANCE:
echo [4] Initial Setup           - Install dependencies and environment
echo [5] Set Credentials         - Update phone number and password
echo [6] Test Environment        - Validate setup and credentials
echo(
echo [A] AI and ANALYSIS:
echo [7] Gemini AI Test          - Test AI prediction capabilities
echo [8] Analyze Existing Data   - Run AI analysis on saved data
echo(
echo [D] DATA and UTILITIES:
echo [9] Fetch External Data     - Download data from custom URL
echo [10] View Current Data      - Display recent scraping results
echo [11] Backup Data            - Create data backup
echo(
echo [H] HELP and INFO:
echo [12] Show Help              - Detailed usage information
echo [13] View Logs              - Check recent activity logs
echo [14] System Status          - Environment and dependency status
echo(
echo [0] Exit
echo(
set /p choice="Enter your choice (0-14): "

if "%choice%"=="1" goto BULK_SCRAPE
if "%choice%"=="2" goto LIVE_SCRAPE
if "%choice%"=="3" goto LIVE_AI_SCRAPE
if "%choice%"=="4" goto INITIAL_SETUP
if "%choice%"=="5" goto SET_CREDENTIALS
if "%choice%"=="6" goto TEST_SETUP
if "%choice%"=="7" goto GEMINI_TEST
if "%choice%"=="8" goto ANALYZE_DATA
if "%choice%"=="9" goto FETCH_DATA
if "%choice%"=="10" goto VIEW_DATA
if "%choice%"=="11" goto BACKUP_DATA
if "%choice%"=="12" goto SHOW_HELP
if "%choice%"=="13" goto VIEW_LOGS
if "%choice%"=="14" goto SYSTEM_STATUS
if "%choice%"=="0" goto EXIT
if "%choice%"=="exit" goto EXIT
if "%choice%"=="quit" goto EXIT

echo(
echo [X] Invalid choice. Please enter 0-14.
timeout /t 2 >nul
goto MAIN_MENU

:BULK_SCRAPE
echo(
echo ==========================================
echo [+] Starting Bulk Scraping Mode
echo ==========================================
echo(
echo This will perform one-time historical data collection.
echo * Data will be saved to: data/databaru_from_api.csv
echo * Logs will be saved to: logs/performance.log
echo(
echo Press any key to start or Ctrl+C to cancel...
pause >nul
call :ACTIVATE_ENV
if errorlevel 1 goto MAIN_MENU
echo(
echo >> Starting scraper with configured credentials...
python scraper_shell.py --mode bulk
call :CHECK_RESULT "Bulk scraping"
goto MAIN_MENU

:LIVE_SCRAPE
echo(
echo ==========================================
echo [S] Starting Live Scraping Mode
echo ==========================================
echo(
echo (!)  WARNING: This starts CONTINUOUS monitoring!
echo (!)  Process runs until you stop it or auto-stop triggers.
echo(
echo (S) Auto-stop conditions:
echo   * After 100 iterations without new data
echo   * After 30 minutes of runtime
echo   * After 50 consecutive empty responses
echo(
echo [C] Controls:
echo   * Press Ctrl+C at ANY TIME to stop gracefully
echo   * Use stop_live_scraping.bat for emergency stop
echo(
set /p confirm="Type 'YES' to continue with live scraping: "
if /i not "%confirm%"=="YES" goto :CANCEL_LIVE_SCRAPE
call :ACTIVATE_ENV
if errorlevel 1 goto MAIN_MENU
echo(
echo >> Starting live scraper...
echo Press Ctrl+C at any time to stop...
echo(
python scraper_shell.py --mode live
call :CHECK_RESULT "Live scraping"
goto MAIN_MENU
:CANCEL_LIVE_SCRAPE
echo [X] Live scraping cancelled.
timeout /t 2 >nul
goto MAIN_MENU

:LIVE_AI_SCRAPE
echo(
echo ==========================================
echo [A] Starting Live Scraping + AI Analysis
echo ==========================================
echo(
echo This combines live scraping with Gemini AI analysis.
echo * Real-time data collection
echo * Automatic AI prediction reports
echo * Enhanced pattern analysis
echo(
call :CHECK_GEMINI_KEY
if errorlevel 1 goto MAIN_MENU
echo(
set "ai_model=gemini-2.5-flash"
set /p model="Choose AI model (1=gemini-2.5-flash, 2=gemini-2.5-pro) [1]: "
if "%model%"=="2" set "ai_model=gemini-2.5-pro"
echo(
echo Selected model: %ai_model%
echo(
set /p confirm="Type 'YES' to start live scraping with AI: "
if /i not "%confirm%"=="YES" goto :CANCEL_AI_SCRAPE
call :ACTIVATE_ENV
if errorlevel 1 goto MAIN_MENU
echo(
echo >> Starting AI-enhanced live scraper...
echo >> AI Model: %ai_model%
echo(
python scraper_shell.py --mode live --model %ai_model%
call :CHECK_RESULT "AI-enhanced live scraping"
goto MAIN_MENU
:CANCEL_AI_SCRAPE
echo [X] AI scraping cancelled.
timeout /t 2 >nul
goto MAIN_MENU

:INITIAL_SETUP
echo(
echo ==========================================
echo [S] Initial Setup and Environment Creation
echo ==========================================
echo(
echo This will:
echo * Create Python virtual environment
echo * Install all required dependencies
echo * Validate ChromeDriver compatibility
echo * Set up directory structure
echo(
echo This may take 5-10 minutes depending on your connection...
echo(
pause
echo(
echo >> Running initial setup...
call setup.bat
echo(
echo [V] Setup completed. Press any key to return to menu...
pause >nul
goto MAIN_MENU

:GEMINI_TEST
echo(
echo ==========================================
echo [A] Testing Gemini AI Integration
echo ==========================================
echo(
call :CHECK_GEMINI_KEY
if errorlevel 1 goto MAIN_MENU
call :ACTIVATE_ENV
if errorlevel 1 goto MAIN_MENU
echo(
echo [T] Testing Gemini AI with sample data...
echo(
python -c "import sys; from src.rl_agent.gemini_predictor import GeminiPredictor; sys.stdout.reconfigure(encoding='utf-8');\
try: \
    predictor = GeminiPredictor('gemini-2.5-flash'); \
    result = predictor.generate_holistic_report('Test data: 12345'); \
    print('[V] Gemini AI Test SUCCESSFUL!'); \
    print('Sample Response:'); \
    print('-' * 40); \
    print(result); \
    print('-' * 40); \
except Exception as e: \
    print(f'[X] Gemini AI Test FAILED: {e}')"
echo(
echo Press any key to return to menu...
pause >nul
goto MAIN_MENU

:ANALYZE_DATA
echo(
echo ==========================================
echo [+] Analyze Existing Data with AI
echo ==========================================
echo(
call :CHECK_GEMINI_KEY
if errorlevel 1 goto MAIN_MENU
call :ACTIVATE_ENV
if errorlevel 1 goto MAIN_MENU
echo(
if exist "data\databaru_from_api.csv" goto :ANALYZE_DATA_EXISTS
echo [X] No data file found at data\databaru_from_api.csv
echo Please run scraping first to generate data.
echo(
echo Press any key to return to menu...
pause >nul
goto MAIN_MENU
:ANALYZE_DATA_EXISTS
echo(
echo [A] Analyzing existing data with Gemini AI...
echo(
python -c "import sys; import pandas as pd; from src.rl_agent.gemini_predictor import GeminiPredictor; sys.stdout.reconfigure(encoding='utf-8');\
try: \
    df = pd.read_csv('data/databaru_from_api.csv'); \
    latest_data = df.tail(10).to_string(); \
    predictor = GeminiPredictor('gemini-2.5-flash'); \
    analysis = predictor.generate_holistic_report(f'Latest 10 records: {latest_data}'); \
    print('[R] GEMINI AI ANALYSIS REPORT'); \
    print('=' * 50); \
    print(analysis); \
    print('=' * 50); \
except Exception as e: \
    print(f'[X] Analysis failed: {e}')"
echo(
echo Press any key to return to menu...
pause >nul
goto MAIN_MENU

:FETCH_DATA
echo(
echo ==========================================
echo [D] Fetch Data from External URL
echo ==========================================
echo(
call :ACTIVATE_ENV
if errorlevel 1 goto MAIN_MENU
echo(
set /p url="Enter URL to fetch data from: "
if "%url%"=="" goto :FETCH_DATA_NO_URL
echo(
set /p method="HTTP Method (GET/POST) [GET]: "
if /i "%method%"=="" set method=GET
echo(
echo >> Fetching data from: %url%
echo Method: %method%
echo(
python -c "import sys; import requests; import json; import os; sys.stdout.reconfigure(encoding='utf-8');\
try: \
    if '%method%'.upper() == 'POST': \
        response = requests.post('%url%'); \
    else: \
        response = requests.get('%url%'); \
    response.raise_for_status(); \
    os.makedirs('data', exist_ok=True); \
    if 'application/json' in response.headers.get('content-type', ''): \
        data = response.json(); \
        with open('data/fetched_data.json', 'w') as f: \
            json.dump(data, f, indent=2); \
        print(f'[V] JSON data saved to: data/fetched_data.json'); \
        print(f'Records fetched: {len(data) if isinstance(data, list) else 1}'); \
    else: \
        with open('data/fetched_data.txt', 'w', encoding='utf-8') as f: \
            f.write(response.text); \
        print(f'[V] Text data saved to: data/fetched_data.txt'); \
        print(f'Size: {len(response.text)} characters'); \
except Exception as e: \
    print(f'[X] Fetch failed: {e}')"
echo(
echo Press any key to return to menu...
pause >nul
goto MAIN_MENU
:FETCH_DATA_NO_URL
echo [X] No URL provided.
timeout /t 2 >nul
goto MAIN_MENU

:VIEW_DATA
echo(
echo ==========================================
echo [F] View Current Data
echo ==========================================
echo(
if exist "data\databaru_from_api.csv" goto :VIEW_DATA_EXISTS
echo [X] No scraping data found.
echo Run scraping operations first to generate data.
goto :VIEW_DATA_CONTINUE
:VIEW_DATA_EXISTS
echo [+] Latest scraping results:
echo(
python -c "import sys; import pandas as pd; sys.stdout.reconfigure(encoding='utf-8');\
try: \
    df = pd.read_csv('data/databaru_from_api.csv'); \
    print(f'Total records: {len(df)}'); \
    print('Latest 5 records:'); \
    print('-' * 30); \
    print(df.tail().to_string(index=False)); \
    print('-' * 30); \
    print(f'Date range: {df.iloc[0,0] if len(df) > 0 else 'N/A'} to {df.iloc[-1,0] if len(df) > 0 else 'N/A'}'); \
except Exception as e: \
    print(f'Error reading data: {e}')"
:VIEW_DATA_CONTINUE
echo(
echo [F] Other data files:
dir /b data\ 2>nul
echo(
echo Press any key to return to menu...
pause >nul
goto MAIN_MENU

:BACKUP_DATA
echo(
echo ==========================================
echo [B] Backup Data
echo ==========================================
echo(
set "backup_dir=backup\backup_%date:~-4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
set "backup_dir=%backup_dir: =0%"
echo Creating backup directory: %backup_dir%
mkdir "%backup_dir%" 2>nul
echo(
echo [B] Backing up data files...
if exist "data\" (
    xcopy /E /I /Y "data\*" "%backup_dir%\data\" >nul
    echo [V] Data files backed up
) else (
    echo (!) No data directory found
)
echo(
echo [B] Backing up configuration...
if exist "config.yaml" (
    copy "config.yaml" "%backup_dir%\" >nul
    echo [V] Configuration backed up
)
echo(
echo [B] Backing up logs...
if exist "logs\" (
    xcopy /E /I /Y "logs\*" "%backup_dir%\logs\" >nul
    echo [V] Logs backed up
) else (
    echo (!) No logs directory found
)
echo(
echo [V] Backup completed: %backup_dir%
echo(
echo Press any key to return to menu...
pause >nul
goto MAIN_MENU

:VIEW_LOGS
echo(
echo ==========================================
echo [C] View Recent Activity Logs
echo ==========================================
echo(
if exist "logs\performance.log" goto :VIEW_LOGS_EXISTS
echo [X] No performance log found.
echo Run scraping operations to generate logs.
goto :VIEW_LOGS_CONTINUE
:VIEW_LOGS_EXISTS
echo [+] Latest performance log entries:
echo(
python -c "import sys; sys.stdout.reconfigure(encoding='utf-8');\
try: \
    with open('logs/performance.log', 'r', encoding='utf-8') as f: \
        lines = f.readlines(); \
    print('Last 15 log entries:'); \
    print('-' * 50); \
    for line in lines[-15:]: \
        print(line.strip()); \
    print('-' * 50); \
except Exception as e: \
    print(f'Error reading logs: {e}')"
:VIEW_LOGS_CONTINUE
echo(
echo [F] Available log files:
dir /b logs\ 2>nul
echo(
echo Press any key to return to menu...
pause >nul
goto MAIN_MENU

:SYSTEM_STATUS
echo(
echo ==========================================
echo [R] System Status and Environment Check
echo ==========================================
echo(
echo Python Environment:
if exist "venv_aipredict\Scripts\python.exe" goto :SYS_STATUS_VENV_EXISTS
echo [X] Virtual environment: NOT FOUND
echo Please run option 4 (Initial Setup) first.
goto :SYS_STATUS_VENV_END
:SYS_STATUS_VENV_EXISTS
echo [V] Virtual environment: READY
call venv_aipredict\Scripts\activate.bat
python --version
echo(
echo Key packages:
python -c "import sys; sys.stdout.reconfigure(encoding='utf-8'); packages = ['selenium', 'seleniumwire', 'customtkinter', 'pandas', 'pyyaml', 'google-genai', 'cryptography']; \
for pkg in packages: \
    try: \
        __import__(pkg.replace('-', '_')); \
        print(f'[V] {pkg}: INSTALLED'); \
    except ImportError: \
        print(f'[X] {pkg}: MISSING')"
:SYS_STATUS_VENV_END
echo(
echo [K] Credentials Status:
if defined PHONE_NUMBER (echo [V] Phone number: CONFIGURED) else (echo [X] Phone number: NOT SET)
if defined PASSWORD (echo [V] Password: CONFIGURED) else (echo [X] Password: NOT SET)
if defined GEMINI_API_KEY (echo [V] Gemini API key: CONFIGURED) else (echo (!) Gemini API key: NOT SET (AI features disabled))
echo(
echo [F] Directory Structure:
for %%d in (data logs backup src venv_aipredict) do (
    if exist "%%d\" (echo [V] %%d: EXISTS) else (echo [X] %%d: MISSING)
)
echo(
echo Network and Dependencies:
ping -n 1 google.com >nul 2>&1
if errorlevel 1 (echo [X] Internet connection: UNAVAILABLE) else (echo [V] Internet connection: AVAILABLE)
echo(
echo Press any key to return to menu...
pause >nul
goto MAIN_MENU

:SET_CREDENTIALS
echo(
echo ==========================================
echo [K] Set Credentials and API Keys
echo ==========================================
echo(
call set_credentials.bat
echo(
echo Press any key to return to menu...
pause >nul
goto MAIN_MENU

:TEST_SETUP
echo(
echo ==========================================
echo [T] Test Environment and Credentials
echo ==========================================
echo(
call test_setup.bat
echo(
echo Press any key to return to menu...
pause >nul
goto MAIN_MENU

:SHOW_HELP
echo(
echo ==========================================
echo [H] Game Agent Data Scraper - Help Guide
echo ==========================================
echo(
echo SCRAPING MODES:
echo(
echo BULK SCRAPING:
echo   * Collects historical data from Win Go platform
echo   * Runs once and exits when complete
echo   * Progress shown in real-time
echo   * Data saved to: data/databaru_from_api.csv
echo(
echo LIVE SCRAPING:
echo   * Continuously monitors for new game results
echo   * Runs until manually stopped or auto-stop triggers
echo   * Automatically reconnects on errors
echo   * Real-time data collection and processing
echo(
echo LIVE + AI ANALYSIS:
echo   * Combines live scraping with Gemini AI
echo   * Real-time prediction reports
echo   * Enhanced pattern analysis
echo   * Requires GEMINI_API_KEY
echo(
echo [A] AI FEATURES:
echo   * Gemini 2.5 Flash: Faster, cost-effective
echo   * Gemini 2.5 Pro: More comprehensive analysis
echo   * Custom analysis prompts in gemini_gems/
echo   * Real-time and batch analysis modes
echo(
echo [S] TECHNICAL INFO:
echo(
echo CREDENTIALS (Currently configured):
echo   * Phone: Uses environment variables or prompts
echo   * Password: Securely stored in environment
echo   * Gemini API: Optional for AI features
echo(
echo FILES CREATED:
echo   * Virtual environment: venv_aipredict/
echo   * Output data: data/databaru_from_api.csv
echo   * Logs: logs/performance.log, logs/scraper_shell.log
echo   * Backups: backup/ directory with timestamps
echo(
echo AUTO-STOP CONDITIONS:
echo   * Time limit: 30 minutes maximum
echo   * Iteration limit: 100 cycles maximum
echo   * Empty response limit: 50 consecutive
echo   * Manual stop: Ctrl+C anytime
echo(
echo TROUBLESHOOTING:
echo   * Browser issues: Check ChromeDriver compatibility
echo   * Permission errors: Run as administrator
echo   * Network issues: Check internet connection
echo   * Environment errors: Re-run Initial Setup
echo   * AI errors: Verify GEMINI_API_KEY
echo(
echo [+] DATA FORMATS:
echo   * CSV: Period (game ID), Number (result)
echo   * JSON: Structured data from external sources
echo   * Logs: Timestamped activity records
echo   * Backups: Complete system state snapshots
echo(
echo Press any key to return to menu...
pause >nul
goto MAIN_MENU

:: Helper Functions
:ACTIVATE_ENV
echo [+] Activating virtual environment...
if exist "venv_aipredict\Scripts\activate.bat" goto :ACTIVATE_ENV_EXISTS
echo [X] Virtual environment not found!
echo Please run Initial Setup (option 4).
echo(
echo Press any key to return to menu...
pause >nul
exit /b 1
:ACTIVATE_ENV_EXISTS
call venv_aipredict\Scripts\activate.bat
if errorlevel 1 goto :ACTIVATE_ENV_FAIL
echo [V] Virtual environment activated.
exit /b 0
:ACTIVATE_ENV_FAIL
echo [X] Failed to activate virtual environment!
echo(
echo Press any key to return to menu...
pause >nul
exit /b 1

:CHECK_GEMINI_KEY
if defined GEMINI_API_KEY goto :CHECK_GEMINI_KEY_EXISTS
echo [X] GEMINI_API_KEY not found in environment variables.
echo(
echo To use AI features, you need to:
echo 1. Get an API key from: https://aistudio.google.com/app/apikey
echo 2. Use option 5 (Set Credentials) to configure it.
echo 3. Or set it manually: set GEMINI_API_KEY=your_key_here
echo(
echo Press any key to return to menu...
pause >nul
exit /b 1
:CHECK_GEMINI_KEY_EXISTS
echo [V] Gemini API key found.
exit /b 0

:CHECK_RESULT
if errorlevel 1 goto :CHECK_RESULT_FAIL
echo [V] %~1 completed successfully!
goto :CHECK_RESULT_END
:CHECK_RESULT_FAIL
echo [X] %~1 failed or was interrupted.
echo Check the error messages above for details.
:CHECK_RESULT_END
echo(
echo Press any key to return to menu...
pause >nul
exit /b 0

:EXIT
echo(
echo ==========================================
echo       Thank you for using
echo    Game Agent Data Scraper v2.0
echo ==========================================
echo(
echo [+] Session Summary:
if exist "data\databaru_from_api.csv" (
    python -c "import sys; import pandas as pd; sys.stdout.reconfigure(encoding='utf-8');\
try: \
    df = pd.read_csv('data/databaru_from_api.csv'); \
    print(f'* Total records collected: {len(df)}'); \
    if len(df) > 0: \
        print(f'* Latest record: {df.iloc[-1,0]}'); \
except: \
    print('* Data file exists but could not be read')" 2>nul
) else (
    echo * No data collected this session
)
echo(
echo [L] Resources:
echo * Documentation: README.md
echo * Logs: logs/ directory
echo * Backups: backup/ directory
echo * Configuration: config.yaml
echo(
echo Have a great day!
echo(
exit /b 0
