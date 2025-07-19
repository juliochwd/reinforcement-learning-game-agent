# Game Agent Data Scraper - PowerShell Runner
# Provides better error handling and Windows integration

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("bulk", "live")]
    [string]$Mode,
    
    [string]$Phone,
    [SecureString]$Password,
    [switch]$Help
)

if ($Help) {
    Write-Host "Game Agent Data Scraper - PowerShell Runner" -ForegroundColor Cyan
    Write-Host "=============================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage:"
    Write-Host "  .\run_scraper.ps1 -Mode bulk                                    # Bulk scraping with prompted credentials"
    Write-Host "  .\run_scraper.ps1 -Mode live                                    # Live scraping with prompted credentials"
    Write-Host "  .\run_scraper.ps1 -Mode bulk -Phone 1234567890                 # Bulk with phone, prompted password"
    Write-Host "  .\run_scraper.ps1 -Mode live -Phone 123 -Password (Get-Credential).Password  # Live with SecureString password"
    Write-Host ""
    Write-Host "Modes:"
    Write-Host "  bulk  - One-time bulk scraping of historical data"
    Write-Host "  live  - Continuous live scraping (Ctrl+C to stop)"
    Write-Host ""
    Write-Host "Environment Variables (alternative):"
    Write-Host "  `$env:PHONE_NUMBER = 'your_phone'"
    Write-Host "  `$env:PASSWORD = 'your_password'"
    exit 0
}

if (-not $Mode) {
    Write-Host "ERROR: Mode parameter is required. Use -Help for usage information." -ForegroundColor Red
    exit 1
}

Write-Host "========================================" -ForegroundColor Green
Write-Host "Game Agent Data Scraper - $($Mode.ToUpper()) Mode" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Get script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Check if virtual environment exists
$VenvPath = Join-Path $ScriptDir "venv_aipredict"
$ActivateScript = Join-Path $VenvPath "Scripts\Activate.ps1"

if (-not (Test-Path $ActivateScript)) {
    Write-Host "ERROR: Virtual environment not found!" -ForegroundColor Red
    Write-Host "Expected path: $ActivateScript" -ForegroundColor Red
    Write-Host "Please run the setup first to create venv_aipredict" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

try {
    # Activate virtual environment
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    & $ActivateScript
    
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to activate virtual environment"
    }
    
    # Build command arguments
    $PythonScript = Join-Path $ScriptDir "scraper_shell.py"
    $CommandArgs = @("--mode", $Mode)
    
    if ($Phone) {
        $CommandArgs += @("--phone", $Phone)
    }
    
    if ($Password) {
        $PlainPassword = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($Password))
        $CommandArgs += @("--password", $PlainPassword)
    }
    
    # Show mode-specific information
    if ($Mode -eq "live") {
        Write-Host "Starting continuous live scraping..." -ForegroundColor Yellow
        Write-Host "Press Ctrl+C at any time to stop gracefully." -ForegroundColor Yellow
    } else {
        Write-Host "Starting one-time bulk scraping..." -ForegroundColor Yellow
    }
    Write-Host ""
    
    # Run the scraper
    $PythonExe = Join-Path $VenvPath "Scripts\python.exe"
    & $PythonExe $PythonScript @CommandArgs
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "SUCCESS: Scraping completed successfully!" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "ERROR: Scraping failed with exit code $LASTEXITCODE" -ForegroundColor Red
    }
    
} catch {
    Write-Host ""
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Full error details:" -ForegroundColor Red
    Write-Host $_.Exception.ToString() -ForegroundColor Red
} finally {
    Write-Host ""
    Read-Host "Press Enter to exit"
}
