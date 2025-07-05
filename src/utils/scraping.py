# ==============================================================================
#                           MODUL UTILITAS SCRAPING
# ==============================================================================
#  Berisi fungsi-fungsi bantuan untuk tugas-tugas scraping umum seperti
#  inisialisasi driver, login, penanganan pop-up, dan pemrosesan API.
# ==============================================================================

# Standard library imports
import json
import logging
import time
import zstandard

# Third-party imports
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from seleniumwire import webdriver
from selenium.webdriver.chrome.service import Service

def setup_driver(is_realtime=False):
    """
    Menginisialisasi dan mengembalikan instance WebDriver Selenium-Wire Chrome.

    Args:
        is_realtime (bool): Jika True, konfigurasikan untuk agen real-time (misalnya, start-maximized).
                            Jika False, konfigurasikan untuk scraping latar belakang.

    Returns:
        selenium.webdriver.Chrome: Instance WebDriver yang telah dikonfigurasi.
    """
    logging.info(f"Initializing WebDriver (Real-time: {is_realtime})...")
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])

    if is_realtime:
        options.add_argument("--start-maximized")

    seleniumwire_options = {'ignore_http_methods': ['OPTIONS']}
    
    service = Service()
    driver = webdriver.Chrome(
        service=service,
        options=options,
        seleniumwire_options=seleniumwire_options
    )
    logging.info("WebDriver initialized successfully.")
    return driver

def handle_popups(driver, xpaths, timers, max_popups=10):
    """
    Secara berulang mencari dan menutup semua pop-up "Confirm" setelah login.

    Args:
        driver: Instance WebDriver Selenium.
        xpaths (dict): Konfigurasi XPath dari file config.
        timers (dict): Konfigurasi timer dari file config.
        max_popups (int): Jumlah maksimum pop-up yang akan ditutup.
    """
    logging.info("Checking for post-login pop-ups...")
    popups_closed = 0
    
    try:
        popup_config = xpaths.get('game_interface', {}).get('popup_confirm_button', {})
        by_str = popup_config.get('by', 'XPATH').upper()
        by = getattr(By, by_str)
        value = popup_config.get('value')
    except (KeyError, AttributeError):
        logging.error("Popup configuration not found or invalid in config.")
        return

    while popups_closed < max_popups:
        try:
            confirm_button = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((by, value))
            )
            logging.info(f"Found a 'Confirm' pop-up. Closing it (popup #{popups_closed + 1})...")
            driver.execute_script("arguments[0].click();", confirm_button)
            popups_closed += 1
            time.sleep(timers.get('post_action_sleep', 1))
        except TimeoutException:
            logging.info("No more 'Confirm' pop-ups found.")
            break
        except Exception as e:
            logging.error(f"An error occurred while handling pop-ups: {e}")
            break

def process_api_response(request):
    """
    Memproses respons permintaan API, menangani kemungkinan kompresi zstd,
    dan mengembalikan daftar rekaman.

    Args:
        request: Objek permintaan yang ditangkap oleh Selenium-Wire.

    Returns:
        list: Daftar rekaman dari respons API, atau daftar kosong jika terjadi kesalahan.
    """
    if not (request and request.response and request.response.body):
        logging.warning("Request, response, or response body is missing.")
        return []

    body = request.response.body
    
    if request.response.headers.get('Content-Encoding') == 'zstd':
        try:
            dctx = zstandard.ZstdDecompressor()
            with dctx.stream_reader(body) as reader:
                body = reader.read()
        except zstandard.ZstdError as e:
            logging.error(f"Failed to decompress zstd body: {e}")
            return []

    try:
        response_str = body.decode('utf-8')
    except UnicodeDecodeError as e:
        logging.error(f"Failed to decode response body to UTF-8: {e}")
        return []

    if not response_str.strip():
        logging.warning("Response body is empty after decoding.")
        return []
        
    try:
        data = json.loads(response_str)
        records = data.get('data', {}).get('list', [])
        return records if isinstance(records, list) else []
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse JSON from response: {e}. Body: {response_str[:200]}")
        return []
