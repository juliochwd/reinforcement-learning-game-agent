# ==============================================================================
#                      API-BASED WEB SCRAPER (FINAL VERSION)
#          Dibuat untuk mengambil data riwayat permainan secara efisien
# ==============================================================================

# Standard library imports
import json
import logging
import time
import os
import yaml

# Third-party imports
import numpy as np
import pandas as pd
import requests
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import tempfile

# Local application/library specific imports
from src.utils.scraping import setup_driver, handle_popups, process_api_response
from src.utils import gcs_utils

# ==============================================================================
#                           KONFIGURASI
# ==============================================================================

def load_config():
    """Memuat konfigurasi dari file config.yaml di root direktori."""
    config_path = 'config.yaml'
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

# Memuat konfigurasi saat startup
config = load_config()
PHONE_NUMBER = os.getenv('PHONE_NUMBER')
PASSWORD = os.getenv('PASSWORD')

# Pengaturan dari file config
WEB_AGENT_CONFIG = config.get('web_agent', {})
LOGIN_URL = WEB_AGENT_CONFIG.get('login_url', 'https://55v7nlu.com/#/login')
API_ENDPOINT = WEB_AGENT_CONFIG.get('api_endpoint', 'api.55fiveapi.com/api/webapi/GetNoaverageEmerdList')
OUTPUT_EXCEL_FILE = config.get('data_path', 'data/databaru_from_api.csv').replace('.csv', '.xlsx')
OUTPUT_CSV_FILE = config.get('data_path', 'data/databaru_from_api.csv')
MAX_PAGES_TO_SCRAPE = WEB_AGENT_CONFIG.get('scraping', {}).get('max_pages', 200)
TIMEOUTS = WEB_AGENT_CONFIG.get('timeouts', {})
TIMERS = WEB_AGENT_CONFIG.get('timers', {})
XPATHS = WEB_AGENT_CONFIG.get('xpaths', {})

# ==============================================================================
#                           SETUP LOGGING
# ==============================================================================

