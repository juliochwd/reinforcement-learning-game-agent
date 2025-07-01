# ==============================================================================
#                           MODUL UTILITAS MODEL
# ==============================================================================
#  Berisi fungsi-fungsi bantuan untuk tugas-tugas terkait model RL, seperti
#  memuat konfigurasi, membuat environment, dan memuat model yang sudah ada.
# ==============================================================================

import os
import yaml
import logging
import torch
from rl_agent.model import ActorCriticSAC_GRU
from rl_agent.environment import TradingEnv

def load_config():
    """
    Memuat konfigurasi dari file config.yaml di root direktori proyek.
    """
    # Berasumsi skrip dipanggil dari root atau memiliki struktur yang dapat diprediksi
    config_path = 'config.yaml'
    if not os.path.exists(config_path):
        # Fallback jika dijalankan dari dalam direktori src
        config_path = os.path.join('..', '..', 'config.yaml')
        if not os.path.exists(config_path):
            raise FileNotFoundError("config.yaml tidak ditemukan di root proyek.")
            
    with open(config_path, 'r', encoding="utf-8") as f:
        return yaml.safe_load(f)

def load_model_robust(model_path, device):
    """
    Memuat model secara robust dengan membaca parameter arsitekturnya terlebih dahulu.
    
    Args:
        model_path (str): Path ke file model yang disimpan (.pth).
        device (torch.device): Device untuk memuat model (misalnya, 'cpu' atau 'cuda').

    Returns:
        torch.nn.Module or None: Model yang dimuat atau None jika gagal.
    """
    if not os.path.exists(model_path):
        logging.error(f"File model tidak ditemukan di '{model_path}'.")
        return None

    try:
        checkpoint = torch.load(model_path, map_location=device, weights_only=False)
        architecture_params = checkpoint['architecture_params']
        
        model = ActorCriticSAC_GRU(**architecture_params)
        model.load_state_dict(checkpoint['model_state_dict'])
        model.to(device)
        model.eval()
        
        logging.info(f"Berhasil memuat model dari '{model_path}' dengan params: {architecture_params}")
        return model
    except FileNotFoundError:
        logging.error(f"File model tidak ditemukan di '{model_path}'.")
        return None
    except KeyError as e:
        logging.error(f"Kunci yang hilang dalam checkpoint model: {e}. File mungkin korup atau dari versi yang berbeda.")
        return None
    except Exception as e:
        logging.error(f"Gagal memuat model dari '{model_path}'. Error: {e}", exc_info=True)
        return None

def create_environment(features_df, targets_df, config):
    """
    Membuat dan mengembalikan instance TradingEnv berdasarkan konfigurasi.

    Args:
        features_df (pd.DataFrame): DataFrame fitur.
        targets_df (pd.DataFrame): DataFrame target.
        config (dict): Kamus konfigurasi yang dimuat.

    Returns:
        TradingEnv: Instance dari environment perdagangan.
    """
    env_params = {
        'window_size': config['window_size'],
        'bet_percentages': config['bet_percentages'],
        'payout_ratio': config['payout_ratio'],
        'transaction_cost': config['transaction_cost']
    }
    return TradingEnv(features_df=features_df, targets_df=targets_df, **env_params)
