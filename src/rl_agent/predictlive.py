import torch
import time
import pandas as pd
import yaml
import os
import logging

# --- Pengaturan Path untuk Utilitas ---
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from src.features.feature_engineering import create_features
from src.rl_agent.environment import TradingEnv
from src.utils.model_helpers import load_config, load_model_robust

def predict_live():
    """Menjalankan agen yang terlatih dalam loop prediksi langsung."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    config = load_config()
    config_dir = os.path.dirname(os.path.join(os.path.dirname(__file__), '..', '..', 'config.yaml'))
    
    # Atur path absolut
    data_path = os.path.join(config_dir, config['data_path'])
    model_dir = os.path.join(config_dir, config['model_dir'])
    model_path = os.path.join(model_dir, "sac_model.pth") # Use the new model name

    # 1. Muat dan proses data
    try:
        raw_df = pd.read_csv(data_path)
        logging.info(f"Data mentah dimuat dari {data_path}")
    except FileNotFoundError:
        logging.error(f"File data tidak ditemukan di '{data_path}'. Harap jalankan scraper terlebih dahulu.")
        return
        
    features_df, targets_df = create_features(raw_df)
    logging.info("Rekayasa fitur diterapkan pada data langsung.")

    # 2. Muat model
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    policy_net = load_model_robust(model_path, device)
    if policy_net is None:
        return

    # 3. Siapkan lingkungan
    bet_percentages = [0.01, 0.025, 0.05]  # Sesuaikan dengan parameter pelatihan baru
    env = TradingEnv(
        features_df=features_df,
        targets_df=targets_df,
        window_size=config['window_size'],
        bet_percentages=bet_percentages
    )
    state, _ = env.reset()
    
    action_labels = ['Tahan'] + \
                    [f'Kecil({p*100:.1f}%)' for p in bet_percentages] + \
                    [f'Besar({p*100:.1f}%)' for p in bet_percentages]

    logging.info("--- Memulai Prediksi Langsung ---")
    try:
        while True:
            with torch.no_grad():
                # Use the correct method for the SAC model
                action = policy_net.get_action(state, device)

            actual_outcome_numeric = env._get_actual_outcome()
            actual_outcome_str = "Besar" if actual_outcome_numeric == 1 else "Kecil"
            
            logging.info(f"Langkah: {env.current_step} | Aksi Prediksi: {action_labels[action]:<10} | Hasil Aktual: {actual_outcome_str}")

            state, _, terminated, truncated, _ = env.step(action)
            
            if terminated or truncated:
                logging.info("\n--- Akhir data tercapai. Mengatur ulang. ---\n")
                state, _ = env.reset()
            
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("--- Prediksi Langsung Dihentikan oleh Pengguna ---")

if __name__ == '__main__':
    predict_live()
