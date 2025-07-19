import logging
import time
import pandas as pd
import numpy as np
import os
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from src.utils.scraping import process_api_response

class DataScraper:
    """
    Bertanggung jawab untuk semua operasi scraping data dari situs web,
    baik dari UI maupun dengan mencegat panggilan API.
    """
    def __init__(self, driver, config, gemini_predictor=None):
        self.driver = driver
        self.config = config
        self.gemini_predictor = gemini_predictor
        self.web_agent_config = self.config.get('web_agent', {})
        self.timeouts = self.web_agent_config.get('timeouts', {})
        self.timers = self.web_agent_config.get('timers', {})
        self.xpaths = self.web_agent_config.get('xpaths', {})
        self.api_endpoint = self.web_agent_config.get('api_endpoint')

    def _get_selector(self, category, name):
        """Helper untuk mendapatkan By dan Value selector dari config."""
        try:
            selector_config = self.xpaths[category][name]
            by_str = selector_config.get('by', 'XPATH').upper()
            by = getattr(By, by_str)
            value = selector_config.get('value')
            if by is None or value is None:
                raise KeyError
            return by, value
        except KeyError:
            logging.error(f"Selector untuk '{category}.{name}' tidak ditemukan di config.yaml.")
            return (By.XPATH, "//invalid-xpath")  # Return a safe default

    def scrape_latest_result(self):
        """
        Mencegat panggilan API riwayat game untuk mendapatkan hasil ronde terakhir.
        Ini adalah metode yang disukai karena keandalan dan kecepatannya.
        """
        logging.info("Menunggu untuk menangkap hasil game terbaru dari API...")
        try:
            del self.driver.requests
            request = self.driver.wait_for_request(self.api_endpoint, timeout=self.timeouts.get('api_wait', 15))
            response_records = process_api_response(request)
            if not response_records:
                logging.warning("Panggilan API dicegat tetapi tidak ada catatan yang ditemukan.")
                return None
            
            latest_record = response_records[0]
            df = pd.DataFrame([latest_record])
            df.rename(columns={'issueNumber': 'Period', 'number': 'Number'}, inplace=True)
            
            # Filter untuk memastikan hanya game '10001' yang diproses
            if '10001' not in str(df['Period'].iloc[0]):
                logging.info(f"Mendapatkan hasil dari game yang tidak relevan (Periode: {df['Period'].iloc[0]}). Mengabaikan.")
                return None

            df['Number'] = pd.to_numeric(df['Number'])
            logging.info(f"Berhasil scrape hasil terbaru: Periode {df['Period'].iloc[0]}, Nomor {df['Number'].iloc[0]}")
            return df[['Period', 'Number']]
        except TimeoutException:
            logging.warning(f"Tidak ada permintaan API ke '{self.api_endpoint}' yang terdeteksi dalam batas waktu.")
            return None
        except Exception as e:
            logging.error(f"Gagal memproses permintaan API yang dicegat: {e}", exc_info=True)
            return None

    def get_current_balance(self, refresh=False):
        """Scrape saldo akun saat ini dari UI, dengan opsi untuk me-refresh."""
        try:
            cont_by, cont_val = self._get_selector('game_interface', 'balance_container')
            if not cont_by or not cont_val:
                raise NoSuchElementException("Selector for balance_container is invalid.")
            balance_container = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((cont_by, cont_val)))

            if refresh:
                logging.info("Me-refresh saldo...")
                ref_by, ref_val = self._get_selector('game_interface', 'balance_refresh_button')
                if not ref_by or not ref_val:
                    raise NoSuchElementException("Selector for balance_refresh_button is invalid.")
                refresh_button = WebDriverWait(balance_container, 10).until(EC.element_to_be_clickable((ref_by, ref_val)))
                self.driver.execute_script("arguments[0].click();", refresh_button)
                time.sleep(self.timers.get('post_action_sleep', 1))

            val_by, val_val = self._get_selector('game_interface', 'balance_value')
            if not val_by or not val_val:
                raise NoSuchElementException("Selector for balance_value is invalid.")
            balance_element = balance_container.find_element(val_by, val_val)
            balance_text = balance_element.text.replace('Rp', '').replace(',', '').strip()
            return float(balance_text)
        except (TimeoutException, NoSuchElementException):
            logging.warning("Tidak dapat menemukan elemen saldo atau waktu tunggu habis.")
            return None
        except (ValueError, TypeError) as e:
            logging.error(f"Gagal mem-parsing nilai saldo. Teks yang ditemukan tidak valid. Error: {e}")
            return None
        except WebDriverException as e:
            logging.warning(f"Tidak dapat scrape saldo saat ini karena error WebDriver: {e}")
            return None

    def get_predicting_period(self):
        """Scrape nomor periode untuk game yang akan datang."""
        try:
            by, val = self._get_selector('game_interface', 'period_display')
            if not by or not val:
                raise NoSuchElementException("Selector for period_display is invalid.")
            period_element = self.driver.find_element(by, val)
            return period_element.text.strip()
        except NoSuchElementException:
            logging.warning("Tidak dapat menemukan elemen periode prediksi.")
            return "Predicting..."
        except WebDriverException as e:
            logging.warning(f"Tidak dapat scrape periode prediksi: {e}")
            return "Predicting..."

    def get_current_timer(self):
        """Scrape nilai timer saat ini dari UI."""
        try:
            by, val = self._get_selector('game_interface', 'timer_display')
            if not by or not val:
                raise NoSuchElementException("Selector for timer_display is invalid.")
            timer_element = self.driver.find_element(by, val)
            return timer_element.text.strip()
        except NoSuchElementException:
            logging.warning("Tidak dapat menemukan elemen timer.")
            return "00:00"
        except WebDriverException as e:
            logging.error(f"Terjadi kesalahan WebDriver saat scrape timer: {e}")
            return "00:00"

    def _handle_post_login_popups(self):
        """Secara berulang mencari dan menutup semua pop-up 'Confirm' setelah login."""
        logging.info("Checking for post-login pop-ups...")
        max_popups_to_close = 10
        popups_closed = 0
        while popups_closed < max_popups_to_close:
            try:
                confirm_button_xpath = "//div[@class='promptBtn' and text()='Confirm']"
                confirm_button = WebDriverWait(self.driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, confirm_button_xpath))
                )
                logging.info(f"Found a 'Confirm' pop-up. Closing it (popup #{popups_closed + 1})...")
                self.driver.execute_script("arguments[0].click();", confirm_button)
                popups_closed += 1
                time.sleep(1)
            except TimeoutException:
                logging.info("No more 'Confirm' pop-ups found.")
                break
            except Exception as e:
                logging.error(f"An error occurred while handling pop-ups: {e}")
                break

    def _get_total_pages_from_ui(self, default_pages=1):
        """Membaca jumlah total halaman dari elemen UI."""
        try:
            page_info_element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'GameRecord__C-foot-page'))
            )
            page_text = page_info_element.text
            total_pages = int(page_text.split('/')[1])
            logging.info(f"Successfully parsed total pages from UI: {total_pages}")
            return total_pages
        except Exception as e:
            logging.error(f"Could not parse total pages from UI. Error: {e}. Defaulting to {default_pages} page(s).")
            return default_pages

    def execute_bulk_scrape(self):
        """
        Menjalankan proses scraping data riwayat permainan secara lengkap dengan
        menggunakan logika yang telah terbukti andal.
        """
        logging.info("--- Memulai Tugas Scraping Data Massal (Versi API) ---")
        try:
            # TAHAP 1: NAVIGASI DAN LOGIN (jika diperlukan)
            # Asumsi driver sudah terbuka, tapi kita pastikan di halaman login.
            if "login" not in self.driver.current_url:
                 self.driver.get(self.web_agent_config.get('login_url', 'https://55v7nlu.com/#/login'))

            # Cek apakah sudah login, jika belum, lakukan login
            try:
                WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.NAME, 'userNumber')))
                logging.info("Halaman login terdeteksi. Memulai proses login...")
                phone = os.getenv('PHONE_NUMBER')
                password = os.getenv('PASSWORD')
                if not (phone and password):
                    logging.critical("Variabel lingkungan PHONE_NUMBER atau PASSWORD tidak diatur. Proses login dibatalkan.")
                    return None
                
                # Masukkan nomor telepon dan tunggu hingga nilainya benar-benar diatur
                phone_input = self.driver.find_element(By.NAME, 'userNumber')
                phone_input.clear()
                phone_input.send_keys(phone)
                WebDriverWait(self.driver, 10).until(EC.text_to_be_present_in_element_value((By.NAME, 'userNumber'), phone))
                # Validasi manual jika perlu
                for _ in range(5):
                    if phone_input.get_attribute('value') == phone:
                        break
                    time.sleep(0.2)
                else:
                    logging.error('Phone input value did not match after retries.')
                    return None
                
                # Masukkan kata sandi dan tunggu hingga nilainya benar-benar diatur
                password_input = self.driver.find_element(By.XPATH, '//input[@placeholder="Password"]')
                password_input.clear()
                password_input.send_keys(password)
                WebDriverWait(self.driver, 10).until(EC.text_to_be_present_in_element_value((By.XPATH, '//input[@placeholder="Password"]'), password))
                for _ in range(5):
                    if password_input.get_attribute('value') == password:
                        break
                    time.sleep(0.2)
                else:
                    logging.error('Password input value did not match after retries.')
                    return None

                # Klik tombol login setelah input diisi
                login_button = self.driver.find_element(By.XPATH, '//button[text()="Log in"]')
                login_button.click()
                logging.info("Login submitted.")
            except TimeoutException:
                logging.info("Sudah dalam keadaan login atau halaman login tidak terdeteksi. Melanjutkan proses.")

            self._handle_post_login_popups()

            logging.info("Zooming out page to 80% to ensure all elements are visible...")
            self.driver.execute_script("document.body.style.zoom='80%'")

            # TAHAP 2: NAVIGASI KE PERMAINAN 'WIN GO 1MIN'
            logging.info("Navigating to the 'Win Go 1Min' game...")
            try:
                win_go_xpath = "//div[@class='lottery' and .//span[normalize-space()='Win Go']]"
                win_go_menu = WebDriverWait(self.driver, 30).until(EC.element_to_be_clickable((By.XPATH, win_go_xpath)))
                self.driver.execute_script("arguments[0].click();", win_go_menu)
                
                win_go_1min_xpath = "//div[contains(@class, 'GameList__C-item') and contains(., '1Min') and not(contains(., '30s'))]"
                win_go_1min_button = WebDriverWait(self.driver, 30).until(EC.element_to_be_clickable((By.XPATH, win_go_1min_xpath)))
                self.driver.execute_script("arguments[0].click();", win_go_1min_button)
                logging.info("Successfully navigated to 'Win Go 1Min'.")
            except TimeoutException as e:
                logging.critical(f"Failed to navigate to 'Win Go 1Min' game. Error: {e}")
                self.driver.save_screenshot("debug_screenshot_navigation_failed.png")
                return None

            # TAHAP 3: SCRAPING DATA
            total_pages = self._get_total_pages_from_ui()
            max_pages_to_scrape = self.web_agent_config.get('scraping', {}).get('max_pages', 300)
            all_records = []

            logging.info("Processing data for the initial page (Page 1)...")
            try:
                initial_request = next(req for req in reversed(self.driver.requests) if self.api_endpoint in req.url)
                records_on_page = process_api_response(initial_request)
                if records_on_page:
                    all_records.extend(records_on_page)
            except StopIteration:
                logging.critical("Could not find the initial API request for page 1. Aborting.")
                return None

            for page_num in range(2, min(total_pages, max_pages_to_scrape) + 1):
                logging.info(f"Navigating to page {page_num}/{min(total_pages, max_pages_to_scrape)}...")
                del self.driver.requests
                try:
                    next_button = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'GameRecord__C-foot-next')]"))
                    )
                    self.driver.execute_script("arguments[0].click();", next_button)
                except TimeoutException:
                    logging.warning("Could not find or click the 'next' button. Stopping pagination.")
                    break

                try:
                    request = self.driver.wait_for_request(self.api_endpoint, timeout=30)
                    records_on_page = process_api_response(request)
                    if records_on_page:
                        all_records.extend(records_on_page)
                    else:
                        logging.warning(f"No records processed from API response for page {page_num}.")
                except TimeoutException:
                    logging.error(f"Timed out waiting for API request on page {page_num}. Stopping.")
                    break
            
            # TAHAP 4: PROSES DAN SIMPAN DATA
            logging.info(f"Total records scraped via API: {len(all_records)}. Processing...")
            if not all_records:
                logging.warning("No records were scraped. Exiting.")
                return None

            df = pd.DataFrame(all_records)
            df.rename(columns={'issueNumber': 'Period', 'number': 'Number', 'colour': 'Color', 'premium': 'Premium'}, inplace=True)
            
            # Filter utama untuk memastikan hanya data dari game '10001' yang diproses
            df['Period'] = df['Period'].astype(str)
            initial_count = len(df)
            df = df[df['Period'].str.contains('10001', na=False)]
            filtered_count = len(df)
            logging.info(f"Memfilter data untuk game '10001'. {initial_count - filtered_count} dari {initial_count} record dihapus.")

            if df.empty:
                logging.warning("Tidak ada data untuk game '10001' yang ditemukan setelah pemfilteran.")
                return None

            df['Number'] = pd.to_numeric(df['Number'])
            df['Big/Small'] = np.where(df['Number'] >= 5, 'Big', 'Small')
            final_df = df[['Period', 'Number', 'Big/Small', 'Color', 'Premium']].copy()
            final_df['Period'] = final_df['Period'].astype(str)
            if isinstance(final_df, pd.DataFrame):
                final_df = final_df.sort_values(by='Period', ascending=True).drop_duplicates(subset='Period', keep='last')

            output_csv_path = self.config['project_setup']['data_path']
            try:
                existing_df = pd.read_csv(output_csv_path)
                existing_df['Period'] = existing_df['Period'].astype(str)
                if not isinstance(existing_df, pd.DataFrame):
                    existing_df = pd.DataFrame(existing_df)
                if not isinstance(final_df, pd.DataFrame):
                    final_df = pd.DataFrame(final_df)
                combined_df = pd.concat([existing_df, final_df], ignore_index=True)
            except FileNotFoundError:
                logging.info(f"'{output_csv_path}' not found. A new file will be created.")
                if not isinstance(final_df, pd.DataFrame):
                    combined_df = pd.DataFrame(final_df)
                else:
                    combined_df = final_df
            
            if isinstance(combined_df, pd.DataFrame):
                combined_df = combined_df.drop_duplicates(subset='Period', keep='last')
                combined_df = combined_df.sort_values(by='Period', ascending=True)
                combined_df.to_csv(output_csv_path, index=False)
            logging.info(f"SUCCESS: All {len(combined_df)} unique records have been saved to '{output_csv_path}'")
            return combined_df

        except Exception as e:
            logging.critical(f"An unrecoverable error occurred during the scraping process: {e}", exc_info=True)
            return None
        finally:
            logging.info("--- Tugas Scraping Data Massal Selesai ---")
            # Navigasi kembali ke halaman game utama untuk melanjutkan operasi normal
            try:
                game_page_url = self.web_agent_config.get('game_url') # Asumsi URL game ada di config
                if game_page_url and self.driver.current_url != game_page_url:
                    self.driver.get(game_page_url)
            except Exception as nav_e:
                logging.warning(f"Could not navigate back to the main game page: {nav_e}")

    def start_live_scraping(self, stop_event):
        """
        Memulai proses scraping data secara live, dipicu oleh pembaruan API,
        dan berhenti ketika event berhenti diatur.
        """
        import time
        logging.info("--- Memulai Live Scraping Berbasis API Event ---")
        logging.info("Live scraping akan berjalan terus menerus. Tekan Ctrl+C untuk berhenti.")
        output_csv_path = self.config['project_setup']['data_path']
        
        # Get configuration values
        scraping_config = self.web_agent_config.get('scraping', {})
        max_iterations = scraping_config.get('max_live_iterations', 100)
        max_time_minutes = scraping_config.get('live_timeout_minutes', 30)
        
        iteration_count = 0
        max_empty_iterations = 50  # Stop after 50 empty iterations
        empty_iterations = 0
        start_time = time.time()
        max_time_seconds = max_time_minutes * 60
        
        logging.info(f"Live scraping auto-stop: {max_iterations} iterations or {max_time_minutes} minutes")
        
        while not stop_event.is_set():
            iteration_count += 1
            current_time = time.time()
            elapsed_minutes = (current_time - start_time) / 60
            
            # Check time limit
            if current_time - start_time > max_time_seconds:
                logging.info(f"Auto-stopping: Time limit reached ({max_time_minutes} minutes)")
                break
                
            # Check iteration limit
            if iteration_count > max_iterations:
                logging.info(f"Auto-stopping: Iteration limit reached ({max_iterations} iterations)")
                break
            
            logging.info(f"Live scraping iteration #{iteration_count}/{max_iterations} ({elapsed_minutes:.1f}/{max_time_minutes} min) - Menunggu pembaruan API...")
            
            try:
                # Hapus request sebelumnya untuk memastikan kita menangkap yang baru
                del self.driver.requests
                
                # Tunggu permintaan dengan timeout untuk memungkinkan pemeriksaan stop_event
                request = self.driver.wait_for_request(self.api_endpoint, timeout=5)
                
                logging.info(f"Permintaan API terdeteksi pada iterasi #{iteration_count}. Memproses data...")
                response_records = process_api_response(request)
                
                if not response_records:
                    logging.warning("API terdeteksi tetapi tidak ada catatan yang ditemukan.")
                    empty_iterations += 1
                    if empty_iterations >= max_empty_iterations:
                        logging.info(f"Auto-stopping: Tidak ada data baru setelah {max_empty_iterations} iterasi.")
                        break
                    continue
                else:
                    empty_iterations = 0  # Reset counter when we get data

                latest_df = pd.DataFrame(response_records)
                latest_df.rename(columns={'issueNumber': 'Period', 'number': 'Number', 'colour': 'Color', 'premium': 'Premium'}, inplace=True)
                
                # Filter untuk memastikan hanya game '10001' yang diproses secara live
                latest_df['Period'] = latest_df['Period'].astype(str)
                if not latest_df['Period'].str.contains('10001').any():
                    logging.info(f"Data live yang diterima bukan untuk game '10001'. Mengabaikan.")
                    continue
                
                # Proses dan simpan data
                try:
                    # Baca data yang ada
                    try:
                        existing_df = pd.read_csv(output_csv_path)
                        existing_df['Period'] = existing_df['Period'].astype(str)
                    except FileNotFoundError:
                        logging.info(f"File data '{output_csv_path}' tidak ditemukan. Membuat file baru.")
                        existing_df = pd.DataFrame({col: pd.Series(dtype='object') for col in ["Period", "Number", "Big/Small", "Color", "Premium"]})

                    latest_df['Period'] = latest_df['Period'].astype(str)
                    latest_df['Number'] = pd.to_numeric(latest_df['Number'])
                    latest_df['Big/Small'] = np.where(latest_df['Number'] >= 5, 'Big', 'Small')

                    if not isinstance(existing_df, pd.DataFrame):
                        existing_df = pd.DataFrame(existing_df)
                    if not isinstance(latest_df, pd.DataFrame):
                        latest_df = pd.DataFrame(latest_df)
                    combined_df = pd.concat([existing_df, latest_df], ignore_index=True)
                    
                    final_cols = ['Period', 'Number', 'Big/Small', 'Color', 'Premium']
                    for col in final_cols:
                        if col not in combined_df.columns:
                            combined_df[col] = pd.NA
                    combined_df = combined_df[final_cols]

                    if isinstance(combined_df, pd.DataFrame):
                        combined_df = combined_df.drop_duplicates(subset='Period', keep='last')
                        combined_df = combined_df.sort_values(by='Period', ascending=True)
                        if not combined_df.equals(existing_df):
                            combined_df.to_csv(output_csv_path, index=False)
                            if self.gemini_predictor:
                                logging.info("Memanggil Gemini untuk prediksi periode berikutnya...")
                                try:
                                    context_df = combined_df.tail(200)
                                    prediction_result = self.gemini_predictor.predict_next_period(context_df)
                                    prediction_path = os.path.join(os.path.dirname(output_csv_path), "next_prediction.txt")
                                    with open(prediction_path, "w") as f:
                                        f.write(prediction_result)
                                    logging.info(f"Prediksi disimpan ke {prediction_path}")
                                    # Tampilkan prediksi di konsol
                                    print("\n--- PREDIKSI PERIODE BERIKUTNYA ---")
                                    print(prediction_result)
                                    print("-------------------------------------\n")
                                except Exception as e:
                                    logging.error(f"Gagal menghasilkan atau menyimpan prediksi: {e}", exc_info=True)
                        else:
                            logging.info("Tidak ada data baru yang terdeteksi. Melewati penyimpanan dan prediksi.")
                    else:
                        logging.warning("Combined DataFrame is not a DataFrame, skipping save.")

                except Exception as e:
                    logging.error(f"Gagal memproses atau menyimpan data live: {e}", exc_info=True)

            except TimeoutException:
                # Timeout diharapkan, ini memungkinkan loop untuk memeriksa stop_event
                logging.debug("Tidak ada permintaan API dalam interval waktu. Melanjutkan pengecekan...")
                continue
            except Exception as e:
                if not stop_event.is_set():
                    logging.error(f"Terjadi kesalahan tak terduga dalam loop live scraping: {e}", exc_info=True)
                time.sleep(5) # Tunggu sebentar sebelum mencoba lagi

        # Log the reason for stopping
        if stop_event.is_set():
            logging.info("--- Live Scraping Dihentikan oleh pengguna (Ctrl+C) ---")
        else:
            logging.info("--- Live Scraping Dihentikan secara otomatis ---")
        
        logging.info(f"Total iterasi yang dijalankan: {iteration_count}")
        elapsed_total = (time.time() - start_time) / 60
        logging.info(f"Total waktu berjalan: {elapsed_total:.1f} menit")
