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
import argparse
import tempfile

# --- Path setup for utils ---
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import prepare_data_splits
from utils import gcs_utils

# --- Replay Memory (Now Prioritized) ---
from src.utils.per import PrioritizedReplayMemory, Transition
from src.utils.model_helpers import load_config, create_environment
from rl_agent.model import GRU_DQN

def optimize_model(policy_net, target_net, memory, optimizer, batch_size, gamma, device):
    """
    Performs one step of optimization on the policy network.
    This function integrates Double DQN and Prioritized Experience Replay.
    """
    if len(memory) < batch_size:
        return  # Not enough samples in memory to train

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
    for i in range(batch_size):
        memory.update(idxs[i], errors[i][0])

    weighted_loss = (loss * is_weights.unsqueeze(1)).mean()
    optimizer.zero_grad()
    weighted_loss.backward()
    torch.nn.utils.clip_grad_value_(policy_net.parameters(), 100)
    optimizer.step()

def train(
    lr=1e-4,
    gamma=0.99,
    hidden_size=128,
    dropout_rate=0.2,
    batch_size=32,
    eps_decay=2000,
    num_episodes=100,
    save_model=True
):
    """
    Trains the DQN model with given hyperparameters and returns the best validation reward.
    This function is now cloud-aware and can handle GCS paths.
    """
    config = load_config()
    logging.info("Starting training with Dueling, Double DQN, and Prioritized Experience Replay.")

    with tempfile.TemporaryDirectory() as temp_dir:
        # --- GCS Path Handling ---
        original_data_path = config['data_path']
        original_model_dir = config['model_dir']
        
        local_data_path = temp_dir if gcs_utils.is_gcs_path(original_data_path) else original_data_path
        local_model_dir = os.path.join(temp_dir, 'models') if gcs_utils.is_gcs_path(original_model_dir) else original_model_dir
        
        os.makedirs(local_model_dir, exist_ok=True)

        if gcs_utils.is_gcs_path(original_data_path):
            logging.info(f"Downloading data from {original_data_path} to {local_data_path}...")
            gcs_utils.download_from_gcs(original_data_path, local_data_path)
        
        # --- Training Logic (using local paths) ---
        final_hyperparams = {
            'lr': lr, 'gamma': gamma, 'hidden_size': hidden_size,
            'dropout_rate': dropout_rate, 'batch_size': batch_size, 'eps_decay': eps_decay
        }
        logging.info("Using Hyperparameters: %s", final_hyperparams)

        try:
            # Use local paths for processing
            data_file = local_data_path
            scaler_path = os.path.join(local_model_dir, config['scaler_name'])
            
            train_X, train_y, val_X, val_y, _, _ = prepare_data_splits(
                data_path=data_file,
                scaler_path=scaler_path
            )
            if train_X.empty or val_X.empty:
                logging.error("Failed to create data splits. Aborting training.")
                return -float('inf')
        except FileNotFoundError:
            logging.error(f"Data file not found at '{data_file}'. Aborting.")
            return -float('inf')

        train_env = create_environment(train_X, train_y, config)
        val_env = create_environment(val_X, val_y, config)
        
        n_actions = train_env.action_space.n
        features_per_step = train_env.features_per_step
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        policy_net = GRU_DQN(features_per_step, n_actions, config['window_size'], final_hyperparams['hidden_size'], final_hyperparams['dropout_rate']).to(device)
        target_net = GRU_DQN(features_per_step, n_actions, config['window_size'], final_hyperparams['hidden_size'], final_hyperparams['dropout_rate']).to(device)
        target_net.load_state_dict(policy_net.state_dict())
        target_net.eval()

        optimizer = optim.AdamW(policy_net.parameters(), lr=final_hyperparams['lr'])
        memory = PrioritizedReplayMemory(config['memory_size'])
        
        best_validation_reward = -float('inf')
        epochs_no_improve = 0
        best_model_state = None
        TARGET_UPDATE = config.get('target_update_frequency', 10)
        steps_done = 0

        for i_episode in range(num_episodes):
            policy_net.train()
            state, _ = train_env.reset()
            state = torch.tensor(state, dtype=torch.float32, device=device).unsqueeze(0)
            done = False
            while not done:
                sample = random.random()
                eps_threshold = config['eps_end'] + (config['eps_start'] - config['eps_end']) * math.exp(-1. * steps_done / final_hyperparams['eps_decay'])
                steps_done += 1
                
                if sample > eps_threshold:
                    with torch.no_grad():
                        action = policy_net(state).max(1)[1].view(1, 1)
                else:
                    action = torch.tensor([[train_env.action_space.sample()]], device=device, dtype=torch.long)
                
                observation, reward, terminated, truncated, _ = train_env.step(action.item())
                reward = torch.tensor([reward], device=device, dtype=torch.float32)
                done = terminated or truncated
                next_state = None if done else torch.tensor(observation, dtype=torch.float32, device=device).unsqueeze(0)
                
                with torch.no_grad():
                    current_q = policy_net(state).gather(1, action)
                    next_q = target_net(next_state).max(1)[0].unsqueeze(1) if next_state is not None else torch.tensor([[0.0]], device=device)
                    expected_q = reward + (final_hyperparams['gamma'] * next_q)
                    error = abs(current_q - expected_q).item()
                
                memory.push(error, state, action, next_state, reward)
                state = next_state
                
                optimize_model(policy_net, target_net, memory, optimizer, final_hyperparams['batch_size'], final_hyperparams['gamma'], device)

            if (i_episode + 1) % TARGET_UPDATE == 0:
                target_net.load_state_dict(policy_net.state_dict())

            if (i_episode + 1) % config['eval_every'] == 0:
                policy_net.eval()
                val_state, _ = val_env.reset()
                val_done = False
                while not val_done:
                    val_state_tensor = torch.tensor(val_state, dtype=torch.float32, device=device).unsqueeze(0)
                    with torch.no_grad():
                        val_action = policy_net(val_state_tensor).max(1)[1].item()
                    val_state, _, val_terminated, val_truncated, _ = val_env.step(val_action)
                    val_done = val_terminated or val_truncated
                
                current_val_reward = val_env.total_reward
                logging.info(f"--- Validation at Episode {i_episode + 1} | Reward: {current_val_reward:.2f} | Best: {best_validation_reward:.2f} ---")
                
                if current_val_reward > best_validation_reward:
                    best_validation_reward = current_val_reward
                    epochs_no_improve = 0
                    if save_model:
                        best_model_state = policy_net.state_dict().copy()
                        logging.info(f"*** New best model state captured with reward {best_validation_reward:.2f} ***")
                else:
                    epochs_no_improve += 1
                
                if epochs_no_improve >= config.get('early_stopping_patience', 5):
                    logging.info(f"Early stopping triggered after {i_episode + 1} episodes.")
                    break

        if save_model and best_model_state:
            local_model_path = os.path.join(local_model_dir, config['best_model_name'])
            
            architecture_params = {
                'features_per_step': features_per_step, 'n_actions': n_actions,
                'window_size': config['window_size'], 'hidden_size': final_hyperparams['hidden_size'],
                'dropout_rate': final_hyperparams['dropout_rate']
            }
            
            torch.save({
                'model_state_dict': best_model_state,
                'architecture_params': architecture_params
            }, local_model_path)
            
            logging.info(f"Best model saved locally to {local_model_path}")

            if gcs_utils.is_gcs_path(original_model_dir):
                logging.info(f"Uploading model artifacts from {local_model_dir} to {original_model_dir}...")
                gcs_utils.upload_to_gcs(local_model_dir, original_model_dir)
                
        elif save_model:
            logging.warning("Training finished, but no best model was saved (no improvement over initial).")

    return best_validation_reward

def main():
    """Main function to train the model with parameters from command line."""
    parser = argparse.ArgumentParser(description="Train a DQN Agent for a game.")
    parser.add_argument('--lr', type=float, default=1e-4, help='Learning rate for the optimizer.')
    parser.add_argument('--gamma', type=float, default=0.99, help='Discount factor for future rewards.')
    parser.add_argument('--hidden_size', type=int, default=128, help='Number of neurons in the hidden layer of the GRU.')
    parser.add_argument('--dropout_rate', type=float, default=0.2, help='Dropout rate for regularization.')
    parser.add_argument('--batch_size', type=int, default=32, help='Batch size for training.')
    parser.add_argument('--eps_decay', type=float, default=2000, help='Decay rate for epsilon-greedy exploration.')
    parser.add_argument('--num_episodes', type=int, default=100, help='Number of episodes to train for.')
    args = parser.parse_args()

    train(
        lr=args.lr,
        gamma=args.gamma,
        hidden_size=args.hidden_size,
        dropout_rate=args.dropout_rate,
        batch_size=args.batch_size,
        eps_decay=args.eps_decay,
        num_episodes=args.num_episodes,
        save_model=True
    )

if __name__ == '__main__':
    # Setup basic logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    main()