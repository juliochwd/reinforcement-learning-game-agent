import pandas as pd
import os
import logging
import joblib
from sklearn.preprocessing import MinMaxScaler
# Adjusted import path to be relative to the src directory
from src.features.feature_engineering import create_features

def prepare_data_splits(data_path, scaler_path, train_ratio=0.7, val_ratio=0.15):
    """
    Memuat data mentah, memisahkan fitur dari target, lalu membagi keduanya secara kronologis
    dan menerapkan penskalaan fitur. Ini secara struktural mencegah kebocoran data.

    Args:
        data_path (str): Path ke data CSV mentah.
        scaler_path (str): Path untuk menyimpan scaler yang sudah di-fit.
        train_ratio (float): Proporsi data untuk digunakan sebagai training.
        val_ratio (float): Proporsi data untuk digunakan sebagai validasi.

    Returns:
        tuple: Sebuah tuple yang berisi (train_X, train_y, val_X, val_y, test_X, test_y).
    """
    # 1. Muat data mentah
    # Pemeriksaan os.path.exists dihapus untuk mendukung path GCS (gs://)
    # pandas dengan gcsfs akan menangani error jika file tidak ditemukan.
    try:
        raw_df = pd.read_csv(data_path)
    except FileNotFoundError:
        logging.error(f"File data tidak ditemukan di: {data_path}")
        raise
    
    # 2. Buat fitur dan target secara terpisah
    logging.info("Memisahkan fitur dan target dari data mentah...")
    features_df, targets_df = create_features(raw_df)
    logging.info(f"Pemisahan selesai. {len(features_df)} baris data yang dapat digunakan.")
    
    # 3. Bagi kedua set data secara sinkron (secara kronologis)
    train_end_idx = int(len(features_df) * train_ratio)
    val_end_idx = train_end_idx + int(len(features_df) * val_ratio)
    
    train_X = features_df.iloc[:train_end_idx]
    val_X = features_df.iloc[train_end_idx:val_end_idx]
    test_X = features_df.iloc[val_end_idx:]
    
    train_y = targets_df.iloc[:train_end_idx]
    val_y = targets_df.iloc[train_end_idx:val_end_idx]
    test_y = targets_df.iloc[val_end_idx:]
    
    logging.info(f"Pemisahan data: {len(train_X)} training, {len(val_X)} validasi, {len(test_X)} sampel tes.")

    # --- PENERAPAN FEATURE SCALING ---
    # 4. Inisialisasi dan fit scaler HANYA pada data training untuk mencegah data leakage
    scaler = MinMaxScaler()
    logging.info("Fitting scaler HANYA pada data training...")
    scaler.fit(train_X)

    # 5. Simpan scaler yang sudah di-fit untuk digunakan oleh agen real-time
    scaler_save_path = scaler_path
    scaler_dir = os.path.dirname(scaler_save_path)
    if not os.path.exists(scaler_dir):
        os.makedirs(scaler_dir)
    joblib.dump(scaler, scaler_save_path)
    logging.info(f"Feature scaler yang sudah di-fit disimpan ke: {scaler_save_path}")

    # 6. Transform semua set data (train, val, test) menggunakan scaler yang sama
    logging.info("Mengaplikasikan scaler ke semua set data (train, val, test)...")
    train_X_scaled = pd.DataFrame(scaler.transform(train_X), columns=train_X.columns, index=train_X.index)
    val_X_scaled = pd.DataFrame(scaler.transform(val_X), columns=val_X.columns, index=val_X.index)
    test_X_scaled = pd.DataFrame(scaler.transform(test_X), columns=test_X.columns, index=test_X.index)
    
    logging.info("Feature scaling berhasil diterapkan.")
    
    return train_X_scaled, train_y, val_X_scaled, val_y, test_X_scaled, test_y
