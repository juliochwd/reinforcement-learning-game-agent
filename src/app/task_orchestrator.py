import threading
import logging
import tkinter as tk
import sys
import os

# --- Path Setup ---
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Late Imports (setelah path setup) ---
from src.rl_agent.realtime_agent import RealtimeAgent
from src.app.gui import ModernConsoleLogger, ModernProgressbarHandler

class TaskOrchestrator:
    def __init__(self, config):
        self.config = config
        self.gui_queue = None
        self.active_agent = None
        self.live_scrape_thread = None

    def set_gui_queue(self, gui_queue):
        self.gui_queue = gui_queue

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
        """
        Memulai tugas scraping data. Ini sekarang berjalan secara independen dari agen utama.
        """
        logging.info("Mempersiapkan untuk tugas scraping data mandiri.")
        scrape_agent = RealtimeAgent(self.config, self.gui_queue, phone=phone, password=password)
        self.run_in_thread(scrape_agent.run_standalone_scrape, button, progress_bar, eta_label, log_widget)

    def start_live_scrape(self, button, progress_bar, eta_label, log_widget, phone=None, password=None):
        """Memulai tugas live scraping di thread terpisah."""
        if self.active_agent:
            logging.warning("Live scrape sudah berjalan.")
            return

        logging.info("Mempersiapkan untuk tugas live scraping.")
        self.active_agent = RealtimeAgent(self.config, self.gui_queue, phone=phone, password=password)
        
        # Kita tidak memerlukan progress bar untuk tugas berkelanjutan seperti live scraping
        self.run_in_thread(self.active_agent.run_live_scrape, button, None, None, log_widget)

    def stop_live_scrape(self, button):
        """Menghentikan tugas live scraping yang sedang berjalan."""
        if self.active_agent:
            logging.info("Mengirim sinyal berhenti ke agen live scrape...")
            self.active_agent.stop()
            self.active_agent = None
            # GUI akan di-update melalui pesan 'live_scrape_finished' dari thread
        else:
            logging.warning("Tidak ada tugas live scrape yang sedang berjalan untuk dihentikan.")
            if button and self.gui_queue is not None:
                 self.gui_queue.put({"type": "task_finished", "button": button})

    def start_task(self, task_name, button, progress_bar, eta_label, log_widget):
        """
        Placeholder for task execution. All training/evaluation tasks have been removed.
        """
        logging.error(f"Task '{task_name}' is no longer available.")
        if button and self.gui_queue is not None:
            self.gui_queue.put({"type": "task_finished", "button": button})
