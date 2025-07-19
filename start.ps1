# Game Agent Data Scraper - Interactive PowerShell Menu
# Main launcher with colored menu selection

function Show-Menu {
    Clear-Host
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "    Game Agent Data Scraper" -ForegroundColor Cyan  
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Select scraping mode:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "[1] " -ForegroundColor Green -NoNewline
    Write-Host "Bulk Scraping      " -ForegroundColor White -NoNewline
    Write-Host "- One-time historical data collection" -ForegroundColor Gray
    
    Write-Host "[2] " -ForegroundColor Green -NoNewline  
    Write-Host "Live Scraping      " -ForegroundColor White -NoNewline
    Write-Host "- Continuous real-time monitoring" -ForegroundColor Gray
    
    Write-Host "[3] " -ForegroundColor Green -NoNewline
    Write-Host "Test Setup         " -ForegroundColor White -NoNewline
    Write-Host "- Validate environment and credentials" -ForegroundColor Gray
    
    Write-Host "[4] " -ForegroundColor Green -NoNewline
    Write-Host "Set Credentials    " -ForegroundColor White -NoNewline
    Write-Host "- Update phone number and password" -ForegroundColor Gray
    
    Write-Host "[5] " -ForegroundColor Green -NoNewline
    Write-Host "View Help          " -ForegroundColor White -NoNewline
    Write-Host "- Show detailed usage information" -ForegroundColor Gray
    
    Write-Host "[6] " -ForegroundColor Red -NoNewline
    Write-Host "Exit" -ForegroundColor White
    Write-Host ""
}

function Start-BulkScraping {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "Starting Bulk Scraping Mode" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "This will perform one-time historical data collection." -ForegroundColor Yellow
    Write-Host "Press any key to start or Ctrl+C to cancel..." -ForegroundColor Yellow
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    Write-Host ""
    
    & ".\run_scraper.ps1" -Mode bulk
    
    Write-Host ""
    Write-Host "Bulk scraping completed." -ForegroundColor Green
    Read-Host "Press Enter to return to menu"
}

function Start-LiveScraping {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Blue
    Write-Host "Starting Live Scraping Mode" -ForegroundColor Blue
    Write-Host "========================================" -ForegroundColor Blue
    Write-Host ""
    Write-Host "This will start continuous real-time monitoring." -ForegroundColor Yellow
    Write-Host "Press Ctrl+C during execution to stop gracefully." -ForegroundColor Yellow
    Write-Host "Press any key to start or Ctrl+C to cancel..." -ForegroundColor Yellow
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    Write-Host ""
    
    & ".\run_scraper.ps1" -Mode live
    
    Write-Host ""
    Write-Host "Live scraping stopped." -ForegroundColor Blue
    Read-Host "Press Enter to return to menu"
}

function Test-Setup {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Magenta
    Write-Host "Testing Setup" -ForegroundColor Magenta
    Write-Host "========================================" -ForegroundColor Magenta
    Write-Host ""
    
    & ".\test_setup.bat"
    
    Write-Host ""
    Read-Host "Press Enter to return to menu"
}

function Set-Credentials {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor DarkYellow
    Write-Host "Set Credentials" -ForegroundColor DarkYellow
    Write-Host "========================================" -ForegroundColor DarkYellow
    Write-Host ""
    
    & ".\set_credentials.ps1"
    
    Write-Host ""
    Read-Host "Press Enter to return to menu"
}

function Show-Help {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Game Agent Data Scraper - Help" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    
    Write-Host "BULK SCRAPING:" -ForegroundColor Green
    Write-Host "  - Collects historical data from the Win Go platform" -ForegroundColor White
    Write-Host "  - Runs once and exits when complete" -ForegroundColor White
    Write-Host "  - Progress is shown in real-time" -ForegroundColor White
    Write-Host "  - Data saved to: data/databaru_from_api.csv" -ForegroundColor Gray
    Write-Host ""
    
    Write-Host "LIVE SCRAPING:" -ForegroundColor Blue
    Write-Host "  - Continuously monitors for new game results" -ForegroundColor White
    Write-Host "  - Runs until manually stopped with Ctrl+C" -ForegroundColor White
    Write-Host "  - Automatically reconnects on errors" -ForegroundColor White
    Write-Host "  - Real-time data collection and processing" -ForegroundColor White
    Write-Host ""
    
    Write-Host "CREDENTIALS:" -ForegroundColor Yellow
    Write-Host "  - Phone: 82284608240 (currently configured)" -ForegroundColor White
    Write-Host "  - Password: [Hidden] (currently configured)" -ForegroundColor White
    Write-Host "  - Use option 4 to update credentials" -ForegroundColor Gray
    Write-Host ""
    
    Write-Host "FILES CREATED:" -ForegroundColor Magenta
    Write-Host "  - Virtual environment: venv_aipredict/" -ForegroundColor White
    Write-Host "  - Output data: data/databaru_from_api.csv" -ForegroundColor White
    Write-Host "  - Logs: logs/performance.log" -ForegroundColor White
    Write-Host ""
    
    Write-Host "TROUBLESHOOTING:" -ForegroundColor Red
    Write-Host "  - If browser issues occur, check ChromeDriver compatibility" -ForegroundColor White
    Write-Host "  - For permission errors, run as administrator" -ForegroundColor White
    Write-Host "  - Environment variables are set persistently" -ForegroundColor White
    Write-Host ""
    
    Read-Host "Press Enter to return to menu"
}

# Main program loop
do {
    Show-Menu
    
    $choice = Read-Host "Enter your choice (1-6)"
    
    switch ($choice) {
        "1" { Start-BulkScraping }
        "2" { Start-LiveScraping }
        "3" { Test-Setup }
        "4" { Set-Credentials }
        "5" { Show-Help }
        "6" { 
            Write-Host ""
            Write-Host "Thank you for using Game Agent Data Scraper!" -ForegroundColor Green
            Write-Host ""
            exit 0 
        }
        "exit" { 
            Write-Host ""
            Write-Host "Thank you for using Game Agent Data Scraper!" -ForegroundColor Green
            Write-Host ""
            exit 0 
        }
        "quit" { 
            Write-Host ""
            Write-Host "Thank you for using Game Agent Data Scraper!" -ForegroundColor Green
            Write-Host ""
            exit 0 
        }
        default { 
            Write-Host ""
            Write-Host "Invalid choice. Please enter 1-6." -ForegroundColor Red
            Start-Sleep -Seconds 2
        }
    }
} while ($true)
