#!/bin/bash
set -e # Exit immediately if a command exits with a non-zero status.

# ==============================================================================
# Skrip untuk Menjalankan Training Job Secara Lokal di dalam Container Docker
# ==============================================================================
#
# Deskripsi:
# Skrip ini mengotomatiskan proses berikut:
# 1. Membangun image Docker dari Dockerfile yang ada.
# 2. Menjalankan container dari image tersebut untuk memulai proses training.
#
# Prasyarat:
# 1. Docker sudah terinstal dan berjalan di mesin lokal (VM).
# 2. Driver NVIDIA dan NVIDIA Container Toolkit sudah terinstal untuk dukungan GPU.
#
# Cara Penggunaan:
# - Jalankan skrip dari terminal: ./run_training_job.sh
#
# ==============================================================================

IMAGE_NAME="rl-game-agent:latest"

echo "=================================================="
echo "Membangun image Docker..."
echo "=================================================="
docker build -t $IMAGE_NAME .
echo "Image Docker berhasil dibangun dengan tag: $IMAGE_NAME"

echo "=================================================="
echo "Menjalankan training job di dalam container Docker..."
echo "=================================================="

# Menjalankan container dan menghapusnya setelah selesai.
# Kode Python di dalam container sekarang bertanggung jawab untuk menangani path GCS.
# Pastikan file config.yaml Anda sudah diatur untuk menunjuk ke path GCS.
docker run --rm \
    $IMAGE_NAME \
    python -m train_pipeline

echo "=================================================="
echo "Training job selesai."
echo "=================================================="