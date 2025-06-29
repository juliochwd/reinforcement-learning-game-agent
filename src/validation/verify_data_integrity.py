import pandas as pd
import numpy as np
import os
import sys
import logging

# --- Pengaturan Path ---
from ..features.feature_engineering import create_features

def verify_no_future_leakage(features_df, raw_df):
    """
    Secara matematis memverifikasi bahwa tidak ada data masa depan yang bocor ke dalam fitur.
    """
    logging.info("Memulai verifikasi integritas data untuk kebocoran masa depan...")
    
    # Pilih 50 indeks acak dari dataframe fitur untuk diuji
    # Ini memberikan cakupan yang baik tanpa memeriksa setiap baris
    if len(features_df) > 50:
        test_indices = np.random.choice(features_df.index, size=50, replace=False)
    else:
        test_indices = features_df.index
        
    total_verified = 0
    total_failed = 0

    for idx in test_indices:
        # Dapatkan satu baris fitur yang dihasilkan
        feature_vector_to_test = features_df.loc[idx]
        
        # Temukan 'Period' yang sesuai dari data mentah
        # Kita perlu menggeser indeks karena create_features menjatuhkan baris NaN di awal
        raw_data_end_index = idx + (len(raw_df) - len(features_df))
        
        # Ambil SEMUA data mentah yang seharusnya tersedia untuk menghasilkan vektor fitur ini.
        # Untuk langkah waktu t, kita hanya boleh menggunakan data mentah dari t-1 dan sebelumnya.
        # .iloc adalah eksklusif pada akhir, jadi kita perlu +1 untuk menyertakan baris saat ini.
        available_raw_data = raw_df.iloc[:raw_data_end_index + 1].copy()
        
        # Hasilkan ulang fitur HANYA menggunakan data yang tersedia secara historis
        recreated_features, _ = create_features(available_raw_data)
        
        if recreated_features.empty:
            logging.error(f"Verifikasi GAGAL di indeks {idx}. Tidak dapat mereproduksi fitur.")
            total_failed += 1
            continue
            
        # Dapatkan vektor fitur yang direproduksi terakhir (yang seharusnya cocok)
        recreated_vector = recreated_features.iloc[-1]
        
        # Bandingkan vektor asli dengan yang direproduksi
        if not np.allclose(feature_vector_to_test.values, recreated_vector.values, equal_nan=True):
            logging.error(f"Verifikasi GAGAL di indeks {idx}!")
            logging.error(f"--> Vektor Asli: {feature_vector_to_test.to_dict()}")
            logging.error(f"--> Vektor yang Direproduksi: {recreated_vector.to_dict()}")
            total_failed += 1
        else:
            total_verified += 1

    logging.info(f"--- Hasil Verifikasi Integritas Data ---")
    if total_failed == 0:
        logging.info(f"SUKSES: {total_verified}/{len(test_indices)} sampel yang diuji berhasil diverifikasi. Tidak ada kebocoran data yang terdeteksi.")
    else:
        logging.error(f"GAGAL: {total_failed}/{len(test_indices)} sampel yang diuji gagal verifikasi. KEBOCORAN DATA TERDETEKSI.")
        
    return total_failed == 0

def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    data_path = os.path.join(project_root, 'data', 'databaru_from_api.csv')
    
    if not os.path.exists(data_path):
        logging.error(f"File data tidak ditemukan di: {data_path}")
        return

    logging.info("Memuat data mentah untuk verifikasi...")
    raw_df = pd.read_csv(data_path)
    
    logging.info("Membuat fitur dari seluruh set data untuk mendapatkan vektor referensi...")
    features_df, _ = create_features(raw_df.copy())
    
    verify_no_future_leakage(features_df, raw_df)

if __name__ == "__main__":
    main()