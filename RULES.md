# PROJECT RULES

## 1. Coding Standards
- Gunakan Python 3.10+ dan ikuti PEP8.
- Semua modul harus modular, reusable, dan mudah diuji.
- Selalu gunakan type hinting dan docstring pada setiap fungsi/class.
- Jangan gunakan fitur deprecated atau hacky.
- Semua perubahan harus lulus linter (flake8/pylint) dan unit test.
- Jangan pernah hardcode path, API key, atau credential di kode.

## 2. Data Handling & Anti-Leakage
- **Split data harus kronologis** (tidak ada data masa depan di train).
- **Feature engineering hanya dari Number** (lag, rolling, fourier). Dilarang menggunakan Premium, Big/Small, Color, streak, corr, wavelet, dsb.
- Tidak boleh ada fitur masa depan, label leakage, atau lookahead bias.
- Audit otomatis X_cols, distribusi label, shape, dan anti-leakage wajib dijalankan setiap perubahan besar.
- Semua data training, test, dan prediksi hanya disimpan lokal.

## 3. Model Training & Evaluation
- Training dan tuning hanya boleh menggunakan fitur yang sudah diaudit.
- Hyperparameter tuning harus menggunakan Optuna dengan logging dan anti-overfitting.
- Evaluasi model wajib mencakup:
  - Akurasi single-label (top-1)
  - Akurasi multi-number (top-N, confidence threshold)
  - Confusion matrix dan classification report
- Overfitting monitoring: warning jika gap akurasi train-test > 0.1.
- Setiap perubahan feature engineering WAJIB diikuti training ulang.

## 4. Deployment & Production
- Semua proses training, tuning, dan prediksi harus thread-safe dan tidak blocking GUI.
- Logging hanya ke file lokal, tidak ada remote logging tanpa izin eksplisit.
- Model hanya diupdate dengan data baru yang valid dan sudah diaudit.
- Tidak ada update model otomatis dari sumber tidak terpercaya.
- Backup model dan data secara rutin.
- Jangan expose port/endpoint pipeline ke publik tanpa autentikasi.

## 5. Security & Privacy
- Data user/game tidak pernah dibagikan ke pihak ketiga.
- API key hanya disimpan di .cursor/mcp.json atau environment variable, tidak di kode.
- Jangan commit credential ke repo publik.
- Scraping hanya dari endpoint resmi dan legal.
- Integrasi MCP hanya untuk fitur yang diizinkan.
- Audit model dan data dilakukan sebelum deployment.
- Update dependency secara berkala, cek CVE/security advisory.

## 6. MCP Integration
- Semua MCP server harus didefinisikan di `.cursor/mcp.json`.
- Jangan pernah expose API key di kode atau dokumentasi.
- Untuk menambah MCP baru, tambahkan entry sesuai format dan audit keamanan.
- Hanya gunakan MCP yang sudah diaudit dan legal.

## 7. Collaboration & Contribution
- Semua kontribusi harus melalui pull request dan lulus audit anti-leakage serta unit test.
- Setiap perubahan besar harus didokumentasikan di CHANGELOG.md.
- Diskusikan perubahan arsitektur di issue sebelum implementasi.
- Semua diskusi keamanan harus diberi label `security`.

## 8. Audit & Testing
- Jalankan unit test dan audit integritas data sebelum merge/deploy.
- Gunakan script audit (validate_data_integrity.py) untuk cek anti-leakage.
- Semua log audit harus disimpan di folder logs/.
- Lakukan audit manual setiap bulan atau setiap perubahan besar.

## 9. Troubleshooting & Support
- Semua error harus dilog ke file dan GUI.
- Jika menemukan potensi celah keamanan, segera laporkan ke maintainer.
- FAQ dan troubleshooting harus selalu diupdate di README.md.

---

**Project ini wajib mematuhi seluruh aturan di atas untuk menjaga keamanan, integritas, dan kualitas produksi.** 