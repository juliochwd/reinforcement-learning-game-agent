import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
try:
    import pywt
except ImportError:
    raise ImportError('PyWavelets (pywt) tidak ditemukan. Pastikan sudah install dengan pip install PyWavelets dan environment Python yang digunakan sudah benar.')
from scipy.stats import entropy, mode

class FeatureEngineer:
    """
    Feature engineering untuk data game dengan berbagai fitur statistik dan sinyal
    """
    
    def __init__(self, window_sizes: List[int] = [10, 30, 50]):
        self.window_sizes = window_sizes
        self.number_mapping = {i: i for i in range(10)}
        self.big_small_mapping = {'Big': 1, 'Small': 0}
        self.color_mapping = {'red': 0, 'green': 1, 'violet': 2}
        
    def encode_categorical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Encode fitur kategorikal"""
        df_encoded = df.copy()
        # Encode Big/Small
        df_encoded['big_small_encoded'] = df_encoded['Big/Small'].apply(lambda x: self.big_small_mapping.get(x, 0))
        # Encode Color (handle multiple colors)
        def encode_color(color_str: str) -> int:
            if pd.isna(color_str):
                return 0
            colors = color_str.split(',')
            # Take the first color if multiple
            return self.color_mapping.get(colors[0].strip(), 0)
        df_encoded['color_encoded'] = df_encoded['Color'].apply(encode_color)
        return df_encoded
    
    def calculate_moving_averages(self, df: pd.DataFrame) -> pd.DataFrame:
        df_ma = df.copy()
        for window in self.window_sizes:
            df_ma[f'number_ma_{window}'] = df_ma['Number'].rolling(window=window).mean()
            df_ma[f'big_small_ma_{window}'] = df_ma['big_small_encoded'].rolling(window=window).mean()
            df_ma[f'color_ma_{window}'] = df_ma['color_encoded'].rolling(window=window).mean()
            df_ma[f'number_std_{window}'] = df_ma['Number'].rolling(window=window).std()
        return df_ma
    
    def calculate_streak_analysis(self, df: pd.DataFrame) -> pd.DataFrame:
        df_streak = df.copy()
        df_streak['big_streak'] = (df_streak['big_small_encoded'] == 1).astype(int).groupby(
            (df_streak['big_small_encoded'] != 1).astype(int).cumsum()
        ).cumsum()
        df_streak['small_streak'] = (df_streak['big_small_encoded'] == 0).astype(int).groupby(
            (df_streak['big_small_encoded'] != 0).astype(int).cumsum()
        ).cumsum()
        for color in ['red', 'green', 'violet']:
            color_encoded = self.color_mapping[color]
            df_streak[f'{color}_streak'] = (df_streak['color_encoded'] == color_encoded).astype(int).groupby(
                (df_streak['color_encoded'] != color_encoded).astype(int).cumsum()
            ).cumsum()
        for num in range(10):
            df_streak[f'number_{num}_streak'] = (df_streak['Number'] == num).astype(int).groupby(
                (df_streak['Number'] != num).astype(int).cumsum()
            ).cumsum()
        return df_streak
    
    def calculate_missing_streak(self, df: pd.DataFrame) -> pd.DataFrame:
        df_missing = df.copy()
        for category in ['big', 'small']:
            encoded_val = 1 if category == 'big' else 0
            df_missing[f'{category}_missing'] = (
                (df_missing['big_small_encoded'] != encoded_val).astype(int).groupby(
                    (df_missing['big_small_encoded'] == encoded_val).astype(int).cumsum()
                ).cumsum()
            )
        for color in ['red', 'green', 'violet']:
            color_encoded = self.color_mapping[color]
            df_missing[f'{color}_missing'] = (
                (df_missing['color_encoded'] != color_encoded).astype(int).groupby(
                    (df_missing['color_encoded'] == color_encoded).astype(int).cumsum()
                ).cumsum()
            )
        for num in range(10):
            df_missing[f'number_{num}_missing'] = (
                (df_missing['Number'] != num).astype(int).groupby(
                    (df_missing['Number'] == num).astype(int).cumsum()
                ).cumsum()
            )
        return df_missing
    
    def calculate_fourier_features(self, df: pd.DataFrame, n_components: int = 5) -> pd.DataFrame:
        df_fourier = df.copy()
        number_series = df_fourier['Number'].values.astype(float)
        fft_result = np.fft.fft(number_series)
        freqs = np.fft.fftfreq(len(number_series))
        for i in range(min(n_components, len(freqs)//2)):
            val = np.asarray(fft_result[i]).item()
            df_fourier[f'fourier_number_magnitude_{i}'] = float(np.abs(val))
            df_fourier[f'fourier_number_phase_{i}'] = float(np.angle(val))
        return df_fourier
    
    def calculate_wavelet_features(self, df: pd.DataFrame, wavelet: str = 'db4', levels: int = 3) -> pd.DataFrame:
        df_wavelet = df.copy()
        number_series = df_wavelet['Number'].values.astype(float)
        coeffs = pywt.wavedec(number_series, wavelet, level=levels)
        for i, coeff in enumerate(coeffs):
            coeff = np.asarray(coeff)
            df_wavelet[f'wavelet_number_level_{i}_mean'] = float(np.mean(coeff))
            df_wavelet[f'wavelet_number_level_{i}_std'] = float(np.std(coeff))
        return df_wavelet
    
    def calculate_correlation_features(self, df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
        df_corr = df.copy()
        df_corr['number_big_small_corr'] = df_corr['Number'].rolling(window=window).corr(df_corr['big_small_encoded'])
        return df_corr
    
    def calculate_volatility_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df_vol = df.copy()
        df_vol['number_change'] = df_vol['Number'].diff()
        df_vol['number_change_abs'] = df_vol['number_change'].abs()
        for window in [5, 10, 20]:
            df_vol[f'number_volatility_{window}'] = df_vol['number_change'].rolling(window=window).std()
        return df_vol
    
    def create_historical_features(self, df: pd.DataFrame, lookback: int = 10) -> pd.DataFrame:
        df_hist = df.copy()
        for i in range(1, lookback + 1):
            df_hist[f'number_lag_{i}'] = df_hist['Number'].shift(i)
            df_hist[f'big_small_lag_{i}'] = df_hist['big_small_encoded'].shift(i)
            df_hist[f'color_lag_{i}'] = df_hist['color_encoded'].shift(i)
        return df_hist
    
    def remove_highly_correlated_features(self, df: pd.DataFrame, threshold: float = 0.65) -> pd.DataFrame:
        """Remove features with high correlation to reduce redundancy. Hanya kolom numerik yang dihitung korelasinya."""
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        for col in ['Big/Small', 'Color', 'Period']:
            if col in numeric_cols:
                numeric_cols.remove(col)
        if len(numeric_cols) < 2:
            return df
        # Pastikan selalu DataFrame
        corr_matrix = df.loc[:, numeric_cols].corr().abs()
        upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
        to_drop = [column for column in upper.columns if any(upper[column] > threshold)]
        return df.drop(columns=to_drop)

    def engineer_all_features(self, df: pd.DataFrame) -> pd.DataFrame:
        print("Memulai feature engineering...")
        df_encoded = self.encode_categorical_features(df)
        print("✓ Categorical encoding selesai")
        df_ma = self.calculate_moving_averages(df_encoded)
        print("✓ Moving averages selesai")
        df_streak = self.calculate_streak_analysis(df_ma)
        print("✓ Streak analysis selesai")
        df_missing = self.calculate_missing_streak(df_streak)
        print("✓ Missing streak selesai")
        df_fourier = self.calculate_fourier_features(df_missing)
        print("✓ Fourier features selesai")
        df_wavelet = self.calculate_wavelet_features(df_fourier)
        print("✓ Wavelet features selesai")
        df_corr = self.calculate_correlation_features(df_wavelet)
        print("✓ Correlation features selesai")
        df_vol = self.calculate_volatility_features(df_corr)
        print("✓ Volatility features selesai")
        df_final = self.create_historical_features(df_vol)
        print("✓ Historical features selesai")
        df_final = df_final.fillna(method='bfill').fillna(0)
        df_final = df_final.fillna(0)
        # Hapus fitur yang sangat berkorelasi (>0.65)
        df_final = self.remove_highly_correlated_features(df_final, threshold=0.65)
        print(f"Feature engineering selesai. Total fitur setelah reduksi korelasi: {len(df_final.columns)}")
        return df_final 

def engineer_features_number_only(df: pd.DataFrame, n_lags: int = 10) -> pd.DataFrame:
    """
    Feature engineering anti-leakage untuk prediksi Number:
    - Hanya gunakan lag dari Number (tanpa Premium, Big/Small, Color, dsb)
    - Semua lag hanya gunakan data masa lalu (n-1)
    """
    df_feat = pd.DataFrame()
    df_feat['Number'] = df['Number']
    for i in range(1, n_lags + 1):
        df_feat[f'number_lag_{i}'] = df['Number'].shift(i)
    df_feat = df_feat.fillna(0)
    return df_feat

def engineer_features_number_advanced(df: pd.DataFrame, n_lags: int = 10, window_sizes = [5, 10, 20]) -> pd.DataFrame:
    """
    Feature engineering anti-leakage untuk prediksi Number:
    - Lag Number (n_lags)
    - Rolling mean, std, min, max, mode, entropy dari Number (window_sizes)
    Semua fitur hanya gunakan data masa lalu (n-1, n-2, ...)
    """
    df_feat = pd.DataFrame()
    df_feat['Number'] = df['Number']
    # Lag features
    for i in range(1, n_lags + 1):
        df_feat[f'number_lag_{i}'] = df['Number'].shift(i)
    # Rolling window features
    for w in window_sizes:
        df_feat[f'number_roll_mean_{w}'] = df['Number'].shift(1).rolling(window=w).mean()
        df_feat[f'number_roll_std_{w}'] = df['Number'].shift(1).rolling(window=w).std()
        df_feat[f'number_roll_min_{w}'] = df['Number'].shift(1).rolling(window=w).min()
        df_feat[f'number_roll_max_{w}'] = df['Number'].shift(1).rolling(window=w).max()
        # Mode
        df_feat[f'number_roll_mode_{w}'] = df['Number'].shift(1).rolling(window=w).apply(lambda x: mode(x, keepdims=False)[0] if len(x) > 0 else 0, raw=False)
        # Entropy
        def rolling_entropy(x):
            counts = np.bincount(x.astype(int))
            probs = counts / counts.sum() if counts.sum() > 0 else np.zeros_like(counts)
            return entropy(probs, base=2) if probs.sum() > 0 else 0
        df_feat[f'number_roll_entropy_{w}'] = df['Number'].shift(1).rolling(window=w).apply(rolling_entropy, raw=False)
    df_feat = df_feat.fillna(0)
    return df_feat

def engineer_features_number_full_anti_leakage(df: pd.DataFrame, n_lags: int = 10, window_sizes = [10, 30, 50]) -> pd.DataFrame:
    """
    Fitur anti-leakage untuk prediksi Number:
    - Lag Number
    - Rolling mean, std, min, max, mode, entropy dari Number
    - Rolling Fourier/Wavelet dari Number (window ke belakang, shift(1))
    Semua fitur hanya dari masa lalu, tanpa leakage.
    """
    df_feat = pd.DataFrame()
    df_feat['Number'] = df['Number']
    # Lag features
    for i in range(1, n_lags + 1):
        df_feat[f'number_lag_{i}'] = df['Number'].shift(i)
    # Rolling window features
    for w in window_sizes:
        df_feat[f'number_roll_mean_{w}'] = df['Number'].shift(1).rolling(window=w).mean()
        df_feat[f'number_roll_std_{w}'] = df['Number'].shift(1).rolling(window=w).std()
        df_feat[f'number_roll_min_{w}'] = df['Number'].shift(1).rolling(window=w).min()
        df_feat[f'number_roll_max_{w}'] = df['Number'].shift(1).rolling(window=w).max()
        # Mode
        df_feat[f'number_roll_mode_{w}'] = df['Number'].shift(1).rolling(window=w).apply(lambda x: mode(x, keepdims=False)[0] if len(x) > 0 else 0, raw=False)
        # Entropy
        def rolling_entropy(x):
            counts = np.bincount(x.astype(int))
            probs = counts / counts.sum() if counts.sum() > 0 else np.zeros_like(counts)
            return entropy(probs, base=2) if probs.sum() > 0 else 0
        df_feat[f'number_roll_entropy_{w}'] = df['Number'].shift(1).rolling(window=w).apply(rolling_entropy, raw=False)
        # Rolling Fourier (magnitude & phase)
        def rolling_fft_mag(x):
            arr = np.array(list(x), dtype=float).flatten()
            if len(arr) < 2:
                return 0
            vals = np.abs(np.fft.fft(arr))
            return vals[1] if len(vals) > 1 else 0
        def rolling_fft_phase(x):
            arr = np.array(list(x), dtype=float).flatten()
            if len(arr) < 2:
                return 0
            vals = np.angle(np.fft.fft(arr))
            return vals[1] if len(vals) > 1 else 0
        df_feat[f'number_roll_fft_mag_{w}'] = df['Number'].shift(1).rolling(window=w).apply(rolling_fft_mag, raw=False)
        df_feat[f'number_roll_fft_phase_{w}'] = df['Number'].shift(1).rolling(window=w).apply(rolling_fft_phase, raw=False)
    df_feat = df_feat.fillna(0)
    return df_feat

# Agar bisa diimport dari modul lain
__all__ = ['FeatureEngineer', 'engineer_features_number_only', 'engineer_features_number_advanced', 'engineer_features_number_full_anti_leakage'] 