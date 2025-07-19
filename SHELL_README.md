# Game Agent Data Scraper - Shell Mode

This project now supports both GUI and shell-based execution. The shell mode provides the same functionality as the GUI but runs from the command line.

## Quick Start

1. **Setup (one-time)**:
   ```bash
   setup.bat
   ```

2. **Run Bulk Scraping**:
   ```bash
   run_bulk_scrape.bat
   ```

3. **Run Live Scraping**:
   ```bash
   run_live_scrape.bat
   ```

## Execution Options

### Simple Batch Files

- **`run_bulk_scrape.bat`** - One-time bulk scraping with credential prompts
- **`run_live_scrape.bat`** - Continuous live scraping with credential prompts  
- **`setup.bat`** - Initial setup and dependency installation

### Advanced Usage

**Batch with arguments:**
```batch
run_scraper.bat bulk --phone 1234567890
run_scraper.bat live --phone 1234567890 --password mypassword
```

**PowerShell with type safety:**
```powershell
.\run_scraper.ps1 -Mode bulk
.\run_scraper.ps1 -Mode live -Phone "82284608240"
# For secure password input:
.\run_scraper.ps1 -Mode bulk -Phone "82284608240" -Password (Read-Host "Enter password" -AsSecureString)
```

**Direct Python execution:**
```bash
# Activate environment first
.\venv_aipredict\Scripts\Activate.ps1

# Run scraper
python scraper_shell.py --mode bulk
python scraper_shell.py --mode live --phone 1234567890
```

## Credential Management

**✅ Your credentials are now configured!**
- Phone: 82284608240
- Password: [Set in environment variables]

### Pre-configured (Your Current Setup)
Your credentials have been set as environment variables. Simply run:
```batch
run_bulk_scrape.bat    # Will use your saved credentials automatically
run_live_scrape.bat    # Will use your saved credentials automatically
```

### Alternative Options

#### Option 1: Environment Variables (Already Set)
```batch
# Your current configuration (already done):
# PHONE_NUMBER=82284608240
# PASSWORD=Dh4910va

# To update credentials, run:
set_credentials.bat
# or
set_credentials.ps1
```

#### Option 2: Command Line Arguments
```batch
run_scraper.bat bulk --phone 82284608240 --password Dh4910va
```

#### Option 3: Interactive Prompts
Just run the scripts without any setup - you'll be prompted to enter credentials.

## Features

### Bulk Scraping Mode
- One-time historical data collection
- Progress tracking via console logs
- Automatic completion and exit
- Same functionality as GUI "Start Scraping" button

### Live Scraping Mode  
- Continuous real-time data monitoring
- **Auto-stop conditions**:
  - After 100 iterations without new data  
  - After 30 minutes of runtime
  - Manual stop with Ctrl+C
- Automatic reconnection on errors
- Same functionality as GUI "Start Live Scrape" button

### Error Handling
- Graceful shutdown on interruption
- Automatic browser cleanup
- Detailed error logging
- Exit codes for script chaining

## File Structure

```
├── scraper_shell.py      # Main shell scraper implementation
├── run_bulk_scrape.bat   # Simple bulk scraping launcher
├── run_live_scrape.bat   # Simple live scraping launcher  
├── run_scraper.bat       # Advanced launcher with arguments
├── run_scraper.ps1       # PowerShell launcher with SecureString support
├── setup.bat             # One-time setup script
├── set_credentials.bat   # Set environment variables (Batch)
├── set_credentials.ps1   # Set environment variables (PowerShell)
├── stop_live_scraping.bat # Emergency stop for live scraping
├── test_setup.bat        # Test and validate complete setup
└── SHELL_README.md       # This file
```

## Differences from GUI

**What's the same:**
- Identical scraping logic and data processing
- Same configuration file (`config.yaml`)
- Same output format and file location
- Same browser automation and API interception

**What's different:**
- No graphical interface or progress bars
- Console-based logging instead of GUI widgets
- Command-line credential input
- Ctrl+C for stopping instead of GUI buttons

## Troubleshooting

**Virtual environment issues:**
```bash
# Recreate environment
setup.bat
```

**Permission issues (PowerShell):**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Browser issues:**
- Same troubleshooting as GUI mode
- Check `logs/performance.log` for details
- Ensure ChromeDriver compatibility

### ⚠️ Live Scraping Safety Features

Live scraping mode now includes automatic stopping conditions to prevent infinite execution:

- **Time Limit**: Maximum 30 minutes runtime
- **Iteration Limit**: Maximum 100 cycles
- **Empty Response Limit**: Stops after 50 consecutive empty API responses
- **User Confirmation**: Requires explicit confirmation before starting live mode

### 🛑 Emergency Stop

If live scraping gets stuck, use:
```bash
stop_live_scraping.bat
```
This will terminate all running Python processes related to the scraper.

## Advanced Configuration

All settings from `config.yaml` apply to shell mode:
- XPath selectors under `xpaths` section
- Timeouts under `timeouts` section  
- URLs under `web_agent` section
- Logging under `logging` section

## Integration Examples

**Scheduled tasks:**
```batch
schtasks /create /tn "DataScraper" /tr "C:\path\to\run_bulk_scrape.bat" /sc daily /st 09:00
```

**Batch processing:**
```batch
for /f %%i in (accounts.txt) do (
    run_scraper.bat bulk --phone %%i
)
```

**CI/CD integration:**
```yaml
- name: Run data scraping
  run: |
    .\setup.bat
    .\run_scraper.bat bulk --phone ${{ secrets.PHONE }} --password ${{ secrets.PASSWORD }}
```
