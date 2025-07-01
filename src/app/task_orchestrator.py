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
from src.rl_agent import evaluate, randomness_test, hyperparameter_search, predictlive
from src.rl_agent.train import train as train_sac
import train_final_model
import estimate_training_time
from src.rl_agent.realtime_agent import RealtimeAgent
from src.app.gui import ConsoleLogger, ProgressbarHandler
from src.utils.model_helpers import load_config

class TaskOrchestrator:
    def __init__(self, config):
        self.config = config
        self.gui_queue = None
        self.realtime_agent = None

    def set_gui_queue(self, gui_queue):
        self.gui_queue = gui_queue

    def run_in_thread(self, target_func, button, progress_bar, eta_label, log_widget):
        if not self.gui_queue:
            print("ERROR: GUI Queue not set in TaskOrchestrator.")
            return

        button.configure(state=tk.DISABLED)
        default_eta = self.config.get('ui', {}).get('default_eta_text', "ETA: --:--")
        if progress_bar:
            progress_bar.set(0) # Progressbar uses .set()
        if eta_label:
            eta_label.configure(text=default_eta)

        logger = logging.getLogger()
        if logger.hasHandlers():
            logger.handlers.clear()
        logger.setLevel(logging.INFO)
        logger.addHandler(ConsoleLogger())
        if progress_bar and eta_label:
            logger.addHandler(ProgressbarHandler(self.gui_queue, progress_bar, eta_label, default_eta))

        def thread_wrapper():
            try:
                target_func()
            except Exception as e:
                logging.critical(f"UNHANDLED EXCEPTION IN THREAD for {target_func.__name__}: {e}", exc_info=True)
            finally:
                self.gui_queue.put({"type": "task_finished", "button": button})

        threading.Thread(target=thread_wrapper, daemon=True).start()

    def start_agent_task(self, button, progress_bar, eta_label, log_widget):
        self.realtime_agent = RealtimeAgent(self.config, self.gui_queue)
        self.run_in_thread(self.realtime_agent.run, button, progress_bar, eta_label, log_widget)

    def stop_agent_task(self):
        if self.realtime_agent:
            self.realtime_agent.stop()
            self.realtime_agent = None

    def start_bulk_scrape(self, button, progress_bar, eta_label, log_widget, phone=None, password=None):
        """
        Memulai tugas scraping data. Ini sekarang berjalan secara independen dari agen utama.
        """
        logging.info("Mempersiapkan untuk tugas scraping data mandiri.")
        # Buat instance agen sementara hanya untuk scraping, teruskan kredensial
        scrape_agent = RealtimeAgent(self.config, self.gui_queue, phone=phone, password=password)
        # Jalankan metode scraping mandiri di thread terpisah
        self.run_in_thread(scrape_agent.run_standalone_scrape, button, progress_bar, eta_label, log_widget)

    def run_offline_training_pipeline(self):
        """
        Runs the full training pipeline (HPT then final training) directly
        in Python, without using Docker or shell scripts.
        """
        try:
            logging.info("--- STAGE 1: Starting Hyperparameter Search ---")
            hyperparameter_search.main()
            logging.info("--- STAGE 1: Hyperparameter Search Finished Successfully ---")
            
            logging.info("--- STAGE 2: Starting Final Model Training ---")
            train_final_model.main()
            logging.info("--- STAGE 2: Final Model Training Finished Successfully ---")
            
            logging.info("Full offline training pipeline completed.")
        except Exception as e:
            logging.error(f"An error occurred during the offline training pipeline: {e}", exc_info=True)

    def run_single_training(self):
        """Runs a single training session with parameters from config."""
        logging.info("Starting single SAC training session...")
        config = load_config()
        sac_params = config.get('sac_hyperparameters', {})
        train_sac(
            lr=sac_params.get('lr', 3e-4),
            gamma=sac_params.get('gamma', 0.99),
            hidden_size=sac_params.get('hidden_size', 256),
            dropout_rate=sac_params.get('dropout_rate', 0.2),
            batch_size=sac_params.get('batch_size', 256),
            buffer_size=sac_params.get('buffer_size', 1_000_000),
            tau=sac_params.get('tau', 0.005),
            alpha=sac_params.get('alpha', 0.2),
            autotune_alpha=sac_params.get('autotune_alpha', True),
            total_timesteps=sac_params.get('total_timesteps', 100_000),
            learning_starts=sac_params.get('learning_starts', 5000)
        )
        logging.info("Single SAC training session finished.")

    def start_task(self, task_name, button, progress_bar, eta_label, log_widget):
        task_map = {
            'full_train': self.run_offline_training_pipeline,
            'single_train': self.run_single_training,
            'final_train': train_final_model.main,
            'hpt': hyperparameter_search.main,
            'evaluate': evaluate.main,
            'randomness_test': randomness_test.main,
            'estimate_time': estimate_training_time.main,
            'predict_headless': predictlive.predict_live,
        }
        
        target_func = task_map.get(task_name)
        if target_func:
            self.run_in_thread(target_func, button, progress_bar, eta_label, log_widget)
        else:
            logging.error(f"Unknown task name: {task_name}")
