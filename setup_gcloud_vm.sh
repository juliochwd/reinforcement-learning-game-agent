#!/bin/bash

# 1. Memperbarui daftar paket dan memastikan utilitas dasar terpasang
echo "Memperbarui daftar paket dan memastikan utilitas terpasang..."
sudo apt-get update
sudo apt-get install -y python3-pip curl yq

# 2. Membuat direktori proyek dan menyalin file
echo "Membuat direktori proyek dan menyalin file..."
PROJ_DIR="/home/$USER/reinforcement-learning-game-agent"
mkdir -p $PROJ_DIR
# Salin semua file dari direktori saat ini ke direktori proyek
# Ini mengasumsikan skrip dijalankan dari root repositori yang di-clone/di-scp
cp -r ./* $PROJ_DIR/
cd $PROJ_DIR

# Gunakan python3.10 yang sudah ada dari image Deep Learning VM
PYTHON_EXEC="python3.10"

# 4. Membuat virtual environment
echo "Membuat virtual environment dengan $PYTHON_EXEC..."
VENV_DIR="$PROJ_DIR/venv"
$PYTHON_EXEC -m venv $VENV_DIR

# 5. Memasang dependensi Python di dalam venv menggunakan requirements.txt
echo "Memasang dependensi Python dari requirements.txt..."
$VENV_DIR/bin/pip install --upgrade pip
$VENV_DIR/bin/pip install -r requirements.txt

# 6. Membuat direktori yang diperlukan (jika ada yang masih relevan)
# Jika semua direktori sudah diatur oleh kode, bagian ini bisa disederhanakan atau dihapus.
# Untuk saat ini, kita asumsikan direktori 'logs' dan 'models' perlu dibuat.
echo "Membuat direktori logs dan models..."
mkdir -p "$PROJ_DIR/logs"
mkdir -p "$PROJ_DIR/models"

# 7. Mengubah kepemilikan direktori proyek untuk memastikan izin yang benar
echo "Finalisasi kepemilikan direktori..."
sudo chown -R $USER:$USER $PROJ_DIR

echo "Setup selesai!"
echo "PENTING: Aktifkan venv untuk melanjutkan dengan menjalankan:"
echo "source $VENV_DIR/bin/activate"