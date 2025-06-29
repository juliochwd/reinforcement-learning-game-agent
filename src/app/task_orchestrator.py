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
from src.rl_agent import train, evaluate, randomness_test, hyperparameter_search
from src.rl_agent.realtime_agent import RealtimeAgent
from src.app.gui import ConsoleLogger, ProgressbarHandler

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

        button.config(state=tk.DISABLED)
        default_eta = self.config.get('ui', {}).get('default_eta_text', "ETA: --:--")
        if progress_bar:
            progress_bar.config(value=0)
        if eta_label:
            eta_label.config(text=default_eta)

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

    def start_bulk_scrape(self):
        if self.realtime_agent and self.realtime_agent.running:
            logging.info("Agent is running. Sending bulk scrape command to the active agent...")
            self.realtime_agent.command_queue.put("scrape_bulk")
        else:
            logging.warning("Scrape command ignored. Please start the agent on the Dashboard first.")

    def start_task(self, task_name, button, progress_bar, eta_label, log_widget):
        task_map = {
            'train': train.main,
            'evaluate': evaluate.main,
            'randomness_test': randomness_test.main,
            'hyperparameter_search': hyperparameter_search.main
        }
        
        target_func = task_map.get(task_name)
        if target_func:
            self.run_in_thread(target_func, button, progress_bar, eta_label, log_widget)
        else:
            logging.error(f"Unknown task name: {task_name}")