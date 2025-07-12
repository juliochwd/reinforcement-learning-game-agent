import threading
import logging
import tkinter as tk
import sys
import os

# --- Path Setup ---
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.app.gui import ModernConsoleLogger, ModernProgressbarHandler
from src.app.supervised_ensemble_trainer import SupervisedEnsembleTrainer

class TaskOrchestrator:
    def __init__(self, config):
        self.config = config
        self.gui_queue = None
        self.active_agent = None
        self.live_scrape_thread = None
        self.ensemble_trainer = SupervisedEnsembleTrainer()
        self.ensemble_trainer.gui_queue = None  # Akan di-set oleh set_gui_queue
        self.watcher_started = False
        self.gui_controller = None  # Tambahkan ini

    def set_gui_controller(self, gui_controller):
        self.gui_controller = gui_controller

    def set_gui_queue(self, gui_queue):
        self.gui_queue = gui_queue
        self.ensemble_trainer.gui_queue = gui_queue

    def run_in_thread(self, target_func, button, progress_bar, eta_label, log_widget):
        if not self.gui_queue:
            print("ERROR: GUI Queue not set in TaskOrchestrator.")
            return

        button.configure(state=tk.DISABLED)
        default_eta = self.config.get('ui', {}).get('default_eta_text', "ETA: --:--")
        if progress_bar:
            progress_bar.set(0)
        if eta_label:
            eta_label.configure(text=default_eta)

        logger = logging.getLogger()
        if logger.hasHandlers():
            logger.handlers.clear()
        logger.setLevel(logging.INFO)
        logger.addHandler(ModernConsoleLogger())
        if progress_bar and eta_label:
            logger.addHandler(ModernProgressbarHandler(self.gui_queue, progress_bar, eta_label, default_eta))

        def thread_wrapper():
            try:
                target_func()
            except Exception as e:
                logging.critical(f"UNHANDLED EXCEPTION IN THREAD for {target_func.__name__}: {e}", exc_info=True)
            finally:
                if self.gui_queue is not None:
                    self.gui_queue.put({"type": "task_finished", "button": button})

        threading.Thread(target=thread_wrapper, daemon=True).start()

    def start_bulk_scrape(self, button, progress_bar, eta_label, log_widget, phone=None, password=None):
        logging.info("Mempersiapkan untuk tugas scraping data mandiri.")
        def do_scrape():
            try:
                from src.rl_agent.browser_manager import BrowserManager
                from src.rl_agent.data_scraper import DataScraper
                if self.gui_queue:
                    self.gui_queue.put({"type": "progress_indeterminate_start"})
                    self.gui_queue.put({"type": "log", "record": "[Scrape] Browser dibuka, memulai login..."})
                browser_mgr = BrowserManager(self.config)
                driver = browser_mgr.initialize_driver()
                if not browser_mgr.login(phone, password):
                    logging.error("Login gagal. Scraping dibatalkan.")
                    if self.gui_queue:
                        self.gui_queue.put({"type": "log", "record": "[Scrape] Login gagal. Scraping dibatalkan."})
                        self.gui_queue.put({"type": "progress_indeterminate_stop"})
                    browser_mgr.close()
                    return
                if self.gui_queue:
                    self.gui_queue.put({"type": "log", "record": "[Scrape] Login berhasil, menavigasi ke game..."})
                if not browser_mgr.navigate_to_game():
                    logging.error("Navigasi ke game gagal. Scraping dibatalkan.")
                    if self.gui_queue:
                        self.gui_queue.put({"type": "log", "record": "[Scrape] Navigasi ke game gagal. Scraping dibatalkan."})
                        self.gui_queue.put({"type": "progress_indeterminate_stop"})
                    browser_mgr.close()
                    return
                if self.gui_queue:
                    self.gui_queue.put({"type": "log", "record": "[Scrape] Navigasi berhasil, mulai scraping data..."})
                scraper = DataScraper(driver, self.config)
                scraper.execute_bulk_scrape()
                if self.gui_queue:
                    self.gui_queue.put({"type": "log", "record": "[Scrape] Scraping selesai."})
                    self.gui_queue.put({"type": "progress_indeterminate_stop"})
            except Exception as e:
                logging.error(f"Scraping gagal: {e}", exc_info=True)
                if self.gui_queue:
                    self.gui_queue.put({"type": "log", "record": f"[Scrape] Scraping gagal: {e}"})
                    self.gui_queue.put({"type": "progress_indeterminate_stop"})
            finally:
                try:
                    browser_mgr.close()
                except Exception:
                    pass
        self.run_in_thread(do_scrape, button, progress_bar, eta_label, log_widget)

    def start_live_scrape(self, button, progress_bar, eta_label, log_widget, phone=None, password=None, mode="both"):
        import threading
        from src.rl_agent.browser_manager import BrowserManager
        from src.rl_agent.data_scraper import DataScraper

        # Stop event untuk live scraping API
        if not hasattr(self, 'live_scrape_stop_event') or self.live_scrape_stop_event is None:
            self.live_scrape_stop_event = threading.Event()
        else:
            self.live_scrape_stop_event.clear()

        def live_scrape_api():
            try:
                browser_mgr = BrowserManager(self.config)
                driver = browser_mgr.initialize_driver()
                if not browser_mgr.login(phone, password):
                    if self.gui_queue:
                        self.gui_queue.put({"type": "log", "record": "[LiveScrape] Login gagal."})
                    browser_mgr.close()
                    return
                if not browser_mgr.navigate_to_game():
                    if self.gui_queue:
                        self.gui_queue.put({"type": "log", "record": "[LiveScrape] Navigasi gagal."})
                    browser_mgr.close()
                    return
                scraper = DataScraper(driver, self.config)
                if self.gui_queue:
                    self.gui_queue.put({"type": "log", "record": "[LiveScrape] Live scraping API dimulai."})
                scraper.start_live_scraping(self.live_scrape_stop_event)
            except Exception as e:
                if self.gui_queue:
                    self.gui_queue.put({"type": "log", "record": f"[LiveScrape] Error: {e}"})
            finally:
                try:
                    browser_mgr.close()
                except Exception:
                    pass
                if self.gui_queue:
                    self.gui_queue.put({"type": "log", "record": "[LiveScrape] Live scraping API dihentikan."})

        # Jalankan watcher CSV (selalu, agar backward compatible)
        if not self.watcher_started:
            self.ensemble_trainer.start_csv_watcher()
            self.watcher_started = True
            if self.gui_queue:
                self.gui_queue.put({"type": "log", "record": "[LiveScrape] Watcher CSV dimulai."})

        # Jalankan live scraping API jika mode bukan hanya csv
        if mode in ("api", "both"):
            t = threading.Thread(target=live_scrape_api, daemon=True)
            t.start()
            if self.gui_queue:
                self.gui_queue.put({"type": "log", "record": "[LiveScrape] Thread live scraping API dijalankan."})

    def stop_live_scrape(self, button):
        if hasattr(self, 'live_scrape_stop_event') and self.live_scrape_stop_event:
            self.live_scrape_stop_event.set()
            if self.gui_queue:
                self.gui_queue.put({"type": "log", "record": "[LiveScrape] Stop signal dikirim ke live scraping API."})
        # Tidak perlu menghentikan watcher CSV, biarkan tetap berjalan (atau tambahkan stop jika ingin)

    def start_hyperparameter_search(self, button, progress_bar, eta_label, log_widget, n_trials=30):
        def run_search():
            self.ensemble_trainer.run_optuna_search(n_trials=n_trials)
        self.run_in_thread(run_search, button, progress_bar, eta_label, log_widget)

    def start_task(self, task_name, button, progress_bar, eta_label, log_widget):
        # Pastikan ensemble_trainer selalu pakai controller terbaru
        self.ensemble_trainer.controller = self.gui_controller
        def run_train_ensemble():
            self.ensemble_trainer.train_ensemble()
        def run_evaluate_ensemble():
            self.ensemble_trainer.evaluate_ensemble()
        def run_predict_ensemble():
            self.ensemble_trainer.predict_ensemble()
        def run_feature_importance():
            self.ensemble_trainer.show_feature_importance()
        def run_ensemble_analysis():
            self.ensemble_trainer.show_ensemble_analysis()
        def run_hyperparameter_search():
            self.start_hyperparameter_search(button, progress_bar, eta_label, log_widget)
        def run_retrain_on_all_data():
            self.ensemble_trainer.retrain_on_all_data()
        if task_name == "train_ensemble":
            self.run_in_thread(run_train_ensemble, button, progress_bar, eta_label, log_widget)
        elif task_name == "evaluate_ensemble":
            self.run_in_thread(run_evaluate_ensemble, button, progress_bar, eta_label, log_widget)
        elif task_name == "predict_ensemble":
            self.run_in_thread(run_predict_ensemble, button, progress_bar, eta_label, log_widget)
        elif task_name == "feature_importance":
            self.run_in_thread(run_feature_importance, button, progress_bar, eta_label, log_widget)
        elif task_name == "ensemble_analysis":
            self.run_in_thread(run_ensemble_analysis, button, progress_bar, eta_label, log_widget)
        elif task_name == "retrain_on_all_data":
            self.run_in_thread(run_retrain_on_all_data, button, progress_bar, eta_label, log_widget)
        elif task_name == "hyperparameter_search":
            run_hyperparameter_search()
        else:
            logging.error(f"Task '{task_name}' is no longer available.")
            if button and self.gui_queue is not None:
                self.gui_queue.put({"type": "task_finished", "button": button})
