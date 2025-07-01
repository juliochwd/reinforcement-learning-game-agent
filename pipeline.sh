#!/bin/bash
set -e

# --- Variables ---
PYTHON_CMD="python3.12"
PROJECT_DIR=$(dirname "$(readlink -f "$0")")
VENV_DIR="$PROJECT_DIR/venv"

echo "============================================="
echo "STARTING FULL VM PIPELINE (HPT + FINAL)"
echo "============================================="

# --- Virtual Environment Setup ---
echo "--> Removing old virtual environment to ensure a clean state..."
rm -rf "$VENV_DIR"

echo "--> Creating new virtual environment with $PYTHON_CMD..."
$PYTHON_CMD -m venv "$VENV_DIR"
echo "Virtual environment created."

# --- Activate and Install Dependencies ---
echo "--> Activating virtual environment and installing dependencies..."
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -r "$PROJECT_DIR/requirements.txt"

# --- Run Hyperparameter Tuning ---
echo "--> STAGE 1: Running Hyperparameter Search..."
python "$PROJECT_DIR/src/rl_agent/hyperparameter_search.py"

# --- Run Final Model Training ---
echo "--> STAGE 2: Running Final Model Training..."
python "$PROJECT_DIR/train_final_model.py"

# --- Deactivate ---
deactivate
echo "============================================="
echo "VM PIPELINE FINISHED SUCCESSFULLY"
echo "============================================="
