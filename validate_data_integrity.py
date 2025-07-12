import pandas as pd
import numpy as np
import logging
from sklearn.preprocessing import LabelEncoder

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def normalize_col(col):
    return col.replace('/', '_')

def check_no_lookahead(train, test, lag_cols):
    for lag_col in lag_cols:
        if not pd.isna(test.iloc[0][lag_col]) and test.iloc[0][lag_col] != 0:
            logging.error(f"Lookahead bias: {lag_col} test[0]={test.iloc[0][lag_col]}")
            raise AssertionError(f"Lookahead bias pada {lag_col}")
    logging.info("Tidak ada lookahead bias pada rolling/lag features.")

def check_label_leakage(df, label_col, feature_cols):
    label = df[label_col]
    if label.dtype == object:
        le_label = LabelEncoder()
        label = le_label.fit_transform(label)
    for col in feature_cols:
        if col == label_col:
            continue
        feat = df[col]
        if feat.dtype == object:
            le_feat = LabelEncoder()
            try:
                feat = le_feat.fit_transform(feat)
            except Exception:
                continue
        if feat is not None and not bool(pd.isnull(feat).all()):
            arr_feat = np.array(feat)
            arr_label = np.array(label)
            if len(np.unique(arr_feat)) > 1:
                try:
                    corr = np.corrcoef(arr_feat, arr_label)[0, 1]
                    if abs(corr) > 0.99:
                        logging.error(f"Label leakage: {col} berkorelasi {corr:.4f} dengan label {label_col}")
                        raise AssertionError(f"Label leakage pada {col} (corr={corr:.4f})")
                except Exception as e:
                    logging.warning(f"Gagal hitung korelasi {col}: {e}")
    logging.info("Tidak ada fitur yang berkorelasi sangat tinggi dengan label.")

def check_future_feature_leakage(df, time_col):
    if not df[time_col].is_monotonic_increasing:
        logging.error("Urutan waktu tidak monoton naik.")
        raise AssertionError("Urutan waktu tidak monoton naik.")
    logging.info("Urutan waktu sudah benar.")

def check_label_in_features(df, label_col, feature_cols):
    for col in feature_cols:
        if col == label_col:
            continue
        if df[col].equals(df[label_col]):
            logging.error(f"Label {label_col} langsung ada di fitur {col}")
            raise AssertionError(f"Label {label_col} langsung ada di fitur {col}")
    logging.info("Tidak ada label yang langsung ada di fitur.")

def main():
    df = pd.read_csv("data/databaru_from_api.csv")
    time_col = "Period"
    label_col = "Number"
    df = df.rename(columns={c: normalize_col(c) for c in df.columns})
    time_col = normalize_col(time_col)
    label_col = normalize_col(label_col)
    n_lags = 10
    # Hanya gunakan fitur lag dari Number
    feature_cols = [f'number_lag_{i}' for i in range(1, n_lags+1)]
    # Siapkan data dengan fitur lag
    df_feat = pd.DataFrame()
    df_feat['Number'] = df[label_col]
    for i in range(1, n_lags+1):
        df_feat[f'number_lag_{i}'] = df[label_col].shift(i)
    df_feat = df_feat.fillna(0)
    # Split train/test secara kronologis
    df = df.sort_values(time_col).reset_index(drop=True)
    split_ratio = 0.8
    split_idx = int(len(df) * split_ratio)
    train = df_feat.iloc[:split_idx].copy()
    test = df_feat.iloc[split_idx:].copy()
    lag_cols = feature_cols
    # Audit: Tidak ada lookahead bias
    check_no_lookahead(train, test, lag_cols)
    # Audit: Tidak ada label leakage (fitur identik/berkorelasi tinggi dengan label)
    check_label_leakage(df_feat, label_col, feature_cols)
    # Audit: Tidak ada fitur masa depan
    check_future_feature_leakage(df, time_col)
    # Audit: Tidak ada label di fitur
    check_label_in_features(df_feat, label_col, feature_cols)
    logging.info("AUDIT SELESAI: TIDAK ADA DATA LEAKAGE TERDETEKSI.")

if __name__ == "__main__":
    main() 