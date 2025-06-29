import torch
import torch.optim as optim
import torch.nn.functional as F
import random
import math
import pandas as pd
from collections import namedtuple, deque
import logging
import yaml
import os
import time
import argparse
import sys

# --- Path setup for utils ---
# This ensures that we can import modules from the 'src' directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))
from utils import prepare_data_splits
from rl_agent.model import GRU_DQN
from rl_agent.environment import TradingEnv
from utils.per import PrioritizedReplayMemory, Transition

# --- Basic Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_config():
    """Loads the configuration from config.yaml."""
    config_path = 'config.yaml'
    if not os.path.exists(config_path):
        logging.error(f"Configuration file not found at: {config_path}")
        raise FileNotFoundError(f"Configuration file not found at: {config_path}")
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config

def optimize_model(policy_net, target_net, memory, optimizer, batch_size, gamma, device):
    """
    Performs one step of optimization on the policy network.
    This function is copied from train.py to ensure identical logic.
    """
    if len(memory) < batch_size:
        return

    transitions, idxs, is_weights = memory.sample(batch_size)
    batch = Transition(*zip(*transitions))

    is_weights = torch.tensor(is_weights, dtype=torch.float32, device=device)

    non_final_mask = torch.tensor(tuple(map(lambda s: s is not None, batch.next_state)), device=device, dtype=torch.bool)
    non_final_next_states = torch.cat([s for s in batch.next_state if s is not None])
    
    state_batch = torch.cat(batch.state)
    action_batch = torch.cat(batch.action)
    reward_batch = torch.cat(batch.reward)

    state_action_values = policy_net(state_batch).gather(1, action_batch)

    next_state_values = torch.zeros(batch_size, device=device)
    with torch.no_grad():
        best_actions = policy_net(non_final_next_states).max(1)[1].unsqueeze(1)
        q_values_from_target = target_net(non_final_next_states)
        next_state_values[non_final_mask] = q_values_from_target.gather(1, best_actions).squeeze(1)

    expected_state_action_values = (next_state_values * gamma) + reward_batch

    loss = F.smooth_l1_loss(state_action_values, expected_state_action_values.unsqueeze(1), reduction='none')
    
    errors = torch.abs(state_action_values - expected_state_action_values.unsqueeze(1)).detach().cpu().numpy()
    for i in range(len(idxs)):
        memory.update(idxs[i], errors[i][0])

    weighted_loss = (loss * is_weights.unsqueeze(1)).mean()

    optimizer.zero_grad()
    weighted_loss.backward()
    torch.nn.utils.clip_grad_value_(policy_net.parameters(), 100)
    optimizer.step()

