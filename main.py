import os
import sys
import yaml
import logging

# --- Path Setup ---
# Menambahkan root direktori proyek ke sys.path untuk memastikan impor modul berjalan lancar.
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.app.gui import App
from src.app.task_orchestrator import TaskOrchestrator

def setup_logging(config):
    """Mengkonfigurasi logging dasar untuk aplikasi."""
    log_config = config.get('logging', {})
    logging.basicConfig(
        level=log_config.get('level', 'INFO'),
        format=log_config.get('format', '%(asctime)s - %(levelname)s - %(message)s'),
        datefmt=log_config.get('datefmt', '%Y-%m-%d %H:%M:%S')
    )

def load_config():
    """Memuat file konfigurasi utama (config.yaml)."""
    config_path = os.path.join(project_root, 'config.yaml')
    try:
        with open(config_path, 'r', encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return config
    except FileNotFoundError:
        logging.critical(f"Error: Configuration file not found at {config_path}")
        sys.exit(1)
    except yaml.YAMLError as e:
        logging.critical(f"Error parsing YAML file: {e}")
        sys.exit(1)

def main():
    """Fungsi utama untuk menjalankan aplikasi."""
    # 1. Muat konfigurasi
    config = load_config()
    
    # 2. Setup logging
    setup_logging(config)

    # 3. Inisialisasi Orkestrator Tugas
    task_orchestrator = TaskOrchestrator(config)
    
    # 4. Inisialisasi dan jalankan GUI
    # GUI akan memegang referensi ke orkestrator untuk mendelegasikan tindakan.
    app = App(config, task_orchestrator)
    app.mainloop()

if __name__ == "__main__":
    main()