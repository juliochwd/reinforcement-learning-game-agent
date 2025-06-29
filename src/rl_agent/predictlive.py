import torch
import time
import pandas as pd
import yaml
import os
import logging

# --- Pengaturan Path untuk Utilitas ---
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from features.feature_engineering import create_features
from rl_agent.environment import TradingEnv

def load_config():
    """Memuat konfigurasi dari config.yaml."""
    config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config.yaml')
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config

def load_model_robust(model_path, device):
    """
    Memuat model secara kuat dengan terlebih dahulu membaca parameter arsitekturnya.
    """
    from rl_agent.model import GRU_DQN # Impor lambat

    if not os.path.exists(model_path):
        logging.error(f"File model tidak ditemukan di '{model_path}'.")
        return None

    try:
        checkpoint = torch.load(model_path, map_location=device, weights_only=False)
        architecture_params = checkpoint['architecture_params']
        
        model = GRU_DQN(**architecture_params)
        model.load_state_dict(checkpoint['model_state_dict'])
        model.to(device)
        model.eval()
        
        logging.info(f"Berhasil memuat model dari '{model_path}' dengan parameter: {architecture_params}")
        return model
    except Exception as e:
        logging.error(f"Gagal memuat model dari '{model_path}'. Kesalahan: {e}")
        return None

def predict_live():
    """Menjalankan agen yang terlatih dalam loop prediksi langsung."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    config = load_config()
    config_dir = os.path.dirname(os.path.join(os.path.dirname(__file__), '..', '..', 'config.yaml'))
    
    # Atur path absolut
    data_path = os.path.join(config_dir, config['data_path'])
    model_dir = os.path.join(config_dir, config['model_dir'])
    model_path = os.path.join(model_dir, config['best_model_name'])

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
            state_tensor = torch.tensor(state, dtype=torch.float32, device=device).unsqueeze(0)
            with torch.no_grad():
                action = policy_net(state_tensor).max(1)[1].item()

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