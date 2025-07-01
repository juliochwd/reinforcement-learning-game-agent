import torch
import torch.optim as optim
import random
from collections import deque
import numpy as np
import logging
import yaml
import os
import time
import argparse
import sys

# --- Path setup ---
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.utils import prepare_data_splits
from utils.model_helpers import load_config, create_environment
from rl_agent.model import ActorCriticSAC_GRU

# --- Basic Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def format_time(seconds):
    """Converts seconds into a human-readable HH:MM:SS format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d} jam, {minutes:02d} menit, {secs:02d} detik"

def main():
    """Main function to benchmark SAC training time."""
    parser = argparse.ArgumentParser(description="Benchmark and estimate total training time for the SAC agent.")
    parser.add_argument('--num_steps_to_profile', type=int, default=5000, help='Number of steps to run for benchmarking.')
    
    args = parser.parse_args()

    logging.info("--- Starting SAC Training Time Benchmark ---")
    logging.info(f"Running for {args.num_steps_to_profile} steps to profile...")

    # --- 1. Replicate SAC Training Setup ---
    config = load_config()
    sac_params = config.get('sac_hyperparameters', {})
    
    hyperparams = {
        'lr': sac_params.get('lr', 3e-4),
        'gamma': sac_params.get('gamma', 0.99),
        'hidden_size': sac_params.get('hidden_size', 256),
        'dropout_rate': sac_params.get('dropout_rate', 0.2),
        'batch_size': sac_params.get('batch_size', 256),
        'buffer_size': sac_params.get('buffer_size', 1_000_000),
        'tau': sac_params.get('tau', 0.005),
        'alpha': sac_params.get('alpha', 0.2),
        'autotune_alpha': sac_params.get('autotune_alpha', True)
    }

    try:
        # We only need the training data for this benchmark
        model_dir = config.get('model_dir', 'models/')
        scaler_path = os.path.join(model_dir, config.get('scaler_name', 'feature_scaler.joblib'))
        train_X, train_y, _, _, _, _ = prepare_data_splits(config['data_path'], scaler_path=scaler_path)
    except FileNotFoundError:
        logging.error(f"Data file not found at '{config['data_path']}'. Aborting.")
        return

    env = create_environment(train_X, train_y, config)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logging.info(f"Using device: {device}")

    agent = ActorCriticSAC_GRU(
        env.features_per_step, env.action_space.n, config['window_size'], 
        hyperparams['hidden_size'], hyperparams['dropout_rate']
    ).to(device)
    
    replay_buffer = deque(maxlen=hyperparams['buffer_size'])
    
    # --- 2. Benchmarking Loop ---
    logging.info("Starting benchmarking loop...")
    state, _ = env.reset()
    start_time = time.time()

    for global_step in range(1, args.num_steps_to_profile + 1):
        action = agent.get_action(state, device)
        next_state, reward, terminated, truncated, _ = env.step(action)
        done = terminated or truncated
        replay_buffer.append((state, action, reward, next_state, done))
        state = next_state
        if done:
            state, _ = env.reset()
        
        if (global_step + 1) % 1000 == 0:
            logging.info(f"Benchmark step {global_step + 1}/{args.num_steps_to_profile}...")

    end_time = time.time()
    logging.info("Benchmarking loop finished.")

    # --- 3. Calculation and Output ---
    total_benchmark_time = end_time - start_time
    steps_per_second = args.num_steps_to_profile / total_benchmark_time
    
    total_timesteps_final = config.get('sac_hyperparameters', {}).get('total_timesteps_final', 200000)
    estimated_total_time = total_timesteps_final / steps_per_second

    total_timesteps_hpt = config.get('total_timesteps_trial', 20000)
    n_trials = config.get('n_trials', 50)
    estimated_hpt_time = (total_timesteps_hpt / steps_per_second) * n_trials

    print("\n" + "="*50)
    print("--- Laporan Estimasi Waktu Training SAC ---")
    print("="*50)
    print(f"Langkah untuk Profiling: {args.num_steps_to_profile}")
    print(f"Total Waktu Profiling: {format_time(total_benchmark_time)}")
    print(f"Langkah per Detik (SPS): {steps_per_second:.2f}")
    print("-"*50)
    print(f"Estimasi Waktu Training Penuh ({total_timesteps_final} langkah):")
    print(f"==> {format_time(estimated_total_time)}")
    print("-"*50)
    print(f"Estimasi Waktu Hyperparameter Search ({n_trials} trial @ {total_timesteps_hpt} langkah):")
    print(f"==> {format_time(estimated_hpt_time)}")
    print("="*50)
    print("\nCatatan: Estimasi ini adalah 'best-case' karena tidak termasuk overhead dari pembaruan model.")
    print("Waktu sebenarnya akan sedikit lebih lama, tetapi ini memberikan gambaran kasar.")

if __name__ == '__main__':
    main()
