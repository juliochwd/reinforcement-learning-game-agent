import logging
import time
import pandas as pd
import numpy as np
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
    def __init__(self, driver, config):
        self.driver = driver
        self.config = config
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
            return by, value
        except KeyError:
            logging.error(f"Selector untuk '{category}.{name}' tidak ditemukan di config.yaml.")
            return None, None

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
            balance_container = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((cont_by, cont_val)))

            if refresh:
                logging.info("Me-refresh saldo...")
                ref_by, ref_val = self._get_selector('game_interface', 'balance_refresh_button')
                refresh_button = WebDriverWait(balance_container, 10).until(EC.element_to_be_clickable((ref_by, ref_val)))
                self.driver.execute_script("arguments[0].click();", refresh_button)
                time.sleep(self.timers.get('post_action_sleep', 1))

            val_by, val_val = self._get_selector('game_interface', 'balance_value')
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
            timer_element = self.driver.find_element(by, val)
            return timer_element.text.strip()
        except NoSuchElementException:
            logging.warning("Tidak dapat menemukan elemen timer.")
            return "00:00"
        except WebDriverException as e:
            logging.error(f"Terjadi kesalahan WebDriver saat scrape timer: {e}")
            return "00:00"

    def execute_bulk_scrape(self):
        """
        Menavigasi ke halaman riwayat permainan dan melakukan scrape beberapa halaman
        data untuk membangun atau memperbarui dataset historis lokal.
        """
        logging.info("--- Memulai Scrape Data Massal menggunakan sesi yang ada ---")
        try:
            my_acc_by, my_acc_val = self._get_selector('navigation', 'my_account_button')
            my_account_button = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((my_acc_by, my_acc_val)))
            my_account_button.click()
            
            hist_by, hist_val = self._get_selector('navigation', 'game_history_button')
            game_history_button = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((hist_by, hist_val)))
            game_history_button.click()
            time.sleep(self.timers.get('api_retry_delay', 2))

            max_pages = self.web_agent_config.get('scraping', {}).get('max_pages', 300)
            all_records = []

            for page_num in range(1, max_pages + 1):
                logging.info(f"Scraping halaman {page_num}/{max_pages}...")
                del self.driver.requests
                
                if page_num > 1:
                    try:
                        next_by, next_val = self._get_selector('navigation', 'history_next_page_button')
                        next_button = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((next_by, next_val)))
                        self.driver.execute_script("arguments[0].click();", next_button)
                    except TimeoutException:
                        logging.info("Tidak ada tombol halaman 'berikutnya' yang ditemukan. Mengakhiri scrape massal.")
                        break
                
                try:
                    request = self.driver.wait_for_request(self.api_endpoint, timeout=self.timeouts.get('api_wait', 30))
                    records_on_page = process_api_response(request)
                    if records_on_page:
                        all_records.extend(records_on_page)
                    else:
                        logging.warning(f"Tidak ada catatan yang ditemukan di halaman {page_num}. Mengakhiri scrape massal.")
                        break
                except TimeoutException:
                    logging.error(f"Permintaan API timed out di halaman {page_num}. Mengakhiri scrape massal.")
                    break
            
            logging.info(f"Scrape massal selesai. Total catatan yang ditemukan: {len(all_records)}")
            if all_records:
                df = pd.DataFrame(all_records)
                df.rename(columns={'issueNumber': 'Period', 'number': 'Number', 'colour': 'Color', 'premium': 'Premium'}, inplace=True)
                df['Number'] = pd.to_numeric(df['Number'])
                df['Big/Small'] = np.where(df['Number'] >= 5, 'Big', 'Small')
                final_df = df[['Period', 'Number', 'Big/Small', 'Color', 'Premium']].copy()
                final_df = final_df.sort_values(by='Period', ascending=True).drop_duplicates(subset='Period', keep='last')
                
                output_csv_path = self.config['data_path']
                try:
                    existing_df = pd.read_csv(output_csv_path)
                    combined_df = pd.concat([existing_df, final_df], ignore_index=True)
                except FileNotFoundError:
                    combined_df = final_df
                
                combined_df.drop_duplicates(subset='Period', keep='last', inplace=True)
                combined_df.sort_values(by='Period', ascending=True, inplace=True)
                combined_df.to_csv(output_csv_path, index=False)
                logging.info(f"BERHASIL: Semua {len(combined_df)} catatan unik disimpan ke '{output_csv_path}'")
                return combined_df
            return None
        except (TimeoutException, NoSuchElementException) as e:
            logging.error(f"Elemen navigasi untuk scrape massal tidak ditemukan: {e}", exc_info=True)
            return None
        except WebDriverException as e:
            logging.error(f"Terjadi kesalahan WebDriver saat scrape massal: {e}", exc_info=True)
            return None
        finally:
            logging.info("--- Scrape Data Massal Selesai ---")
            self.driver.back()
            self.driver.back()