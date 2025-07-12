# Reinforcement Learning Game Agent (Supervised, Anti-Leakage)

## Deskripsi Proyek
Pipeline produksi untuk supervised online learning prediksi Number pada game, menggunakan River (HoeffdingTreeClassifier) dan Optuna untuk hyperparameter tuning. Dirancang anti-leakage, modular, robust, dan siap produksi. Mendukung GUI (customtkinter), integrasi scraping, dan monitoring real-time.

## Fitur Utama
- **Supervised Online Learning**: River HoeffdingTreeClassifier, update model real-time.
- **Feature Engineering Anti-Leakage**: Hanya lag, rolling, fourier dari Number (tanpa Premium, Big/Small, Color, dsb).
- **Hyperparameter Tuning**: Optuna, anti-overfitting, logging lengkap, dashboard-ready.
- **Evaluasi Lengkap**: Akurasi single-label (top-1) & multi-number (top-N, confidence threshold).
- **Prediksi Online**: Prediksi beberapa Number sekaligus (multi-number) sesuai threshold confidence.
- **GUI Modern**: customtkinter, tab Settings, Logs, Data Management, Training, dsb.
- **Realtime CSV/API Watcher**: Monitoring data baru, prediksi otomatis, update model.
- **Audit & Logging**: Audit anti-leakage, logging ke file & GUI, audit fitur otomatis.
- **Integrasi MCP**: Mendukung context7, sequential-thinking, firecrawl-mcp, Pieces, supermemory.

## Arsitektur
- `src/app/supervised_ensemble_trainer.py`: Pipeline utama training, evaluasi, prediksi, watcher.
- `src/utils/feature_engineering.py`: Feature engineering anti-leakage (lag, rolling, fourier Number).
- `src/app/gui.py`: GUI customtkinter, tab Settings, Logs, dsb.
- `src/rl_agent/data_scraper.py`: Scraping data API, integrasi ke pipeline.
- `.cursor/mcp.json`: Konfigurasi MCP (context7, sequential-thinking, firecrawl-mcp, Pieces, supermemory).

## Anti-Leakage & Best Practice
- **Split data kronologis** (train/test), tidak ada data masa depan di train.
- **Feature engineering hanya dari Number** (lag, rolling, fourier), tanpa fitur dari Premium, Big/Small, Color, streak, corr, wavelet, dsb.
- **Audit otomatis**: X_cols, distribusi label, shape, anti-lookahead, anti-label leakage.
- **Training, tuning, evaluasi, prediksi, watcher**: Semua konsisten hanya pakai fitur Number.
- **Overfitting monitoring**: Warning jika gap akurasi train-test > 0.1.

## Instalasi & Setup
1. **Clone repo & masuk ke direktori**
   ```bash
   git clone <repo-url>
   cd reinforcement-learning-game-agent
   ```
2. **Buat virtual environment & install dependencies**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # atau .venv\Scripts\activate di Windows
   pip install -r requirements.txt
   ```
3. **Konfigurasi MCP (opsional)**
   - Edit `.cursor/mcp.json` untuk menambah/atur MCP server (context7, firecrawl, supermemory, dsb).

## Cara Training Ulang
1. Jalankan pipeline training dari GUI atau script:
   ```python
   from src.app.supervised_ensemble_trainer import SupervisedEnsembleTrainer
   trainer = SupervisedEnsembleTrainer()
   trainer.train_ensemble()
   ```
2. Untuk hyperparameter tuning:
   ```python
   trainer.run_optuna_search(n_trials=30)
   ```

## Evaluasi Model
- **Akurasi single-label (top-1):**
  ```python
  trainer.evaluate_ensemble()
  ```
- **Akurasi multi-number (top-N, confidence threshold):**
  ```python
  trainer.evaluate_ensemble(threshold=0.7)
  # atau
  trainer.show_multinumber_accuracy(threshold=0.7)
  ```
- **Analisis model (confusion matrix, classification report, multi-number accuracy):**
  ```python
  trainer.show_ensemble_analysis(threshold=0.7)
  ```

## Prediksi Online
- **Prediksi satu data terbaru:**
  ```python
  trainer.predict_ensemble()
  ```
- **Prediksi otomatis dari watcher (CSV/API):**
  - Aktifkan watcher dari GUI atau panggil `trainer.start_csv_watcher()`

## Pengaturan MCP
- `.cursor/mcp.json` sudah mendukung context7, sequential-thinking, firecrawl-mcp, Pieces, supermemory.
- Untuk menambah MCP baru, tambahkan entry sesuai format di file tersebut.

## Troubleshooting
- **Model error saat prediksi:** Pastikan sudah training ulang setelah perubahan fitur.
- **Akurasi rendah:** Data Number memang acak, pipeline sudah anti-leakage.
- **Linter error:** Sudah diatasi dengan type checking, type: ignore, dan isinstance.
- **Warning pywt:** Sudah tidak ada fitur wavelet, warning aman diabaikan.

## FAQ
- **Q: Kenapa akurasi rendah?**
  - A: Karena hanya fitur Number yang digunakan, tidak ada pola prediktif kuat (anti-leakage).
- **Q: Bolehkah menambah fitur lain?**
  - A: Boleh, tapi risiko data leakage tinggi. Pipeline ini dirancang untuk keamanan maksimal.
- **Q: Bagaimana menambah MCP baru?**
  - A: Edit `.cursor/mcp.json` sesuai format.
- **Q: Bagaimana mengubah threshold confidence?**
  - A: Ubah argumen `threshold` pada fungsi evaluasi/prediksi.

---

**Pipeline ini sudah siap produksi, robust, modular, dan anti-leakage.**
Jika ada pertanyaan atau ingin integrasi lebih lanjut, silakan hubungi maintainer.
