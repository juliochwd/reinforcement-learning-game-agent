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
VENV_HEALTHY=false
# Periksa apakah direktori venv ada
if [ -d "$VENV_DIR" ]; then
    echo "--> Virtual environment found. Performing health check..."
    # Coba aktifkan venv dan impor library kunci (misalnya, torch).
    # Redirect output error ke null agar tidak mengacaukan log jika gagal.
    if source "$VENV_DIR/bin/activate" && python -c "import torch; import pandas; import optuna" &> /dev/null; then
        VENV_HEALTHY=true
        echo "--> Health check PASSED. Skipping setup."
        deactivate # Nonaktifkan setelah pemeriksaan kesehatan
    else
        echo "--> Health check FAILED. venv is corrupted or incomplete. Rebuilding..."
        rm -rf "$VENV_DIR"
    fi
fi

# Jika venv tidak sehat atau tidak ada, buat dari awal.
if [ "$VENV_HEALTHY" = false ]; then
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

# --- Set PYTHONPATH to ensure project modules are found ---
export PYTHONPATH=$PROJECT_DIR
echo "--> PYTHONPATH set to: $PYTHONPATH"

# --- Run Hyperparameter Tuning ---
echo "--> STAGE 1: Running Hyperparameter Search..."
# The python script is expected to print its own PROGRESS updates
$PYTHON_CMD "$PROJECT_DIR/src/rl_agent/hyperparameter_search.py"
echo "PROGRESS: 80%"

# --- Run Final Model Training ---
echo "--> STAGE 2: Running Final Model Training..."
# The python script is expected to print its own PROGRESS updates
$PYTHON_CMD "$PROJECT_DIR/train_final_model.py"
echo "PROGRESS: 100%"

# --- Deactivate ---
deactivate
echo "============================================="
echo "VM PIPELINE FINISHED SUCCESSFULLY"
echo "============================================="
