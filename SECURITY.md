# SECURITY POLICY

## Data Security & Privacy
- **Data user/game tidak pernah dibagikan ke pihak ketiga.**
- **Semua data training, test, dan prediksi hanya disimpan lokal.**
- **Tidak ada data sensitif yang diupload ke cloud tanpa izin eksplisit.**

## Anti-Data Leakage
- **Pipeline dirancang anti-leakage:**
  - Split data kronologis (tidak ada data masa depan di train).
  - Feature engineering hanya dari Number (tanpa Premium, Big/Small, Color, dsb).
  - Tidak ada fitur masa depan, label leakage, atau lookahead bias.
  - Audit otomatis X_cols, distribusi label, shape, dan anti-leakage.
- **Audit kode dan data dilakukan setiap perubahan besar.**

## Credential & API Key Management
- **API key (misal FIRECRAWL_API_KEY) disimpan di .cursor/mcp.json, bukan di kode.**
- **Jangan commit credential ke repo publik.**
- **Gunakan environment variable untuk API key di server produksi.**

## Keamanan Scraping & Integrasi
- **Scraping hanya dari endpoint resmi dan legal.**
- **Tidak ada scraping data user tanpa izin.**
- **Integrasi MCP (context7, firecrawl, supermemory, dsb.) hanya untuk fitur yang diizinkan.**

## Keamanan Pipeline & Model
- **Model hanya diupdate dengan data baru yang valid.**
- **Tidak ada update model otomatis dari sumber tidak terpercaya.**
- **Audit model dan data dilakukan sebelum deployment.**
- **Logging hanya ke file lokal, tidak ada remote logging tanpa izin.**

## Best Practice Keamanan
- **Selalu training ulang model setelah perubahan fitur.**
- **Audit pipeline dan data secara berkala.**
- **Gunakan virtual environment untuk isolasi dependency.**
- **Update dependency secara berkala, cek CVE/security advisory.**
- **Jangan expose port/endpoint pipeline ke publik tanpa autentikasi.**

## Saran Keamanan Produksi
- **Gunakan server dengan akses terbatas (firewall, VPN).**
- **Pisahkan environment dev, staging, dan production.**
- **Backup data dan model secara rutin.**
- **Audit akses ke data dan model.**
- **Gunakan monitoring untuk deteksi anomali/potensi serangan.**

---

**Jika menemukan potensi celah keamanan, segera laporkan ke maintainer.**
