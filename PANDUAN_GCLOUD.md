# Panduan Menjalankan Proyek di Google Cloud VM

Dokumen ini memberikan panduan lengkap untuk menyiapkan dan menjalankan alur kerja training dan hyperparameter tuning (HPT) di lingkungan Google Cloud VM menggunakan Docker.

## 1. Pendahuluan

Proyek ini dirancang untuk berjalan di dalam container Docker di sebuah VM Google Cloud. Pendekatan ini memastikan lingkungan yang konsisten dan dapat direproduksi, serta memanfaatkan akselerasi GPU untuk training. Semua dependensi dikelola di dalam image Docker, sehingga penyiapan di VM menjadi minimal.

## 2. Penyiapan Awal VM

Ikuti langkah-langkah ini untuk menyiapkan lingkungan VM Anda.

### a. Buat VM
Mulai dengan instance "Deep Learning on Linux" di Google Cloud. Pastikan konfigurasi berikut:
- **Sistem Operasi**: Debian 11
- **Tipe GPU**: NVIDIA T4 atau yang lebih baru
- **Versi CUDA**: 12.4 (biasanya sudah terinstal pada image Deep Learning)

### b. Instal Prasyarat
Setelah VM berjalan, hubungkan melalui SSH dan instal prasyarat penting:

```bash
# Perbarui daftar paket
sudo apt-get update

# Instal Git untuk mengkloning repositori dan Docker untuk menjalankan container
sudo apt-get install -y git docker.io

# Tambahkan pengguna Anda ke grup docker agar tidak perlu menggunakan sudo setiap saat
# Anda perlu logout dan login kembali agar perubahan ini berlaku
sudo usermod -aG docker ${USER}
```

### c. Kloning Repositori
Kloning repositori proyek ke direktori home Anda:

```bash
# Ganti [URL_REPOSITORI_ANDA] dengan URL Git yang sebenarnya
git clone [URL_REPOSITORI_ANDA] reinforcement-learning-game-agent
cd reinforcement-learning-game-agent
```

## 3. Membangun Image Docker

Sebelum menjalankan pekerjaan apa pun, Anda perlu membangun image Docker yang berisi semua kode dan dependensi. Perintah ini hanya perlu dijalankan sekali, atau setiap kali Anda mengubah `Dockerfile` atau `requirements.txt`.

```bash
docker build -t rl-game-agent:latest .
```
*Catatan: Skrip `run_training_job.sh` juga akan menjalankan perintah ini secara otomatis.*

## 4. Menjalankan Training Standar

Untuk menjalankan satu sesi training dengan hyperparameter default yang ditentukan dalam kode:

```bash
bash ./run_training_job.sh
```

Skrip ini melakukan hal berikut:
1.  **Membangun Image Docker**: Memastikan image `rl-game-agent:latest` sudah terbaru.
2.  **Menjalankan Container**: Memulai container Docker dengan akses GPU (`--gpus all`).
3.  **Memetakan Volume**: Menghubungkan direktori lokal (`data`, `models`, `logs`) ke dalam container agar data, model yang disimpan, dan log tetap ada di VM Anda setelah container berhenti.
4.  **Memulai Training**: Menjalankan skrip `src/rl_agent/train.py` di dalam container.

## 5. Menjalankan Hyperparameter Tuning (HPT)

Untuk menjalankan pencarian hyperparameter tuning menggunakan Optuna:

```bash
# Pastikan image Docker sudah dibangun (lihat langkah 3)
docker run --rm --gpus all \
    -v "$(pwd)/data:/app/data" \
    -v "$(pwd)/models:/app/models" \
    -v "$(pwd)/logs:/app/logs" \
    rl-game-agent:latest \
    python3 run_optuna_hpt.py
```

Perintah ini akan:
1.  **Menjalankan Beberapa Sesi Training**: Optuna akan secara otomatis menjalankan banyak sesi training kecil, masing-masing dengan set hyperparameter yang berbeda.
2.  **Mencetak Hasil**: Setelah selesai, skrip akan mencetak hyperparameter terbaik yang ditemukan dan skor validasi yang sesuai langsung di konsol Anda.

## 6. Struktur Direktori Penting

Direktori berikut di-mount dari VM Anda ke dalam container, memungkinkan persistensi data:

-   `./data`: Tempatkan file data mentah Anda di sini (misalnya, `databaru_from_api.csv`). Skrip di dalam container akan membacanya dari `/app/data`.
-   `./models`: Model yang telah dilatih (misalnya, `best_model.pth`) dan artefak lainnya (seperti `feature_scaler.joblib`) akan disimpan di sini.
-   `./logs`: File log, gambar plot (misalnya, `evaluation_summary.png`), dan output lainnya akan disimpan di sini untuk analisis pasca-training.