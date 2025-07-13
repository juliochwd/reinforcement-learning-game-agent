# Reinforcement Learning Game Agent (Supervised, Anti-Leakage)

## Deskripsi Proyek
Pipeline produksi untuk supervised online learning prediksi Number pada game, menggunakan River (HoeffdingTreeClassifier) dan Optuna untuk hyperparameter tuning. Dirancang anti-leakage, modular, robust, dan siap produksi. Mendukung GUI (customtkinter), integrasi scraping, dan monitoring real-time.

## Fitur Utama
- **Supervised Online Learning**: River HoeffdingTreeClassifier, update model real-time.
- **Ensemble Default**: VotingEnsemble (beberapa HoeffdingTree) sebagai model default, lebih stabil.
- **Model Versioning & Rollback Otomatis**: Model dan metadata disimpan per versi, rollback otomatis jika streak/drift ekstrem.
- **Feature Engineering Anti-Leakage**: Hanya lag, rolling, fourier dari Number (tanpa Premium, Big/Small, Color, dsb).
- **Hyperparameter Tuning**: Optuna, anti-overfitting, logging lengkap, dashboard-ready.
- **Evaluasi Lengkap**: Akurasi multi-number (top-N, confidence threshold), longest losing streak, drift monitoring.
- **Objective Training Modern**: Model dilatih untuk minimasi longest losing streak pada prediksi multi-number, bukan hanya single-label accuracy.
- **Prediksi Online**: Prediksi beberapa Number sekaligus (multi-number) sesuai threshold confidence.
- **GUI Modern & Monitoring**: customtkinter, tab Monitoring (grafik streak, distribusi prediksi, drift), Settings, Logs, Data Management, Training, dsb.
- **Realtime CSV/API Watcher**: Monitoring data baru, prediksi otomatis, update model.
- **Audit & Logging**: Audit anti-leakage, logging ke file & GUI, audit fitur otomatis.
- **Notifikasi Telegram Otomatis**: Rollback, drift, streak ekstrem langsung ke Telegram.
- **Integrasi MCP**: Mendukung context7, sequential-thinking, firecrawl-mcp, Pieces, supermemory.
- **CI/CD Otomatis**: Linter, unit test, audit anti-leakage otomatis di GitHub Actions.

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
- **Akurasi multi-number (top-N, confidence threshold) & Longest Losing Streak:**
  ```python
  result = trainer.evaluate_with_confidence_threshold(threshold=0.7)
  print(result['multi_number_accuracy'])
  print(result['longest_losing_streak'])
  # Output contoh:
  # multi_number_accuracy: 0.42
  # longest_losing_streak: 5
  ```
- **Analisis model (confusion matrix, classification report, multi-number accuracy, longest losing streak):**
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

## Monitoring & Visualisasi
- Tab Monitoring di GUI: grafik streak kekalahan, distribusi prediksi, dan deteksi drift real-time.
- Semua event penting (rollback, drift, streak ekstrem) otomatis dikirim ke Telegram.

## Deployment & Troubleshooting
- Model versioning otomatis, rollback mudah jika performa menurun.
- Semua error, rollback, drift, dan streak ekstrem tercatat di log, GUI, dan Telegram.
- CI/CD: Setiap push/PR otomatis audit, linter, dan unit test.

## FAQ
- **Q: Kenapa streak kekalahan bisa panjang?**
  - A: Karena data Number acak dan hanya fitur Number yang digunakan (anti-leakage), model tetap bisa mengalami streak panjang. Tuning weight streak di training bisa membantu.
- **Q: Bagaimana mengubah fokus training ke streak?**
  - A: Atur parameter `weight_streak` di `SupervisedEnsembleTrainer`.

---

**Pipeline ini sudah siap produksi, robust, modular, anti-leakage, dan kini fokus pada minimasi streak kekalahan multi-number.**
Jika ada pertanyaan atau ingin integrasi lebih lanjut, silakan hubungi maintainer.
