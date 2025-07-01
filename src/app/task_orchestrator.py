import threading
import logging
import tkinter as tk
import sys
import os
import subprocess

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

    def run_vm_training_pipeline(self):
        """
        Executes the training pipeline on a remote VM via SSH.
        """
        logging.info("--- Preparing to run pipeline on VM ---")
        vm_config = self.config.get('vm_pipeline')
        if not vm_config:
            logging.error("VM pipeline configuration ('vm_pipeline') not found in config.yaml.")
            return

        try:
            # Upload the new pipeline script first
            scp_command = [
                'scp',
                '-i', vm_config['ssh_key_path'],
                'pipeline.sh',
                f"{vm_config['user']}@{vm_config['host']}:{vm_config['remote_script_path']}"
            ]
            logging.info(f"Uploading pipeline script: {' '.join(scp_command)}")
            subprocess.run(scp_command, check=True)

            # A more robust command to ensure Python 3.12 is installed and used.
            remote_command = f"""
DEBIAN_FRONTEND=noninteractive
PYTHON_VERSION="3.12.6"
PYTHON_MAJOR="3.12"
REMOTE_PROJECT_PATH="{os.path.dirname(vm_config['remote_script_path'])}"

# Check if Python 3.12 is already installed
if ! command -v python$PYTHON_MAJOR &> /dev/null; then
    echo "Python $PYTHON_MAJOR not found. Installing..."
    
    # Update and install build dependencies
    sudo apt-get update -y
    sudo apt-get install -y build-essential zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev libssl-dev libreadline-dev libffi-dev libsqlite3-dev wget libbz2-dev
    
    # Download, compile, and install Python
    wget "https://www.python.org/ftp/python/$PYTHON_VERSION/Python-$PYTHON_VERSION.tgz"
    tar -xf "Python-$PYTHON_VERSION.tgz"
    cd "Python-$PYTHON_VERSION"
    ./configure --enable-optimizations
    make -j$(nproc)
    sudo make altinstall
    cd ..
    rm -rf "Python-$PYTHON_VERSION" "Python-$PYTHON_VERSION.tgz"
    
    # Install pip for the new version
    wget https://bootstrap.pypa.io/get-pip.py
    sudo python$PYTHON_MAJOR get-pip.py
    rm get-pip.py
else
    echo "Python $PYTHON_MAJOR is already installed."
fi

# Now, execute the pipeline script using the correct python version
# The pipeline script should be modified to use `python3.12`
cd $REMOTE_PROJECT_PATH && bash pipeline.sh
"""
            
            ssh_command = [
                'ssh',
                '-i', vm_config['ssh_key_path'],
                f"{vm_config['user']}@{vm_config['host']}",
                remote_command
            ]
            
            logging.info(f"Executing command: {' '.join(ssh_command)}")
            
            # Use Popen to stream output in real-time
            process = subprocess.Popen(
                ssh_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
                encoding='utf-8',
                errors='replace'
            )

            # Log stdout and handle progress updates
            for line in process.stdout:
                line = line.strip()
                if line.startswith("PROGRESS:"):
                    try:
                        # Extract percentage, e.g., "PROGRESS: 50%" -> 50
                        progress_str = line.split(':')[1].strip().replace('%', '')
                        progress_value = int(progress_str)
                        # GUI update must be thread-safe, so we put it in the queue
                        if self.gui_queue:
                            self.gui_queue.put({"type": "progress", "value": progress_value / 100.0})
                    except (ValueError, IndexError) as e:
                        logging.warning(f"Could not parse progress line: {line} - Error: {e}")
                else:
                    logging.info(line)

            # Log stderr after stdout is done
            stderr_output = process.stderr.read()
            if stderr_output:
                logging.error("--- VM Script Errors ---")
                logging.error(stderr_output.strip())
                
            process.wait()
            
            if process.returncode == 0:
                logging.info("--- VM pipeline finished successfully. ---")
            else:
                logging.error(f"--- VM pipeline failed with exit code {process.returncode}. ---")

        except FileNotFoundError:
            logging.error("Error: 'ssh' command not found. Is OpenSSH client installed and in your system's PATH?")
        except Exception as e:
            logging.error(f"An error occurred while running the VM pipeline: {e}", exc_info=True)

    def start_task(self, task_name, button, progress_bar, eta_label, log_widget):
        task_map = {
            'full_train': self.run_offline_training_pipeline,
            'full_train_vm': self.run_vm_training_pipeline,
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
