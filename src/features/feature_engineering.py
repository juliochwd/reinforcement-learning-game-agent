import pandas as pd
import numpy as np

def create_features(df):
    """
    Menciptakan fitur dan target dari data mentah, mengembalikannya sebagai dua dataframe terpisah
    untuk mencegah kebocoran data secara struktural.

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
    features = pd.DataFrame(index=df.index) # Buat dataframe baru untuk fitur

    # --- Fitur Kontekstual Harian (Untuk Strategi Mean Reversion) ---
    # Fitur ini memberikan kesadaran pada agen tentang posisinya dalam siklus harian.
    period_str = df['Period'].astype(str)
    # Buat pengenal hari di DataFrame utama untuk digunakan dalam groupby
    df['day_identifier'] = period_str.str[:-4]
    features['draw_of_the_day'] = period_str.str[-4:].astype(int)
    
    # Hitung ketidakseimbangan Big/Small kumulatif untuk setiap hari
    # Ini adalah fitur kunci untuk mengeksploitasi celah 'mean reversion'
    df['is_small'] = (df['is_big'] == 0).astype(int)
    # Geser untuk mencegah kebocoran data (imbalance dihitung sebelum langkah saat ini)
    # Untuk menghindari KeyError yang tidak biasa dengan groupby, buat kolom sementara
    df['shifted_is_big'] = df['is_big'].shift(1)
    df['shifted_is_small'] = df['is_small'].shift(1)
    
    daily_big_counts = df.groupby('day_identifier')['shifted_is_big'].cumsum()
    daily_small_counts = df.groupby('day_identifier')['shifted_is_small'].cumsum()
    features['daily_big_small_imbalance'] = daily_small_counts - daily_big_counts

    # Hapus kolom sementara setelah digunakan
    df.drop(columns=['shifted_is_big', 'shifted_is_small'], inplace=True)
    
    # Normalisasi fitur harian agar lebih mudah dipelajari oleh model
    features['draw_of_the_day_norm'] = features['draw_of_the_day'] / 1440.0
    # Kita bisa menormalisasi imbalance dengan draw_of_the_day
    # Hindari pembagian dengan nol di awal
    features['daily_imbalance_norm'] = features['daily_big_small_imbalance'] / (features['draw_of_the_day'] + 1e-6)


    # Fitur Streak (Momentum Beruntun)
    # Gunakan Series yang baru dibuat untuk perhitungan streak
    shifted_is_big_for_streak = df['is_big'].shift(1)
    block = (shifted_is_big_for_streak != shifted_is_big_for_streak.shift(1)).cumsum()
    features['consecutive_count'] = df.groupby(block).cumcount() + 1

    # Fitur Ganjil/Genap
    features['is_last_digit_even'] = (df['last_digit'].shift(1) % 2 == 0).astype(int)

    # Fitur Lag (Melihat ke Belakang)
    for lag in [1, 2, 3, 5, 10]:
        features[f'lag_last_digit_{lag}'] = df['last_digit'].shift(lag)

    # Fitur Rolling Window (Agregasi Jendela Geser) - DIOPTIMALKAN
    shifted_data = df['last_digit'].shift(1)
    for window in [3, 5, 10, 30]:
        # Buat objek rolling HANYA SEKALI per jendela untuk efisiensi
        rolling_window = shifted_data.rolling(window=window)
        
        # Hitung semua agregasi dari objek yang sama untuk menghindari perhitungan ulang
        features[f'rolling_mean_{window}'] = rolling_window.mean()
        features[f'rolling_std_{window}'] = rolling_window.std()
        features[f'rolling_min_{window}'] = rolling_window.min()
        features[f'rolling_max_{window}'] = rolling_window.max()

    # Fitur Frekuensi & Momentum
    for window in [3, 10, 30]:
        shifted_is_big_for_ratio = df['is_big'].shift(1)
        features[f'big_small_ratio_{window}'] = shifted_is_big_for_ratio.rolling(window=window).mean()

    # --- Pisahkan Target dan Gabungkan ---
    targets_df = df[['Period', 'Premium', 'is_big']].copy()
    
    # Gabungkan fitur dengan target untuk pemfilteran NaN yang konsisten
    full_processed_df = pd.concat([features, targets_df], axis=1)
    
    # Hapus baris yang memiliki nilai NaN di mana saja (memastikan fitur dan target selaras)
    full_processed_df.dropna(inplace=True)
    full_processed_df.reset_index(drop=True, inplace=True)

    # Pisahkan kembali menjadi dataframe fitur dan target yang bersih
    # Hapus kolom identifier mentah karena tidak berguna untuk model
    # Hapus kolom identifier mentah karena tidak berguna untuk model
    # Juga hapus 'draw_of_the_day' yang tidak dinormalisasi
    final_features_df = full_processed_df[features.columns].drop(columns=['draw_of_the_day'])
    final_targets_df = full_processed_df[targets_df.columns]

    return final_features_df, final_targets_df
