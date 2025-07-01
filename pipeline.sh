#!/bin/bash
set -e
set -x # Enable debugging

# --- Variables ---
PYTHON_CMD="python3.12"
PROJECT_DIR=$(dirname "$(readlink -f "$0")")
VENV_DIR="$PROJECT_DIR/venv"

echo "============================================="
echo "STARTING FULL VM PIPELINE (HPT + FINAL)"
echo "============================================="

# --- Virtual Environment Setup ---
# Menghapus venv yang ada secara paksa untuk memastikan pembangunan ulang dengan setup.py terbaru.
# Ini diperlukan satu kali untuk membuat entry points console script.
echo "--> Forcing a one-time rebuild of the virtual environment to apply new setup."
rm -rf "$VENV_DIR"

# Selalu buat venv baru pada eksekusi ini
if [ ! -d "$VENV_DIR" ]; then
    echo "--> Creating and setting up a fresh virtual environment..."
    echo "PROGRESS: 10%"

    echo "--> Creating new virtual environment with $PYTHON_CMD..."
    $PYTHON_CMD -m venv "$VENV_DIR"
    echo "Virtual environment created."
    echo "PROGRESS: 20%"

    echo "--> Activating and installing dependencies..."
    source "$VENV_DIR/bin/activate"
    pip install --upgrade pip
    echo "PROGRESS: 30%"
    pip install -r "$PROJECT_DIR/requirements.txt"
    echo "--> Installing project in editable mode..."
    pip install -e .
    # Nonaktifkan setelah penyiapan selesai
    deactivate
    echo "PROGRESS: 50%"
else
    # Jika venv sehat, kita sudah siap 50%
    echo "PROGRESS: 50%"
fi

# --- Activate for Execution ---
echo "--> Activating virtual environment for script execution..."
source "$VENV_DIR/bin/activate"

echo "--- Checking Python path after activation ---"
which $PYTHON_CMD || echo "WARNING: $PYTHON_CMD not found in PATH after activation."

# --- Run Hyperparameter Tuning ---
echo "--> STAGE 1: Running Hyperparameter Search..."
# Run the console script entry point created by setup.py
run-hpt
echo "PROGRESS: 80%"

# --- Run Final Model Training ---
echo "--> STAGE 2: Running Final Model Training..."
# Run the console script entry point created by setup.py
train-final
echo "PROGRESS: 100%"

# --- Deactivate ---
deactivate
echo "============================================="
echo "VM PIPELINE FINISHED SUCCESSFULLY"
echo "============================================="
