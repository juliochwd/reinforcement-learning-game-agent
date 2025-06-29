import logging
import yaml
import json
import os

# Impor fungsi yang diperlukan
from run_optuna_hpt import run_hyperparameter_tuning
from src.rl_agent.train import train

def main():
    """
    Menjalankan pipeline pelatihan yang disederhanakan.
    1. Menjalankan Hyperparameter Tuning (HPT) untuk menemukan parameter terbaik.
    2. Melatih model akhir menggunakan parameter terbaik dari HPT.
    """
    # Konfigurasi logging dasar
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Memuat konfigurasi untuk mendapatkan jumlah episode pelatihan penuh
    try:
        with open("config.yaml", 'r') as f:
            config = yaml.safe_load(f)
        num_episodes_full = config.get('num_episodes_full', 500) # Default 500 jika tidak ada
    except FileNotFoundError:
        logging.error("File 'config.yaml' tidak ditemukan. Menggunakan jumlah episode default.")
        num_episodes_full = 500
    except Exception as e:
        logging.error(f"Gagal memuat config.yaml: {e}. Menggunakan jumlah episode default.")
        num_episodes_full = 500

    # --- Langkah 1: Hyperparameter Tuning ---
    logging.info("--- Memulai Langkah 1: Hyperparameter Tuning (Optuna) ---")
    best_params = run_hyperparameter_tuning()
    
    if not best_params:
        logging.critical("!!! GAGAL: Hyperparameter tuning tidak menghasilkan parameter. !!!")
        logging.critical("Pipeline tidak dapat dilanjutkan.")
        return
    
    logging.info("--- Selesai: Hyperparameter Tuning ---")
    logging.info(f"Parameter terbaik yang ditemukan: {best_params}")

    # Menyimpan hyperparameter terbaik ke file
    try:
        model_dir = config.get('model_dir', 'models')
        os.makedirs(model_dir, exist_ok=True)
        hyperparams_path = os.path.join(model_dir, 'best_hyperparameters.json')
        logging.info(f"Menyimpan hyperparameter terbaik ke {hyperparams_path}")
        with open(hyperparams_path, 'w') as f:
            json.dump(best_params, f, indent=4)
    except Exception as e:
        logging.error(f"Gagal menyimpan hyperparameter: {e}")

    # --- Langkah 2: Pelatihan Model Akhir ---
    logging.info("--- Memulai Langkah 2: Pelatihan Model Akhir ---")
    logging.info(f"Menggunakan {num_episodes_full} episode untuk pelatihan akhir.")
    
    try:
        # Memanggil fungsi train dengan parameter dari HPT
        # **best_params akan unpack dictionary menjadi keyword arguments
        train(
            lr=best_params['lr'],
            gamma=best_params['gamma'],
            hidden_size=best_params['hidden_size'],
            dropout_rate=best_params['dropout_rate'],
            batch_size=best_params['batch_size'],
            eps_decay=best_params['eps_decay'],
            num_episodes=num_episodes_full,
            save_model=True  # Pastikan model terbaik disimpan
        )
        logging.info("--- Selesai: Pelatihan Model Akhir ---")
    except Exception as e:
        logging.critical(f"!!! GAGAL: Pelatihan model akhir gagal dengan error: {e} !!!")
        return

    logging.info(">>> Pipeline Pelatihan Otomatis Berhasil Diselesaikan! <<<")

if __name__ == '__main__':
    main()