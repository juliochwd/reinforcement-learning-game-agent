import logging
import time
import os
import queue
import pandas as pd
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

from src.rl_agent.browser_manager import BrowserManager
from src.rl_agent.data_scraper import DataScraper

class RealtimeAgent:
    """
    Orkestrator utama untuk operasi real-time. Mengelola loop game,
    interaksi UI, pengambilan keputusan, dan komunikasi dengan GUI.
    """
    def __init__(self, config, gui_queue, phone=None, password=None):
        self.config = config
        self.gui_queue = gui_queue
        self.phone = phone
        self.password = password
        self.running = False
        self.web_agent_config = self.config.get('web_agent', {})
        self.timeouts = self.web_agent_config.get('timeouts', {})
        self.timers = self.web_agent_config.get('timers', {})
        self.xpaths = self.web_agent_config.get('xpaths', {})
        self.browser_manager = BrowserManager(config)
        self.data_scraper = None

    def _get_selector(self, category, name):
        try:
            selector_config = self.xpaths[category][name]
            by_str = selector_config.get('by', 'XPATH').upper()
            by = getattr(By, by_str)
            value = selector_config.get('value')
            return by, value
        except KeyError:
            logging.error(f"Selector untuk '{category}.{name}' tidak ditemukan di config.yaml.")
            return None, None

    def _initialize_modules(self):
        logging.info("Menginisialisasi modul-modul agen...")
        driver = self.browser_manager.initialize_driver()
        if not driver:
            logging.error("Gagal menginisialisasi WebDriver. Agen berhenti.")
            return False
        
        self.data_scraper = DataScraper(driver, self.config)
                    
        if not self.browser_manager.login(phone=self.phone, password=self.password) or not self.browser_manager.navigate_to_game():
            logging.error("Gagal login atau navigasi ke game. Agen berhenti.")
            return False
            
        return True

    def run_standalone_scrape(self):
        logging.info("--- Memulai Tugas Scraping Data Mandiri ---")
        driver = None
        try:
            driver = self.browser_manager.initialize_driver()
            if not driver:
                logging.error("Gagal menginisialisasi WebDriver untuk scraping.")
                return

            self.data_scraper = DataScraper(driver, self.config)
            
            # Teruskan kredensial ke metode login
            if not self.browser_manager.login(phone=self.phone, password=self.password) or not self.browser_manager.navigate_to_game():
                logging.error("Gagal login atau navigasi untuk scraping.")
                return

            self.gui_queue.put({"type": "bulk_scrape_started"})
            self.data_scraper.execute_bulk_scrape()
            logging.info("Scraping data mandiri selesai.")

        except Exception as e:
            logging.critical(f"Error selama scraping mandiri: {e}", exc_info=True)
        finally:
            if driver:
                self.browser_manager.close()
            self.gui_queue.put({"type": "bulk_scrape_finished"})
            logging.info("--- Tugas Scraping Data Mandiri Selesai ---")

