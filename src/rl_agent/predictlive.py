import time
import pandas as pd
import os
import logging

# --- Pengaturan Path untuk Utilitas ---
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from src.utils.model_helpers import load_config
from src.rl_agent.decision_maker import DecisionMaker

def predict_live():
    """Menjalankan agen yang terlatih dalam loop prediksi langsung menggunakan DecisionMaker."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    try:
        config = load_config()
        decision_maker = DecisionMaker(config)
    except FileNotFoundError as e:
        logging.error(f"Gagal menginisialisasi DecisionMaker. Pastikan model telah dilatih. Kesalahan: {e}")
        return

    # Untuk simulasi, kita perlu data historis. Kita akan memuatnya sekali.
    try:
        data_path = config['project_setup']['data_path']
        full_df = pd.read_csv(data_path)
        logging.info(f"Data historis dimuat dari {data_path} untuk simulasi.")
    except FileNotFoundError:
        logging.error(f"File data tidak ditemukan di '{data_path}'.")
        return

    window_size = config['environment']['window_size']
    action_labels = ['Tahan', 'Taruhan Kecil', 'Taruhan Besar']

    logging.info("--- Memulai Simulasi Prediksi Langsung ---")
    try:
        # Loop melalui data historis seolah-olah itu adalah data langsung
        for i in range(window_size, len(full_df)):
            # Dapatkan data historis hingga saat ini
            historical_data_window = full_df.iloc[i - window_size : i]
            
            # Dapatkan keputusan dari DecisionMaker
            action = decision_maker.get_decision(historical_data_window)
            
            # Dapatkan hasil aktual dari langkah berikutnya untuk perbandingan
            actual_outcome_numeric = full_df.iloc[i]['is_big']
            actual_outcome_str = "Besar" if actual_outcome_numeric == 1 else "Kecil"
            
            logging.info(f"Langkah: {i} | Aksi Prediksi: {action_labels[action]:<15} | Hasil Aktual: {actual_outcome_str}")
            
            time.sleep(1) # Jeda untuk mensimulasikan kedatangan data secara real-time

    except KeyboardInterrupt:
        logging.info("--- Prediksi Langsung Dihentikan oleh Pengguna ---")
    except Exception as e:
        logging.error(f"Terjadi kesalahan saat loop prediksi: {e}", exc_info=True)

if __name__ == '__main__':
    predict_live()