def format_time(seconds):
    """Converts seconds into a human-readable HH:MM:SS format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d} jam, {minutes:02d} menit, {secs:02d} detik"

def main():
    """Main function to benchmark training time."""
    parser = argparse.ArgumentParser(description="Benchmark and estimate total training time for the RL agent.")
    parser.add_argument('--num_episodes_to_profile', type=int, default=3, help='Number of episodes to run for benchmarking (reduced for faster estimation).')
    parser.add_argument('--total_episodes', type=int, default=1000, help='Total number of episodes for the full training plan.')
    
    args = parser.parse_args()

    logging.info("--- Memulai Benchmark Waktu Training ---")
    logging.info(f"Menjalankan {args.num_episodes_to_profile} episode untuk membuat profil...")

    # --- 1. Replikasi Setup Training dari train.py ---
    config = load_config()
    
    # Gunakan hyperparameter default atau dari config untuk konsistensi
    hyperparams = {
        'lr': config['hyperparameters']['lr']['low'],
        'gamma': config['hyperparameters']['gamma']['high'],
        'hidden_size': config['hyperparameters']['hidden_size'][0],
        'dropout_rate': config['hyperparameters']['dropout_rate']['low'],
        'batch_size': config['hyperparameters']['batch_size'][0],
        'eps_decay': config['hyperparameters']['eps_decay']['low']
    }

    try:
        train_X, train_y, _, _, _, _ = prepare_data_splits(config['data_path'])
        if train_X.empty:
            logging.error("Gagal membuat pemisahan data. Membatalkan benchmark.")
            return
    except FileNotFoundError:
        logging.error(f"File data tidak ditemukan di '{config['data_path']}'. Membatalkan.")
        return

    env_params = {
        'window_size': config['window_size'],
        'bet_percentages': config['bet_percentages'],
        'loss_penalty_multiplier': config['loss_penalty_multiplier'],
        'win_bonus': config['win_bonus'],
        'time_decay_penalty': config['time_decay_penalty'],
        'transaction_cost': config['transaction_cost']
    }
    env = TradingEnv(features_df=train_X, targets_df=train_y, **env_params)
    
    n_actions = env.action_space.n
    features_per_step = env.features_per_step
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logging.info(f"Menggunakan perangkat: {device}")

    policy_net = GRU_DQN(features_per_step, n_actions, config['window_size'], hyperparams['hidden_size'], hyperparams['dropout_rate']).to(device)
    target_net = GRU_DQN(features_per_step, n_actions, config['window_size'], hyperparams['hidden_size'], hyperparams['dropout_rate']).to(device)
    target_net.load_state_dict(policy_net.state_dict())
    target_net.eval()

    optimizer = optim.AdamW(policy_net.parameters(), lr=hyperparams['lr'])
    memory = PrioritizedReplayMemory(config['memory_size'])
    
    steps_done = 0

    # --- 2. Loop Benchmarking ---
    logging.info("Memulai loop benchmarking...")
    start_time = time.time()

    for i_episode in range(args.num_episodes_to_profile):
        state, _ = env.reset()
        state = torch.tensor(state, dtype=torch.float32, device=device).unsqueeze(0)
        done = False
        while not done:
            sample = random.random()
            eps_threshold = config['eps_end'] + (config['eps_start'] - config['eps_end']) * math.exp(-1. * steps_done / hyperparams['eps_decay'])
            steps_done += 1
            
            if sample > eps_threshold:
                with torch.no_grad():
                    action = policy_net(state).max(1)[1].view(1, 1)
            else:
                action = torch.tensor([[env.action_space.sample()]], device=device, dtype=torch.long)
            
            observation, reward, terminated, truncated, _ = env.step(action.item())
            reward = torch.tensor([reward], device=device, dtype=torch.float32)
            done = terminated or truncated
            next_state = None if done else torch.tensor(observation, dtype=torch.float32, device=device).unsqueeze(0)
            
            with torch.no_grad():
                current_q = policy_net(state).gather(1, action)
                next_q = target_net(next_state).max(1)[0].unsqueeze(1) if next_state is not None else torch.tensor([[0.0]], device=device)
                expected_q = reward + (hyperparams['gamma'] * next_q)
                error = abs(current_q - expected_q).item()
            
            memory.push(error, state, action, next_state, reward)
            state = next_state
            
            optimize_model(policy_net, target_net, memory, optimizer, hyperparams['batch_size'], hyperparams['gamma'], device)
        
        if (i_episode + 1) % 5 == 0:
            logging.info(f"Episode benchmark {i_episode + 1}/{args.num_episodes_to_profile} selesai.")

    end_time = time.time()
    logging.info("Loop benchmarking selesai.")

    # --- 3. Kalkulasi dan Output ---
    total_benchmark_time = end_time - start_time
    avg_time_per_episode = total_benchmark_time / args.num_episodes_to_profile
    
    estimated_total_time = avg_time_per_episode * args.total_episodes
    
    # Estimasi untuk Hyperparameter Search
    n_trials = config.get('n_trials', 50)
    episodes_per_trial = config.get('num_episodes_trial', 50)
    estimated_hpt_time = avg_time_per_episode * episodes_per_trial * n_trials

    print("\n" + "="*50)
    print("--- Laporan Estimasi Waktu Training ---")
    print("="*50)
    print(f"Episode untuk Profiling: {args.num_episodes_to_profile}")
    print(f"Total Waktu Profiling:   {format_time(total_benchmark_time)}")
    print(f"Waktu Rata-rata/Episode: {avg_time_per_episode:.2f} detik")
    print("-"*50)
    print(f"Estimasi Waktu Training Penuh ({args.total_episodes} episode):")
    print(f"==> {format_time(estimated_total_time)}")
    print("-"*50)
    print(f"Estimasi Waktu Hyperparameter Search ({n_trials} trial @ {episodes_per_trial} episode):")
    print(f"==> {format_time(estimated_hpt_time)}")
    print("="*50)
    print("\nCara Menggunakan:")
    print("python estimate_training_time.py --num_episodes_to_profile 20 --total_episodes 1000")
    print("\nCatatan: Estimasi ini mengasumsikan beban kerja yang konsisten per episode.")
    print("Waktu sebenarnya dapat bervariasi tergantung pada panjang episode dan faktor sistem lainnya.")


if __name__ == '__main__':
    main()