# Set Environment Variables for Game Agent Data Scraper (PowerShell)
# This script sets up your credentials as environment variables securely

Write-Host "Setting up environment variables for Game Agent Data Scraper..." -ForegroundColor Green
Write-Host ""

try {
    # Set environment variables for current session
    $env:PHONE_NUMBER = "82284608240"
    $env:PASSWORD = "Dh4910va"
    
    # Set persistent environment variables (user-level)
    [Environment]::SetEnvironmentVariable("PHONE_NUMBER", "82284608240", "User")
    [Environment]::SetEnvironmentVariable("PASSWORD", "Dh4910va", "User")
    
    Write-Host "Environment variables set successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "PHONE_NUMBER: 82284608240" -ForegroundColor Yellow
    Write-Host "PASSWORD: [HIDDEN]" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "These credentials will now be used automatically when running:" -ForegroundColor Cyan
    Write-Host "- run_bulk_scrape.bat" -ForegroundColor White
    Write-Host "- run_live_scrape.bat" -ForegroundColor White
    Write-Host "- .\run_scraper.ps1 -Mode bulk" -ForegroundColor White
    Write-Host "- .\run_scraper.ps1 -Mode live" -ForegroundColor White
    Write-Host ""
    Write-Host "Note: You may need to restart PowerShell for persistent variables to take effect in new sessions." -ForegroundColor Yellow
    
} catch {
    Write-Host "ERROR: Failed to set environment variables" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
} finally {
    Write-Host ""
    Read-Host "Press Enter to continue"
}
