#!/bin/bash
set -e
set -x # Enable debugging

# --- Variables ---
# Use the VM's default, pre-installed, and optimized python3 interpreter.
PYTHON_CMD="python3"
PROJECT_DIR=$(dirname "$(readlink -f "$0")")
VENV_DIR="$PROJECT_DIR/venv"

echo "============================================="
echo "STARTING FULL VM PIPELINE (HPT + FINAL)"
echo "============================================="

# --- Environment Variable Constraints for VM ---
# Force underlying numerical libraries (NumPy, PyTorch, etc.) to use a single thread.
# This is the definitive fix for the 400% CPU usage issue on the VM.
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1

# --- Virtual Environment Setup ---
# We force a rebuild to ensure it uses the correct python3.10 interpreter
# and installs the correct package entry points.
echo "--> Forcing venv rebuild to use the VM's native Python 3.10"
rm -rf "$VENV_DIR"

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
echo "--> Logging HPT output to /tmp/hpt.log on the VM."
# Run the console script entry point, redirecting all output to a log file
# This prevents the SSH session from hanging and allows for post-mortem debugging.
run-hpt > /tmp/hpt.log 2>&1
echo "--> HPT process finished. See /tmp/hpt.log on the VM for details."
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
