import logging
import time
import os
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from src.utils.scraping import setup_driver, handle_popups

class BrowserManager:
    """
    Mengelola siklus hidup browser Selenium, termasuk inisialisasi,
    login, navigasi, dan penutupan.
    """
    def __init__(self, config):
        self.config = config
        self.web_agent_config = self.config.get('web_agent', {})
        self.timeouts = self.web_agent_config.get('timeouts', {})
        self.timers = self.web_agent_config.get('timers', {})
        self.xpaths = self.web_agent_config.get('xpaths', {})
        self.login_url = self.web_agent_config.get('login_url')
        self.driver = None

    def _get_selector(self, category, name):
        """Helper untuk mendapatkan By dan Value selector dari config."""
        try:
            selector_config = self.xpaths[category][name]
            by_str = selector_config.get('by', 'XPATH').upper()
            by = getattr(By, by_str)
            value = selector_config.get('value')
            return by, value
        except KeyError:
            logging.error(f"Selector untuk '{category}.{name}' tidak ditemukan di config.yaml.")
            return None, None

    def initialize_driver(self):
        """Menginisialisasi instance webdriver Selenium."""
        logging.info("Initializing Selenium WebDriver...")
        self.driver = setup_driver(is_realtime=True)
        self.driver.set_page_load_timeout(self.timeouts.get('page_load', 60))
        return self.driver

    def login(self, phone=None, password=None):
        """Menangani proses login ke situs web."""
        try:
            # Prioritaskan kredensial yang diberikan, fallback ke variabel lingkungan
            login_phone = phone if phone else os.getenv('PHONE_NUMBER')
            login_password = password if password else os.getenv('PASSWORD')

            if not login_phone or not login_password:
                logging.critical("Kredensial (PHONE_NUMBER/PASSWORD) tidak tersedia. Proses login dibatalkan.")
                return False

            logging.info(f"Navigasi ke halaman login: {self.login_url}")
            self.driver.get(self.login_url)
            
            user_by, user_val = self._get_selector('login', 'user_input')
            pass_by, pass_val = self._get_selector('login', 'password_input')
            submit_by, submit_val = self._get_selector('login', 'submit_button')

            WebDriverWait(self.driver, self.timeouts.get('element_wait', 30)).until(EC.presence_of_element_located((user_by, user_val)))
            self.driver.find_element(user_by, user_val).send_keys(login_phone)
            self.driver.find_element(pass_by, pass_val).send_keys(login_password)
            self.driver.find_element(submit_by, submit_val).click()
            
            logging.info("Login terkirim. Menunggu navigasi...")
            time.sleep(self.timers.get('post_login_sleep', 3))
            handle_popups(self.driver, self.xpaths, self.timers)
            time.sleep(self.timers.get('post_action_sleep', 1)) # Extra delay after login
            return True
        except (TimeoutException, NoSuchElementException) as e:
            logging.error(f"Elemen login tidak ditemukan atau waktu tunggu habis: {e}", exc_info=True)
            return False
        except WebDriverException as e:
            logging.error(f"Terjadi error WebDriver saat login: {e}", exc_info=True)
            return False

    def navigate_to_game(self):
        """Menavigasi dari halaman utama ke game Win Go 1Min."""
        try:
            logging.info("Menavigasi ke game 'Win Go 1Min'...")
            handle_popups(self.driver, self.xpaths, self.timers)
            
            menu_by, menu_val = self._get_selector('navigation', 'win_go_menu')
            btn_by, btn_val = self._get_selector('navigation', 'win_go_1min_button')

            win_go_menu = WebDriverWait(self.driver, self.timeouts.get('element_wait', 20)).until(EC.element_to_be_clickable((menu_by, menu_val)))
            self.driver.execute_script("arguments[0].click();", win_go_menu)
            time.sleep(self.timers.get('post_action_sleep', 1))
            
            # Extra delay before clicking the 1min button
            time.sleep(self.timers.get('post_action_sleep', 1))

            win_go_1min_button = WebDriverWait(self.driver, self.timeouts.get('element_wait', 20)).until(EC.element_to_be_clickable((btn_by, btn_val)))
            self.driver.execute_script("arguments[0].click();", win_go_1min_button)
            
            logging.info("Berhasil menavigasi ke 'Win Go 1Min'.")
            return True
        except (TimeoutException, NoSuchElementException) as e:
            logging.error(f"Elemen navigasi game tidak ditemukan atau waktu tunggu habis: {e}", exc_info=True)
            return False
        except WebDriverException as e:
            logging.error(f"Terjadi error WebDriver saat navigasi: {e}", exc_info=True)
            return False

    def logout(self):
        """Mencoba untuk logout dengan menavigasi ke halaman 'My' dan mengklik logout."""
        try:
            logging.info("Mencoba untuk logout untuk memulihkan sesi...")
            
            my_acc_by, my_acc_val = self._get_selector('navigation', 'my_account_button')
            logout_by, logout_val = self._get_selector('navigation', 'logout_button')

            my_account_button = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((my_acc_by, my_acc_val)))
            my_account_button.click()
            time.sleep(self.timers.get('post_action_sleep', 1))

            logout_button = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((logout_by, logout_val)))
            logout_button.click()
            time.sleep(self.timers.get('api_retry_delay', 2))
            
            logging.info("Logout berhasil.")
            return True
        except (TimeoutException, NoSuchElementException):
            logging.warning("Tidak dapat menemukan tombol logout, mungkin sudah logout.")
            return True # Anggap berhasil jika tidak bisa logout
        except WebDriverException as e:
            logging.error(f"Tidak dapat melakukan logout bersih: {e}", exc_info=True)
            return False

    def get_driver(self):
        """Mengembalikan instance driver yang aktif."""
        return self.driver

    def close(self):
        """Menutup webdriver."""
        if self.driver:
            logging.info("Menutup WebDriver.")
            self.driver.quit()
            self.driver = None
