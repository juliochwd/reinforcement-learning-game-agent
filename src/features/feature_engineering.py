import pandas as pd
import numpy as np

def create_features(df):
    """
    Menciptakan fitur dan target dari data mentah, mengembalikannya sebagai dua dataframe terpisah
    untuk mencegah kebocoran data secara struktural.
    Versi ini disederhanakan untuk hanya membuat fitur yang paling penting.

    Returns:
        tuple[pd.DataFrame, pd.DataFrame]: Sebuah tuple berisi (features_df, targets_df).
            - features_df: Berisi fitur-fitur yang aman (shifted/rolled) untuk input agen.
            - targets_df: Berisi data hasil/target untuk perhitungan reward.
    """
    df = df.copy()
    df = df.sort_values(by='Period').reset_index(drop=True)

    # --- Buat Kolom Dasar (termasuk target) ---
    df['last_digit'] = df['Premium'].astype(int) % 10
    df['is_big'] = (df['last_digit'] >= 5).astype(int)

    # --- Buat Fitur-Fitur Aman (Hanya menggunakan data yang digeser/shifted) ---
    features = pd.DataFrame(index=df.index)

    # --- Fitur Kontekstual Harian (Mean Reversion) ---
    period_str = df['Period'].astype(str)
    df['day_identifier'] = period_str.str[:-4]
    draw_of_the_day = period_str.str[-4:].astype(int)
    
    df['is_small'] = (df['is_big'] == 0).astype(int)
    df['shifted_is_big'] = df['is_big'].shift(1)
    df['shifted_is_small'] = df['is_small'].shift(1)
    
    daily_big_counts = df.groupby('day_identifier')['shifted_is_big'].cumsum()
    daily_small_counts = df.groupby('day_identifier')['shifted_is_small'].cumsum()
    daily_big_small_imbalance = daily_small_counts - daily_big_counts
    
    features['daily_imbalance_norm'] = daily_big_small_imbalance / (draw_of_the_day + 1e-6)

    # --- Fitur Rolling Window (Hanya Mean) ---
    for window in [3, 5, 10, 30]:
        shifted_data = df['last_digit'].shift(1)
        features[f'rolling_mean_{window}'] = shifted_data.rolling(window=window).mean()

    # --- Fitur Frekuensi & Momentum (Ratio) ---
    for window in [3, 10, 30]:
        shifted_is_big_for_ratio = df['is_big'].shift(1)
        features[f'big_small_ratio_{window}'] = shifted_is_big_for_ratio.rolling(window=window).mean()

    # --- Pisahkan Target dan Gabungkan untuk pembersihan NaN ---
    targets_df = df[['Period', 'Premium', 'is_big']].copy()
    
    full_processed_df = pd.concat([features, targets_df], axis=1)
    
    # Hapus baris yang memiliki nilai NaN di mana saja
    full_processed_df.dropna(inplace=True)
    full_processed_df.reset_index(drop=True, inplace=True)

    # Pisahkan kembali menjadi dataframe fitur dan target yang bersih
    final_features_df = full_processed_df[features.columns]
    final_targets_df = full_processed_df[targets_df.columns]

    return final_features_df, final_targets_df