import pandas as pd
import os

# Path yang benar ke file data, disesuaikan dengan struktur direktori
DATA_PATH = 'data/databaru_from_api.csv' 

print(f"Menganalisis file: {DATA_PATH}")

# Memastikan file ada sebelum melanjutkan
if not os.path.exists(DATA_PATH):
    print(f"[ERROR] File tidak ditemukan di path: {DATA_PATH}")
    exit()

df = pd.read_csv(DATA_PATH)

# Buat ulang kolom target dan fitur yang dicurigai
df['last_digit'] = df['Premium'].astype(int) % 10
df['is_big'] = (df['last_digit'] >= 5).astype(int)
print("\n--- Analisis Duplikasi Data ---")
duplicate_rows = df.duplicated().sum()
duplicate_periods = df.duplicated(subset=['Period']).sum()
print(f"Jumlah baris duplikat penuh: {duplicate_rows}")
print(f"Jumlah 'Period' yang terduplikasi: {duplicate_periods}")
if duplicate_periods > 0:
    print("[Warning] Ada duplikasi pada kolom 'Period'. Ini bisa menyebabkan masalah.")
else:
    print("[OK] Tidak ada duplikasi pada kolom 'Period'.")