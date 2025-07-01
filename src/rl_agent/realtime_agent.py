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
from src.rl_agent.decision_maker import DecisionMaker

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
        self.is_paused = False
        self.command_queue = queue.Queue()
        self.web_agent_config = self.config.get('web_agent', {})
        self.timeouts = self.web_agent_config.get('timeouts', {})
        self.timers = self.web_agent_config.get('timers', {})
        self.xpaths = self.web_agent_config.get('xpaths', {})
        self.browser_manager = BrowserManager(config)
        self.data_scraper = None
        self.decision_maker = DecisionMaker(config)
        self.historical_data = None
        self.current_balance = self.web_agent_config.get('initial_balance', 2000000)
        self.initial_balance = None
        self.total_profit = 0

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
        
        if not self.decision_maker.load_model():
            logging.error("Gagal memuat model DecisionMaker. Agen berhenti.")
            return False

        data_path = self.config['data_path']
        if os.path.exists(data_path):
            self.historical_data = pd.read_csv(data_path)
            logging.info(f"Data historis berhasil dimuat dari {data_path}.")
        else:
            logging.error(f"Data historis tidak ditemukan di {data_path}. Agen berhenti.")
            return False
            
        if not self.browser_manager.login() or not self.browser_manager.navigate_to_game():
            logging.error("Gagal login atau navigasi ke game. Agen berhenti.")
            return False
            
        return True

    def _is_data_sequential(self, predicting_period, window_size=5):
        try:
            if len(self.historical_data) < window_size:
                logging.warning(f"Data historis tidak cukup (memiliki {len(self.historical_data)}, butuh {window_size}).")
                return False
            predicting_period_num = int(predicting_period)
            historical_periods = pd.to_numeric(self.historical_data['Period'])
            last_known_period = historical_periods.iloc[-1]
            if last_known_period != predicting_period_num - 1:
                logging.warning(f"Data tidak relevan. Prediksi untuk {predicting_period_num}, tapi data terakhir adalah {last_known_period}.")
                return False
            last_n_periods = historical_periods.tail(window_size)
            is_sequential = (last_n_periods.diff().dropna() == 1).all()
            if not is_sequential:
                logging.warning(f"Data tidak sekuensial. Periode terakhir: {last_n_periods.tolist()}.")
            return is_sequential
        except (ValueError, TypeError) as e:
            logging.error(f"Tidak dapat memvalidasi urutan data: {e}")
            return False

    def _place_bet(self, action_str, bet_amount_units):
        try:
            logging.info(f"Mencoba menempatkan taruhan: '{action_str}' dengan {bet_amount_units} unit.")
            if 'Small' in action_str:
                bet_by, bet_val = self._get_selector('game_interface', 'bet_small_button')
            elif 'Big' in action_str:
                bet_by, bet_val = self._get_selector('game_interface', 'bet_big_button')
            else:
                return False

            driver = self.browser_manager.get_driver()
            bet_button = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((bet_by, bet_val)))
            driver.execute_script("arguments[0].click();", bet_button)
            
            input_by, input_val = self._get_selector('game_interface', 'bet_amount_input')
            amount_input = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((input_by, input_val)))
            
            amount_input.clear()
            amount_input.send_keys(str(bet_amount_units))
            time.sleep(self.timers.get('popup_check_sleep', 0.5))

            confirm_by, confirm_val = self._get_selector('game_interface', 'bet_confirm_button')
            confirm_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((confirm_by, confirm_val)))
            driver.execute_script("arguments[0].click();", confirm_button)
            
            logging.info("Taruhan berhasil ditempatkan dan dikonfirmasi.")
            time.sleep(self.timers.get('post_action_sleep', 1))
            return True
        except Exception as e:
            logging.error(f"Gagal menempatkan taruhan: {e}", exc_info=True)
            return False

    def _handle_new_round(self, predicting_period):
        logging.info(f"Membuat keputusan untuk ronde saat ini: {predicting_period}")
        
        if not self._is_data_sequential(predicting_period, window_size=self.config.get('window_size', 5)):
            action_idx, action_str = 0, "Hold (Data Tidak Valid/Stale)"
        else:
            action_idx, action_str = self.decision_maker.get_action(self.historical_data)

        new_balance = self.data_scraper.get_current_balance(refresh=False)
        if new_balance is not None:
            if self.initial_balance is None:
                self.initial_balance = new_balance
            self.current_balance = new_balance
            self.total_profit = self.current_balance - self.initial_balance

        bet_amount_display = 0
        if action_idx != 0:
            can_bet = True
            try:
                timer_str = self.data_scraper.get_current_timer()
                minutes, seconds = map(int, timer_str.split(':'))
                if minutes == 0 and seconds <= self.timeouts.get('bet_placement_buffer_seconds', 7):
                    logging.warning(f"Timer di {timer_str} di bawah ambang batas. Memaksa 'Hold'.")
                    action_str = f"Hold (Batas Waktu {timer_str})"
                    can_bet = False
            except Exception as e:
                logging.error(f"Tidak dapat parse timer. Melewatkan taruhan. Error: {e}")
                action_str = "Hold (Timer Error)"
                can_bet = False

            if can_bet:
                try:
                    percentage_str = action_str[action_str.find("(")+1:action_str.find("%")]
                    bet_percentage = float(percentage_str) / 100
                    bet_amount_currency = self.current_balance * bet_percentage
                    bet_unit_divisor = self.web_agent_config.get('bet_unit_divisor', 1000)
                    bet_amount_units = max(1, int(bet_amount_currency / bet_unit_divisor))
                    if self._place_bet(action_str, bet_amount_units):
                        bet_amount_display = bet_amount_units * bet_unit_divisor
                except Exception as e:
                    logging.error(f"Tidak dapat parse persentase taruhan dari '{action_str}'. Default ke 1 unit. Error: {e}")
                    if self._place_bet(action_str, 1):
                         bet_amount_display = self.web_agent_config.get('bet_unit_divisor', 1000)
        else:
            logging.info("Aksi adalah 'Hold', tidak ada taruhan yang akan ditempatkan.")

        self.gui_queue.put({
            "type": "agent_update", "action_str": action_str,
            "total_reward": self.total_profit, "balance": self.current_balance - bet_amount_display,
            "bet_amount": bet_amount_display, "period": predicting_period
        })

    def _update_after_round(self, last_bet_on_period):
        latest_result_df = None
        for i in range(5):
            time.sleep(self.timers.get('api_retry_delay', 2))
            latest_result_df = self.data_scraper.scrape_latest_result()
            if latest_result_df is not None and int(latest_result_df['Period'].iloc[0]) >= last_bet_on_period:
                logging.info(f"Berhasil scrape hasil untuk ronde selesai {latest_result_df['Period'].iloc[0]}.")
                self.historical_data = pd.concat([self.historical_data, latest_result_df], ignore_index=True).drop_duplicates(subset=['Period'], keep='last')
                
                new_balance = self.data_scraper.get_current_balance(refresh=True)
                if new_balance is not None:
                    self.current_balance = new_balance
                    if self.initial_balance is not None:
                        self.total_profit = self.current_balance - self.initial_balance

                self.gui_queue.put({
                    "type": "agent_update", "action_str": "Ronde Selesai",
                    "total_reward": self.total_profit, "balance": self.current_balance,
                    "bet_amount": 0, "period": latest_result_df['Period'].iloc[0]
                })
                return
            logging.debug(f"Percobaan {i+1} untuk mengambil hasil untuk {last_bet_on_period}, belum tersedia.")
            time.sleep(1)

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

    def _check_commands(self):
        try:
            command = self.command_queue.get_nowait()
            if command == "scrape_bulk":
                logging.info("Perintah 'scrape_bulk' diterima oleh agen yang sedang berjalan.")
                self.is_paused = True
                self.gui_queue.put({"type": "bulk_scrape_started"})
                new_data = self.data_scraper.execute_bulk_scrape()
                if new_data is not None:
                    self.historical_data = new_data
                    logging.info("Data historis agen diperbarui setelah scraping.")
                self.is_paused = False
                self.gui_queue.put({"type": "bulk_scrape_finished"})
        except queue.Empty:
            pass

    def _recover_session(self):
        logging.warning("Halaman tampaknya macet. Memicu protokol pemulihan.")
        logging.info("Pemulihan L1: Me-refresh halaman dan menavigasi ke game.")
        self.browser_manager.get_driver().refresh()
        time.sleep(5)
        if self.browser_manager.navigate_to_game():
            logging.info("Pemulihan L1 berhasil.")
            return True
        
        logging.warning("Pemulihan L1 gagal. Eskalasi ke L2: Login ulang penuh.")
        if self.browser_manager.logout() and self.browser_manager.login() and self.browser_manager.navigate_to_game():
            logging.info("Pemulihan L2 berhasil.")
            return True

        logging.critical("Semua upaya pemulihan gagal. Menghentikan agen.")
        self.running = False
        return False

    def run(self):
        self.running = True
        logging.info("--- Memulai Agen Real-time Live ---")
        
        if not self._initialize_modules():
            self.stop()
            return

        last_bet_on_period = pd.to_numeric(self.historical_data['Period']).max() if self.historical_data is not None and not self.historical_data.empty else 0
        last_round_time = time.time()
        logging.info(f"Agen memulai. Periode terakhir yang diketahui dari data adalah: {last_bet_on_period}")

        while self.running:
            try:
                self._check_commands()
                if self.is_paused:
                    time.sleep(1)
                    continue

                if time.time() - last_round_time > self.timeouts.get('recovery_threshold_seconds', 75):
                    if self._recover_session():
                        last_round_time = time.time()
                    else:
                        continue

                predicting_period_str = self.data_scraper.get_predicting_period()
                try:
                    predicting_period = int(predicting_period_str)
                except (ValueError, TypeError):
                    time.sleep(1)
                    continue
                
                if predicting_period > last_bet_on_period:
                    last_round_time = time.time()
                    logging.info(f"--- Ronde Baru Terdeteksi: {predicting_period}. Ronde sebelumnya adalah: {last_bet_on_period} ---")
                    
                    if last_bet_on_period > 0:
                        self._update_after_round(last_bet_on_period)
                    
                    self._handle_new_round(predicting_period)
                    last_bet_on_period = predicting_period
                
                time.sleep(1)

            except WebDriverException as e:
                logging.error(f"Loop agen real-time gagal karena error WebDriver: {e}", exc_info=True)
                if not self._recover_session():
                    break
            except Exception as e:
                logging.critical(f"Loop agen real-time menghadapi error tak terduga: {e}", exc_info=True)
                time.sleep(5)

        self.stop()

    def stop(self):
        if self.running:
            self.running = False
            logging.info("Sinyal berhenti diterima. Agen akan berhenti.")
        self.browser_manager.close()
        logging.info("--- Agen Real-time Berhenti ---")
        if self.gui_queue:
            self.gui_queue.put({"type": "agent_stopped"})