def setup_logging():
    """Mengkonfigurasi logging untuk menampilkan output di konsol."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    # Mencegah log dari library lain yang terlalu "berisik"
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("seleniumwire").setLevel(logging.WARNING)

# ==============================================================================
#                           FUNGSI-FUNGSI BANTUAN
# ==============================================================================

def get_total_pages_from_ui(driver, xpaths, timeouts, default_pages=1):
    """
    Membaca jumlah total halaman dari elemen UI, contohnya '1/1722'.
    """
    try:
        page_info_config = xpaths.get('history_interface', {}).get('page_info', {})
        page_info_element = WebDriverWait(driver, timeouts.get('element_wait', 10)).until(
            EC.presence_of_element_located((page_info_config.get('by', 'CLASS_NAME'), page_info_config.get('value')))
        )
        page_text = page_info_element.text
        total_pages_str = page_text.split('/')[1]
        total_pages = int(total_pages_str)
        logging.info(f"Successfully parsed total pages from UI: {total_pages}")
        return total_pages
    except Exception as e:
        logging.error(f"Could not parse total pages from UI. Error: {e}. Defaulting to {default_pages} page(s).")
        return default_pages

# ==============================================================================
#                           FUNGSI UTAMA SCRAPING
# ==============================================================================

def scrape_all_data_via_api():
    """
    Login dengan Selenium, menangkap detail API, lalu mengambil semua data riwayat
    dengan cepat menggunakan 'requests'.
    """
    if not PHONE_NUMBER or not PASSWORD:
        logging.critical("PHONE_NUMBER or PASSWORD environment variables not set. Aborting.")
        return

    driver = None
    try:
        # TAHAP 1: LOGIN DAN NAVIGASI DENGAN SELENIUM
        driver = setup_driver()
        driver.set_page_load_timeout(TIMEOUTS.get('page_load', 60))
        logging.info(f"Navigating to login page: {LOGIN_URL}")
        driver.get(LOGIN_URL)
        
        login_xpaths = XPATHS.get('login', {})
        user_input_cfg = login_xpaths.get('user_input', {})
        password_input_cfg = login_xpaths.get('password_input', {})
        submit_button_cfg = login_xpaths.get('submit_button', {})

        WebDriverWait(driver, TIMEOUTS.get('element_wait', 30)).until(EC.presence_of_element_located((user_input_cfg.get('by', 'NAME'), user_input_cfg.get('value'))))
        driver.find_element(user_input_cfg.get('by', 'NAME'), user_input_cfg.get('value')).send_keys(PHONE_NUMBER)
        driver.find_element(password_input_cfg.get('by', 'XPATH'), password_input_cfg.get('value')).send_keys(PASSWORD)
        driver.find_element(submit_button_cfg.get('by', 'XPATH'), submit_button_cfg.get('value')).click()
        logging.info("Login submitted. Waiting for page to load and handle pop-ups.")

        handle_popups(driver, XPATHS, TIMERS)

        zoom_level = WEB_AGENT_CONFIG.get('scraping', {}).get('zoom_level', '80%')
        logging.info(f"Zooming out page to {zoom_level} to ensure all elements are visible...")
        driver.execute_script(f"document.body.style.zoom='{zoom_level}'")
        
        # TAHAP 1.5: NAVIGASI KE PERMAINAN 'WIN GO 1MIN'
        logging.info("Navigating to the 'Win Go 1Min' game...")

        try:
            nav_xpaths = XPATHS.get('navigation', {})
            win_go_cfg = nav_xpaths.get('win_go_menu', {})
            win_go_1min_cfg = nav_xpaths.get('win_go_1min_button', {})

            logging.info("Waiting for 'Win Go' menu...")
            win_go_menu = WebDriverWait(driver, TIMEOUTS.get('element_wait', 30)).until(
                EC.element_to_be_clickable((win_go_cfg.get('by', 'XPATH'), win_go_cfg.get('value')))
            )
            driver.execute_script("arguments[0].click();", win_go_menu)
            logging.info("Main 'Win Go' menu clicked.")

            logging.info("Waiting for 'Win Go 1Min' sub-menu...")
            win_go_1min_button = WebDriverWait(driver, TIMEOUTS.get('element_wait', 30)).until(
                EC.element_to_be_clickable((win_go_1min_cfg.get('by', 'XPATH'), win_go_1min_cfg.get('value')))
            )
            driver.execute_script("arguments[0].click();", win_go_1min_button)
            logging.info("Successfully clicked on 'Win Go 1Min' sub-menu.")

        except TimeoutException as e:
            logging.critical(f"Failed to navigate to 'Win Go 1Min' game. Element not found or not clickable. Error: {e}")
            driver.save_screenshot("debug_screenshot_navigation_failed.png")
            logging.info("Debug screenshot saved as 'debug_screenshot_navigation_failed.png'")
            return

        # TAHAP 2: MENENTUKAN TOTAL HALAMAN & MENANGKAP DETAIL API
        total_pages = get_total_pages_from_ui(driver, XPATHS, TIMEOUTS)

        # TAHAP 3: MENGAMBIL DATA DARI HALAMAN 1 (YANG SUDAH TER-LOAD)
        all_records = []
        logging.info("Processing data for the initial page (Page 1)...")
        
        try:
            initial_request = next(req for req in reversed(driver.requests) if API_ENDPOINT in req.url)
            records_on_page = process_api_response(initial_request)
            if records_on_page:
                all_records.extend(records_on_page)
                logging.info(f"SUCCESS: Added {len(records_on_page)} records from the initial page.")
            else:
                logging.warning("No records processed from the initial page's API response. It might be empty.")
        except StopIteration:
            logging.critical("Could not find the initial API request for page 1. Aborting.")
            return

        # TAHAP 3.5: LOOP KLIK 'NEXT' UNTUK HALAMAN 2 DAN SETERUSNYA
        for page_num in range(2, min(total_pages, MAX_PAGES_TO_SCRAPE) + 1):
            logging.info(f"Navigating to page {page_num}/{min(total_pages, MAX_PAGES_TO_SCRAPE)}...")
            
            del driver.requests
            
            try:
                next_button_cfg = XPATHS.get('navigation', {}).get('history_next_page_button', {})
                next_button = WebDriverWait(driver, TIMEOUTS.get('element_wait', 10)).until(
                    EC.element_to_be_clickable((next_button_cfg.get('by', 'XPATH'), next_button_cfg.get('value')))
                )
                driver.execute_script("arguments[0].click();", next_button)
                logging.info("Clicked 'next' button.")
            except TimeoutException:
                logging.warning("Could not find or click the 'next' button. Stopping pagination.")
                break

            try:
                request = driver.wait_for_request(API_ENDPOINT, timeout=TIMEOUTS.get('api_wait', 30))
                logging.info(f"API request for page {page_num} captured.")
                records_on_page = process_api_response(request)
                
                if records_on_page:
                    all_records.extend(records_on_page)
                    logging.info(f"SUCCESS: Added {len(records_on_page)} records from page {page_num}.")
                else:
                    logging.warning(f"No records processed from API response for page {page_num}.")
            except TimeoutException:
                logging.error(f"Timed out waiting for API request on page {page_num}. Stopping.")
                break

        # TAHAP 4: MEMPROSES DAN MENYIMPAN DATA KE EXCEL (HANYA SEKALI)
        logging.info(f"Total records scraped via API: {len(all_records)}. Processing...")
        if not all_records:
            logging.warning("No records were scraped. Exiting.")
            return

        df = pd.DataFrame(all_records)
        df.rename(columns={'issueNumber': 'Period', 'number': 'Number', 'colour': 'Color', 'premium': 'Premium'}, inplace=True)
        
        df['Number'] = pd.to_numeric(df['Number'])
        df['Big/Small'] = np.where(df['Number'] >= 5, 'Big', 'Small')
        
        final_df = df[['Period', 'Number', 'Big/Small', 'Color', 'Premium']].copy()
        final_df = final_df.sort_values(by='Period', ascending=True).drop_duplicates(subset='Period', keep='last')

        with tempfile.TemporaryDirectory() as temp_dir:
            local_excel_path = os.path.join(temp_dir, os.path.basename(OUTPUT_EXCEL_FILE))
            local_csv_path = os.path.join(temp_dir, os.path.basename(OUTPUT_CSV_FILE))

            # Download existing data if using GCS
            if gcs_utils.is_gcs_path(OUTPUT_EXCEL_FILE):
                try:
                    gcs_utils.download_from_gcs(OUTPUT_EXCEL_FILE, local_excel_path)
                    existing_df = pd.read_excel(local_excel_path)
                    logging.info(f"Successfully loaded {len(existing_df)} existing records from GCS path '{OUTPUT_EXCEL_FILE}'.")
                    combined_df = pd.concat([existing_df, final_df], ignore_index=True)
                except Exception as e:
                    logging.warning(f"Could not download or read from GCS path '{OUTPUT_EXCEL_FILE}'. Creating new dataset. Error: {e}")
                    combined_df = final_df
            else:
                 try:
                    existing_df = pd.read_excel(OUTPUT_EXCEL_FILE)
                    logging.info(f"Successfully loaded {len(existing_df)} existing records from local path '{OUTPUT_EXCEL_FILE}'.")
                    combined_df = pd.concat([existing_df, final_df], ignore_index=True)
                 except FileNotFoundError:
                    logging.info(f"Local file '{OUTPUT_EXCEL_FILE}' not found. A new file will be created.")
                    combined_df = final_df

            combined_df['Period'] = combined_df['Period'].astype(str)
            combined_df.drop_duplicates(subset='Period', keep='last', inplace=True)
            combined_df = combined_df.sort_values(by='Period', ascending=True)

            # Save to local temporary files first
            with pd.ExcelWriter(local_excel_path, engine='xlsxwriter') as writer:
                combined_df.to_excel(writer, index=False, sheet_name='Sheet1')
                workbook  = writer.book
                worksheet = writer.sheets['Sheet1']
                text_format = workbook.add_format({'num_format': '@'})
                worksheet.set_column('A:A', 20, text_format)
            
            combined_df.to_csv(local_csv_path, index=False, sep=',')

            # Upload to GCS if applicable
            if gcs_utils.is_gcs_path(OUTPUT_EXCEL_FILE):
                gcs_utils.upload_to_gcs(local_excel_path, OUTPUT_EXCEL_FILE)
                logging.info(f"SUCCESS: All {len(combined_df)} unique records have been uploaded to '{OUTPUT_EXCEL_FILE}'")
            else:
                # If not GCS, move from temp to final destination
                os.replace(local_excel_path, OUTPUT_EXCEL_FILE)
                logging.info(f"SUCCESS: All {len(combined_df)} unique records have been saved to '{OUTPUT_EXCEL_FILE}'")

            if gcs_utils.is_gcs_path(OUTPUT_CSV_FILE):
                gcs_utils.upload_to_gcs(local_csv_path, OUTPUT_CSV_FILE)
                logging.info(f"SUCCESS: Data also uploaded to CSV at '{OUTPUT_CSV_FILE}'")
            else:
                os.replace(local_csv_path, OUTPUT_CSV_FILE)
                logging.info(f"SUCCESS: Data also saved to CSV at '{OUTPUT_CSV_FILE}'")

    except Exception as e:
        logging.critical(f"An unrecoverable error occurred during the scraping process: {e}", exc_info=True)
    finally:
        if driver:
            driver.quit()
            logging.info("WebDriver has been closed.")

# ==============================================================================
#                               BLOK EKSEKUSI UTAMA
# ==============================================================================

if __name__ == "__main__":
    setup_logging()
    scrape_all_data_via_api()
