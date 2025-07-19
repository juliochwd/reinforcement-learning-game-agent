#!/usr/bin/env python3
"""
Game Agent Data Scraper - Interactive Python Menu
Cross-platform launcher with menu selection
"""
import os
import sys
import subprocess
import platform

def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if platform.system() == 'Windows' else 'clear')

def show_menu():
    """Display the main menu."""
    clear_screen()
    print()
    print("=" * 40)
    print("    Game Agent Data Scraper")
    print("=" * 40)
    print()
    print("Select scraping mode:")
    print()
    print("[1] Bulk Scraping      - One-time historical data collection")
    print("[2] Live Scraping      - Continuous real-time monitoring")
    print("[3] Test Setup         - Validate environment and credentials")
    print("[4] Set Credentials    - Update phone number and password")
    print("[5] View Help          - Show detailed usage information")
    print("[6] Exit")
    print()

def run_command(command):
    """Run a system command and return the result."""
    try:
        if platform.system() == 'Windows':
            result = subprocess.run(command, shell=True, check=True)
        else:
            result = subprocess.run(command.split(), check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"Command failed with error: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

def bulk_scraping():
    """Execute bulk scraping mode."""
    print()
    print("=" * 40)
    print("Starting Bulk Scraping Mode")
    print("=" * 40)
    print()
    print("This will perform one-time historical data collection.")
    input("Press Enter to start or Ctrl+C to cancel...")
    print()
    
    if platform.system() == 'Windows':
        success = run_command("run_bulk_scrape.bat")
    else:
        success = run_command("python scraper_shell.py --mode bulk")
    
    print()
    if success:
        print("✅ Bulk scraping completed successfully!")
    else:
        print("❌ Bulk scraping failed. Check logs for details.")
    
    input("Press Enter to return to menu...")

def live_scraping():
    """Execute live scraping mode."""
    print()
    print("=" * 40)
    print("Starting Live Scraping Mode")
    print("=" * 40)
    print()
    print("This will start continuous real-time monitoring.")
    print("Press Ctrl+C during execution to stop gracefully.")
    input("Press Enter to start or Ctrl+C to cancel...")
    print()
    
    if platform.system() == 'Windows':
        success = run_command("run_live_scrape.bat")
    else:
        success = run_command("python scraper_shell.py --mode live")
    
    print()
    if success:
        print("✅ Live scraping completed successfully!")
    else:
        print("❌ Live scraping stopped or failed. Check logs for details.")
    
    input("Press Enter to return to menu...")

def test_setup():
    """Test the setup and configuration."""
    print()
    print("=" * 40)
    print("Testing Setup")
    print("=" * 40)
    print()
    
    if platform.system() == 'Windows':
        run_command("test_setup.bat")
    else:
        # Basic cross-platform setup test
        print("Testing Python environment...")
        try:
            import yaml, pandas, selenium
            print("✅ Required packages are installed")
        except ImportError as e:
            print(f"❌ Missing packages: {e}")
        
        if os.path.exists("config.yaml"):
            print("✅ Configuration file exists")
        else:
            print("❌ Configuration file missing")
        
        if os.path.exists("venv_aipredict"):
            print("✅ Virtual environment exists")
        else:
            print("❌ Virtual environment not found")
    
    print()
    input("Press Enter to return to menu...")

def set_credentials():
    """Set or update credentials."""
    print()
    print("=" * 40)
    print("Set Credentials")
    print("=" * 40)
    print()
    
    if platform.system() == 'Windows':
        run_command("set_credentials.bat")
    else:
        # Cross-platform credential setting
        phone = input("Enter phone number (current: 82284608240): ").strip()
        if not phone:
            phone = "82284608240"
        
        password = input("Enter password: ").strip()
        if not password:
            print("Password cannot be empty!")
            input("Press Enter to return to menu...")
            return
        
        # Set environment variables (session only for non-Windows)
        os.environ['PHONE_NUMBER'] = phone
        os.environ['PASSWORD'] = password
        print(f"✅ Credentials set for current session:")
        print(f"   Phone: {phone}")
        print(f"   Password: [HIDDEN]")
    
    print()
    input("Press Enter to return to menu...")

def show_help():
    """Display help information."""
    print()
    print("=" * 40)
    print("Game Agent Data Scraper - Help")
    print("=" * 40)
    print()
    
    print("BULK SCRAPING:")
    print("  - Collects historical data from the Win Go platform")
    print("  - Runs once and exits when complete")
    print("  - Progress is shown in real-time")
    print("  - Data saved to: data/databaru_from_api.csv")
    print()
    
    print("LIVE SCRAPING:")
    print("  - Continuously monitors for new game results")
    print("  - Runs until manually stopped with Ctrl+C")
    print("  - Automatically reconnects on errors")
    print("  - Real-time data collection and processing")
    print()
    
    print("CREDENTIALS:")
    print("  - Phone: 82284608240 (currently configured)")
    print("  - Password: [Hidden] (currently configured)")
    print("  - Use option 4 to update credentials")
    print()
    
    print("FILES CREATED:")
    print("  - Virtual environment: venv_aipredict/")
    print("  - Output data: data/databaru_from_api.csv")
    print("  - Logs: logs/performance.log")
    print()
    
    print("TROUBLESHOOTING:")
    print("  - If browser issues occur, check ChromeDriver compatibility")
    print("  - For permission errors, run as administrator")
    print("  - Environment variables are set persistently")
    print()
    
    input("Press Enter to return to menu...")

def main():
    """Main program loop."""
    while True:
        show_menu()
        
        try:
            choice = input("Enter your choice (1-6): ").strip()
            
            if choice == "1":
                bulk_scraping()
            elif choice == "2":
                live_scraping()
            elif choice == "3":
                test_setup()
            elif choice == "4":
                set_credentials()
            elif choice == "5":
                show_help()
            elif choice == "6" or choice.lower() in ["exit", "quit"]:
                print()
                print("Thank you for using Game Agent Data Scraper!")
                print()
                sys.exit(0)
            else:
                print()
                print("❌ Invalid choice. Please enter 1-6.")
                input("Press Enter to continue...")
                
        except KeyboardInterrupt:
            print()
            print("\nThank you for using Game Agent Data Scraper!")
            print()
            sys.exit(0)
        except Exception as e:
            print(f"An error occurred: {e}")
            input("Press Enter to continue...")

if __name__ == "__main__":
    main()
