#!/usr/bin/env python3
"""
Shell-based scraper that replaces the GUI functionality.
Run directly from command line with credentials as arguments or environment variables.
"""
import os
import sys
import yaml
import logging
import argparse
import getpass
import threading
import time
import signal

# --- Path Setup ---
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.rl_agent.realtime_agent import RealtimeAgent
from src.rl_agent.gemini_predictor import GeminiPredictor

class ShellScraper:
    """Shell-based scraper that works without GUI."""
    
    def __init__(self, config, gemini_model=None):
        self.config = config
        self.stop_event = threading.Event()
        self.agent = None
        self.gemini_predictor = None
        if gemini_model:
            try:
                self.gemini_predictor = GeminiPredictor(model_name=gemini_model)
                logging.info(f"GeminiPredictor initialized with model: {gemini_model}")
            except Exception as e:
                logging.error(f"Failed to initialize GeminiPredictor: {e}")
                self.gemini_predictor = None

    def setup_logging(self):
        """Setup console logging for shell mode."""
        log_config = self.config.get('logging', {})
        
        # Create logs directory if it doesn't exist
        log_dir = os.path.join(project_root, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        # Setup logging with both console and file output
        logging.basicConfig(
            level=log_config.get('level', 'INFO'),
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            handlers=[
                logging.StreamHandler(sys.stdout),  # Console output
                logging.FileHandler(os.path.join(log_dir, 'scraper_shell.log'))  # File output
            ]
        )
        
        # Also log to performance.log for compatibility
        perf_handler = logging.FileHandler(os.path.join(log_dir, 'performance.log'))
        perf_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(perf_handler)
        
        logging.info("=== Shell Scraper Started ===")
        logging.info(f"Working directory: {project_root}")
        logging.info(f"Log directory: {log_dir}")
        
    def get_credentials(self, phone=None, password=None):
        """Get credentials from arguments, environment, or prompt user."""
        if not phone:
            phone = os.getenv('PHONE_NUMBER')
        if not password:
            password = os.getenv('PASSWORD')
            
        if not phone:
            phone = input("Enter phone number: ").strip()
        if not password:
            password = getpass.getpass("Enter password: ").strip()
            
        if not phone or not password:
            logging.error("Phone number and password are required!")
            return None, None
            
        return phone, password
    
    def signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully."""
        logging.info("Received interrupt signal. Stopping scraper...")
        self.stop_event.set()
        if self.agent:
            self.agent.stop()
        sys.exit(0)
    
    def run_bulk_scrape(self, phone=None, password=None):
        """Run bulk scraping operation."""
        logging.info("=== Starting Bulk Scraping ===")
        
        phone, password = self.get_credentials(phone, password)
        if not phone or not password:
            logging.error("Phone number and password are required!")
            return False
            
        logging.info(f"Using phone: {phone}")
        logging.info("Credentials validated successfully")
            
        # Mock GUI queue for compatibility
        class MockQueue:
            def put(self, item):
                logging.info(f"Queue update: {item}")
                
        mock_queue = MockQueue()
        
        try:
            logging.info("Initializing RealtimeAgent...")
            self.agent = RealtimeAgent(self.config, mock_queue, phone=phone, password=password)
            
            logging.info("Starting standalone scrape operation...")
            self.agent.run_standalone_scrape()
            
            logging.info("=== Bulk Scraping Completed Successfully ===")
            return True
        except KeyboardInterrupt:
            logging.info("Bulk scraping interrupted by user")
            return True
        except Exception as e:
            logging.error(f"Bulk scraping failed: {e}", exc_info=True)
            return False
    
    def run_live_scrape(self, phone=None, password=None):
        """Run live scraping operation."""
        logging.info("=== Starting Live Scraping ===")
        logging.info("Press Ctrl+C to stop live scraping")
        
        phone, password = self.get_credentials(phone, password)
        if not phone or not password:
            logging.error("Phone number and password are required!")
            return False
            
        logging.info(f"Using phone: {phone}")
        logging.info("Credentials validated successfully")
        
        # Setup signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        
        # Mock GUI queue for compatibility
        class MockQueue:
            def __init__(self, predictor):
                self.predictor = predictor

            def put(self, item):
                logging.info(f"Queue update: {item}")
                if isinstance(item, dict) and item.get('type') == 'new_data' and self.predictor:
                    data = item.get('data')
                    logging.info(f"New data received: {data}. Requesting prediction from Gemini...")
                    report = self.predictor.generate_holistic_report(str(data))
                    print("\n--- GEMINI HOLISTIC REPORT ---")
                    print(report)
                    print("----------------------------\n")

        mock_queue = MockQueue(self.gemini_predictor)
        
        try:
            logging.info("Initializing RealtimeAgent...")
            self.agent = RealtimeAgent(self.config, mock_queue, phone=phone, password=password)
            
            logging.info("Starting live scrape operation...")
            self.agent.run_live_scrape()
            
            logging.info("=== Live Scraping Completed ===")
            return True
        except KeyboardInterrupt:
            logging.info("Live scraping stopped by user")
            return True
        except Exception as e:
            logging.error(f"Live scraping failed: {e}", exc_info=True)
            return False
    
    def fetch_external_data(self, url, method='GET'):
        """Fetch data from external URL."""
        logging.info(f"=== Starting Data Fetch from {url} ===")
        logging.info(f"Method: {method}")
        
        try:
            import requests
            import json
            import os
            
            # Make request
            if method.upper() == 'POST':
                response = requests.post(url)
            else:
                response = requests.get(url)
            
            response.raise_for_status()
            
            # Create data directory if not exists
            data_dir = os.path.join(project_root, 'data')
            os.makedirs(data_dir, exist_ok=True)
            
            # Determine content type and save appropriately
            content_type = response.headers.get('content-type', '')
            
            if 'application/json' in content_type:
                data = response.json()
                output_file = os.path.join(data_dir, 'fetched_data.json')
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                logging.info(f"JSON data saved to: {output_file}")
                logging.info(f"Records: {len(data) if isinstance(data, list) else 1}")
                
                # If it's a list of records, also save as CSV for compatibility
                if isinstance(data, list) and len(data) > 0:
                    try:
                        import pandas as pd
                        df = pd.DataFrame(data)
                        csv_file = os.path.join(data_dir, 'fetched_data.csv')
                        df.to_csv(csv_file, index=False)
                        logging.info(f"CSV format also saved to: {csv_file}")
                    except Exception as e:
                        logging.warning(f"Could not convert to CSV: {e}")
            
            else:
                # Save as text file
                output_file = os.path.join(data_dir, 'fetched_data.txt')
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                logging.info(f"Text data saved to: {output_file}")
                logging.info(f"Size: {len(response.text)} characters")
            
            logging.info("=== Data Fetch Completed Successfully ===")
            return True
            
        except Exception as e:
            logging.error(f"Data fetch failed: {e}", exc_info=True)
            return False

def load_config():
    """Load configuration file."""
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.yaml')
    try:
        with open(config_path, 'r', encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return config
    except FileNotFoundError:
        logging.critical(f"Error: Configuration file not found at {config_path}")
        sys.exit(1)
    except yaml.YAMLError as e:
        logging.critical(f"Error parsing YAML file: {e}")
        sys.exit(1)

def main():
    """Main function for shell scraper."""
    print("=== Game Agent Data Scraper - Shell Mode ===")
    print("Initializing...")
    
    parser = argparse.ArgumentParser(description='Game Agent Data Scraper - Shell Mode')
    parser.add_argument('--mode', choices=['bulk', 'live', 'fetch'], required=True,
                       help='Scraping mode: bulk (one-time), live (continuous), or fetch (external data)')
    parser.add_argument('--phone', help='Phone number for login')
    parser.add_argument('--password', help='Password for login')
    parser.add_argument('--model', choices=['gemini-2.5-flash', 'gemini-2.5-pro'], default=None,
                       help='Enable Gemini AI prediction with the specified model.')
    parser.add_argument('--url', help='URL to fetch data from (for fetch mode)')
    parser.add_argument('--method', choices=['GET', 'POST'], default='GET',
                       help='HTTP method for fetch mode')
    
    args = parser.parse_args()
    
    # Load configuration
    print("Loading configuration...")
    config = load_config()
    
    # Initialize scraper
    print("Initializing scraper...")
    scraper = ShellScraper(config, gemini_model=args.model)
    scraper.setup_logging()
    
    logging.info(f"Starting Game Agent Data Scraper in {args.mode} mode")
    logging.info(f"Arguments: mode={args.mode}, phone={'***' if args.phone else 'None'}, model={args.model}")
    
    # Run scraping based on mode
    try:
        if args.mode == 'bulk':
            success = scraper.run_bulk_scrape(args.phone, args.password)
        elif args.mode == 'live':
            success = scraper.run_live_scrape(args.phone, args.password)
        elif args.mode == 'fetch':
            if not args.url:
                logging.error("URL is required for fetch mode. Use --url parameter.")
                print("=== ERROR: URL required for fetch mode ===")
                sys.exit(1)
            success = scraper.fetch_external_data(args.url, args.method)
        else:
            logging.error(f"Unknown mode: {args.mode}")
            success = False
        
        if success:
            logging.info("Scraping completed successfully")
            print("=== SUCCESS: Scraping completed successfully ===")
            sys.exit(0)
        else:
            logging.error("Scraping failed")
            print("=== ERROR: Scraping failed - check logs for details ===")
            sys.exit(1)
            
    except Exception as e:
        logging.error(f"Unexpected error in main: {e}", exc_info=True)
        print(f"=== FATAL ERROR: {e} ===")
        sys.exit(1)

if __name__ == "__main__":
    main()
