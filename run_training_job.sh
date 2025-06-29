#!/bin/bash
set -e # Exit immediately if a command exits with a non-zero status.

echo "=================================================="
echo "Membuat file config.yaml untuk lingkungan cloud..."
echo "=================================================="
cat <<EOF > config.yaml
# Configuration for the Reinforcement Learning Game Agent
# --- File Paths ---
# Relative to the reinforcement-learning-game-agent directory
data_path: "data/databaru_from_api.csv"
model_dir: "model/"
best_model_name: "best_tuned_model.pth"
scaler_name: "feature_scaler.joblib"
log_dir: "logs/"
mlflow_dir: "mlruns/"

# --- Environment and Model Parameters ---
window_size: 30
features_per_step: 29 # This value is now dynamically determined by feature_engineering.py
bet_percentages: [0.01, 0.025] # The bet sizes available to the agent.

# --- Environment Reward Parameters ---
# These parameters are used by the TradingEnv
loss_penalty_multiplier: 1.3  # Multiplier for losses. > 1.0 makes the agent more risk-averse.
win_bonus: 1.0e-5             # Small bonus for any correct bet to encourage participation.
time_decay_penalty: 1.0e-6    # Small penalty for holding, to encourage action.
transaction_cost: 1.0e-4      # Cost per transaction.

# --- Training Parameters ---
# For Optuna Hyperparameter Search
n_trials: 50
num_episodes_trial: 50 # Episodes per Optuna trial
eval_every: 5
target_update_frequency: 10 # How many episodes before updating the target network
early_stopping_patience: 5  # How many validation checks without improvement before stopping

# For Final Model Training
num_episodes_final: 100 # Episodes for training the final best model

# --- Replay Memory ---
memory_size: 50000 # Increased memory size for PER to be more effective

# --- Hyperparameter Search Space (for Optuna) ---
# These are the ranges Optuna will search within.
hyperparameters:
  lr:
    low: 1.0e-5
    high: 1.0e-3
  gamma:
    low: 0.9
    high: 0.999
  hidden_size: [128, 256]
  dropout_rate:
    low: 0.1
    high: 0.5
  batch_size: [32, 64]
  eps_decay:
    low: 1000
    high: 5000

# --- Epsilon-Greedy Strategy ---
eps_start: 0.9
eps_end: 0.05

# --- Setup Configuration ---
setup:
  python_version: "3.10"
  dependencies:
    - "scikit-learn"
    - "matplotlib"
  directories:
    - "data/raw"
    - "data/processed"
    - "notebooks"


# --- UI Configuration (for app.py) ---
ui:
  title: "Game Agent Control Center"
  geometry: "900x700"
  default_eta_text: "ETA: --:--"
  initial_balance_display: "2,000,000.00"
  colors:
    background: "#f0f2f5"
    sidebar: "#ffffff"
    accent: "#1877f2"
    text: "#050505"
    log_background: "#1e1e1e"
    log_foreground: "#d4d4d4"
  fonts:
    normal: { family: "Helvetica", size: 11 }
    bold: { family: "Helvetica", size: 11, weight: "bold" }
    header: { family: "Helvetica", size: 16, weight: "bold" }
  sidebar_buttons:
    "Dashboard": "📊"
    "Data Management": "💾"
    "Train & Validate": "🏋️"
    "Test Best Model": "📈"

# --- Web Agent & Scraping Configuration ---
web_agent:
  login_url: "https://55v7nlu.com/#/login"
  api_endpoint: "api.55fiveapi.com/api/webapi/GetNoaverageEmerdList"
  initial_balance: 2000000
  bet_unit_divisor: 1000 # e.g., 1000 units = 1000 currency
  scraping:
    max_pages: 300
    zoom_level: "80%"
  timeouts:
    page_load: 60
    element_wait: 30
    api_wait: 15
    recovery_threshold_seconds: 75
    bet_placement_buffer_seconds: 7
  timers:
    post_login_sleep: 3
    post_action_sleep: 1
    popup_check_sleep: 0.5
    api_retry_delay: 2
  xpaths:
    login:
      user_input: { by: "NAME", value: "userNumber" }
      password_input: { by: "XPATH", value: '//input[@placeholder="Password"]' }
      submit_button: { by: "XPATH", value: '//button[text()="Log in"]' }
    navigation:
      win_go_menu: { by: "XPATH", value: "//div[@class='lottery' and .//span[normalize-space()='Win Go']]" }
      win_go_1min_button: { by: "XPATH", value: "//div[contains(@class, 'GameList__C-item') and contains(., '1Min') and not(contains(., '30s'))]" }
      my_account_button: { by: "XPATH", value: "//div[contains(@class, 'van-tabbar-item') and .//div[text()='My' or text()='Saya']]" }
      logout_button: { by: "XPATH", value: "//div[contains(@class, 'mine-content-item') and .//div[text()='Log out']]" }
      game_history_button: { by: "XPATH", value: "//div[contains(@class, 'mine-content-item') and .//div[text()='Game history']]" }
      history_next_page_button: { by: "XPATH", value: "//div[contains(@class, 'GameRecord__C-foot-next')]" }
    game_interface:
      timer_display: { by: "XPATH", value: "//div[@class='TimeLeft__C-time']" }
      period_display: { by: "XPATH", value: "//div[contains(@class, 'TimeLeft__C-id')]" }
      balance_container: { by: "XPATH", value: "//div[contains(@class, 'Wallet__C-balance-l1')]" }
      balance_value: { by: "XPATH", value: "./div" } # Relative to balance_container
      balance_refresh_button: { by: "XPATH", value: "./i[contains(@class, 'van-icon-replay')]" } # Relative
      bet_small_button: { by: "XPATH", value: "//div[contains(@class, 'Betting__C-foot-s')]" }
      bet_big_button: { by: "XPATH", value: "//div[contains(@class, 'Betting__C-foot-b')]" }
      bet_amount_input: { by: "XPATH", value: "//input[contains(@class, 'van-field__control')]" }
      bet_confirm_button: { by: "XPATH", value: "//div[contains(@class, 'Betting__Popup-foot-s')]" }
      popup_confirm_button: { by: "XPATH", value: "//div[@class='promptBtn' and text()='Confirm']" }
      popup_close_icon: { by: "XPATH", value: "//i[contains(@class, 'van-icon-close')]" }
    history_interface:
      page_info: { by: "CLASS_NAME", value: "GameRecord__C-foot-page" }
EOF

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