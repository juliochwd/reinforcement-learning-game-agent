# ---- Tahap 1: Builder ----
# Menggunakan image Python penuh untuk menginstal dependensi
FROM python:3.10 AS builder

WORKDIR /app

# Menyalin hanya requirements.txt terlebih dahulu untuk caching
COPY requirements.txt .

# Perbarui apt dan instal JDK
RUN apt-get update && apt-get install -y openjdk-17-jdk --no-install-recommends && rm -rf /var/lib/apt/lists/*

# Instal Cython dan wheel
RUN pip install cython wheel

# Menginstal dependensi, termasuk torch yang besar
RUN pip install --no-cache-dir --timeout=600 -r requirements.txt


# ---- Tahap 2: Final ----
# Memulai dari image slim yang jauh lebih kecil
FROM python:3.10-slim

WORKDIR /app

# Menyalin HANYA paket yang terinstal dari tahap builder, bukan file cache atau installer
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages

# Menyalin kode aplikasi Anda
COPY . .

# Membuat pengguna non-root untuk keamanan
RUN useradd -m appuser
USER appuser

# Menetapkan entrypoint
ENTRYPOINT ["python", "-m"]