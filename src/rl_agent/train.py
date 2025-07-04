import torch
import torch.optim as optim
import torch.nn.functional as F
import random
import numpy as np
import logging
import os
import time
from datetime import datetime
import optuna
import pandas as pd
import joblib
from sklearn.preprocessing import MinMaxScaler

# --- Path setup ---
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import prepare_data_splits
from utils.model_helpers import load_config, create_environment
from utils.per import PrioritizedReplayMemory, Transition

# --- SAC Specific Imports ---
from rl_agent.model import ActorCriticSAC_GRU

def train(
    lr=3e-4,
    gamma=0.99,
    hidden_size=256,
    dropout_rate=0.2,
    batch_size=256,
    buffer_size=1_000_000,
    tau=0.005,  # For soft target updates
    alpha=0.2,  # Initial entropy coefficient
    autotune_alpha=True,
    total_timesteps=100_000,
    learning_starts=5000,
    eval_freq=5000,
    early_stopping_patience=5,
    early_stopping_threshold=0.01,
    save_model=True,
    optuna_trial=None,
    preprocessed_data=None
):
    """
    Trains the SAC-Discrete model.
    Can accept preprocessed data to speed up HPT.
    """
    config = load_config()
    logging.info("Starting SAC-Discrete training.")

    # --- Path Handling: Define paths that are always needed ---
    local_model_dir = config['model_dir']
    os.makedirs(local_model_dir, exist_ok=True)

    if preprocessed_data:
        logging.info("Using preprocessed data.")
        # When data is preprocessed, we still need to handle the scaler
        train_X_unscaled, train_y, val_X_unscaled, val_y = preprocessed_data
    else:
        logging.info("Loading and preprocessing data...")
        # Data will be loaded inside the try block

    # --- Data Loading and Processing ---
    try:
        if not preprocessed_data:
            # 1. Get unscaled data splits if not provided
            local_data_path = config['data_path']
            train_X_unscaled, train_y, val_X_unscaled, val_y, _, _ = prepare_data_splits(
                data_path=local_data_path
            )
        
        # 2. Handle the scaler lifecycle here
        scaler = MinMaxScaler()
        logging.info("Fitting scaler ONLY on training data...")
        train_X_scaled_np = scaler.fit_transform(train_X_unscaled)
        train_X = pd.DataFrame(train_X_scaled_np, columns=train_X_unscaled.columns, index=train_X_unscaled.index)
        
        # 3. Save the fitted scaler
        scaler_path = os.path.join(local_model_dir, config['scaler_name'])
        joblib.dump(scaler, scaler_path)
        logging.info(f"Fitted feature scaler saved to: {scaler_path}")

        # 4. Transform validation data with the same scaler
        logging.info("Applying scaler to validation data...")
        val_X_scaled_np = scaler.transform(val_X_unscaled)
        val_X = pd.DataFrame(val_X_scaled_np, columns=val_X_unscaled.columns, index=val_X_unscaled.index)

    except FileNotFoundError:
        logging.error(f"Data file not found at '{config['data_path']}'. Aborting.")
        return -float('inf')

    # --- Environment, Device, and Model Setup ---
    env = create_environment(train_X, train_y, config)
    val_env = create_environment(val_X, val_y, config)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    n_actions = env.action_space.n
    features_per_step = env.features_per_step
    window_size = config['window_size']

    agent = ActorCriticSAC_GRU(features_per_step, n_actions, window_size, hidden_size, dropout_rate).to(device)
    critic_target = ActorCriticSAC_GRU(features_per_step, n_actions, window_size, hidden_size, dropout_rate).to(device)
    critic_target.load_state_dict(agent.state_dict())
    critic_target.eval()

    actor_optimizer = optim.Adam(agent.actor_head.parameters(), lr=lr)
    critic_optimizer = optim.Adam(list(agent.critic1_head.parameters()) + list(agent.critic2_head.parameters()), lr=lr)

    # --- Entropy Tuning ---
    if autotune_alpha:
        target_entropy = -torch.log(torch.tensor(1.0 / n_actions)).item()
        log_alpha = torch.zeros(1, requires_grad=True, device=device)
        alpha_optimizer = optim.Adam([log_alpha], lr=lr)
    else:
        log_alpha = torch.log(torch.tensor(alpha, device=device))

    # --- Replay Buffer ---
    replay_buffer = PrioritizedReplayMemory(buffer_size)

    # --- Training Loop ---
    state, _ = env.reset()
    global_step = 0
    start_time = time.time()
    best_validation_reward = -float('inf')
    best_model_state = None
    epochs_no_improve = 0

    while global_step < total_timesteps:
        global_step += 1
        
        if global_step < learning_starts:
            action = env.action_space.sample()
        else:
            action = agent.get_action(state, device)

        next_state, reward, terminated, truncated, _ = env.step(action)
        done = terminated or truncated
        
        # For PER, we need an initial error to push. We can calculate it.
        with torch.no_grad():
            state_tensor = torch.tensor(state, dtype=torch.float32, device=device).unsqueeze(0)
            action_tensor = torch.tensor([action], dtype=torch.long, device=device).unsqueeze(1)
            
            _, q1_pred, q2_pred = agent(state_tensor)
            current_q = torch.min(q1_pred, q2_pred).gather(1, action_tensor)

            next_state_tensor = torch.tensor(next_state, dtype=torch.float32, device=device).unsqueeze(0)
            next_policy_dist, next_q1_target, next_q2_target = critic_target(next_state_tensor)
            min_next_q_target = torch.min(next_q1_target, next_q2_target)
            next_action_probs = next_policy_dist.probs
            next_log_action_probs = next_policy_dist.logits
            v_next = (next_action_probs * (min_next_q_target - log_alpha.exp() * next_log_action_probs)).sum(dim=1, keepdim=True)
            
            q_target = torch.tensor([reward], device=device) + (1.0 - done) * gamma * v_next
            
            td_error = F.l1_loss(current_q, q_target).item()

        replay_buffer.push(td_error, state, action, reward, next_state, done)
        
        state = next_state
        if done:
            state, _ = env.reset()

        if len(replay_buffer) < batch_size or global_step < learning_starts:
            continue

        # --- Sample from buffer and prepare batch ---
        transitions, idxs, is_weights = replay_buffer.sample(batch_size)
        # Correctly unpack the batch of transitions
        batch = Transition(*zip(*transitions))
        
        states = torch.tensor(np.array(batch.state), dtype=torch.float32, device=device)
        actions = torch.tensor(np.array(batch.action), dtype=torch.long, device=device).unsqueeze(1)
        rewards = torch.tensor(np.array(batch.reward), dtype=torch.float32, device=device).unsqueeze(1)
        next_states = torch.tensor(np.array(batch.next_state), dtype=torch.float32, device=device)
        dones = torch.tensor(np.array(batch.done), dtype=torch.float32, device=device).unsqueeze(1)
        is_weights = torch.tensor(is_weights, dtype=torch.float32, device=device).unsqueeze(1)

        # --- Critic Loss ---
        with torch.no_grad():
            next_policy_dist, next_q1_target, next_q2_target = critic_target(next_states)
            min_next_q_target = torch.min(next_q1_target, next_q2_target)
            
            # We need action probabilities for the expectation
            next_action_probs = next_policy_dist.probs
            next_log_action_probs = next_policy_dist.logits # Using logits is more stable
            
            v_next = (next_action_probs * (min_next_q_target - log_alpha.exp() * next_log_action_probs)).sum(dim=1, keepdim=True)
            q_target = rewards + (1.0 - dones) * gamma * v_next

        _, q1_pred, q2_pred = agent(states)
        q1_pred = q1_pred.gather(1, actions)
        q2_pred = q2_pred.gather(1, actions)
        
        # Calculate TD errors for updating priorities
        td_errors = (torch.abs(torch.min(q1_pred, q2_pred) - q_target)).detach()

        # Apply importance sampling weights to the loss
        critic_loss1 = F.mse_loss(q1_pred, q_target, reduction='none')
        critic_loss2 = F.mse_loss(q2_pred, q_target, reduction='none')
        critic_loss = ((critic_loss1 + critic_loss2) * is_weights).mean()
        
        critic_optimizer.zero_grad()
        critic_loss.backward()
        critic_optimizer.step()

        # --- Actor and Alpha Loss ---
        policy_dist, q1_pred_policy, q2_pred_policy = agent(states)
        min_q_pred_policy = torch.min(q1_pred_policy, q2_pred_policy)
        
        # Advantage Normalization (Best Practice)
        # We treat the Q-values as advantages and normalize them before the policy update.
        advantages = min_q_pred_policy.detach()
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

        action_probs = policy_dist.probs
        log_action_probs = policy_dist.logits

        actor_loss = (action_probs * (log_alpha.exp().detach() * log_action_probs - advantages)).mean()
        
        actor_optimizer.zero_grad()
        actor_loss.backward()
        actor_optimizer.step()

        # Update priorities in the replay buffer
        for i in range(batch_size):
            replay_buffer.update(idxs[i], td_errors[i].item())

        if autotune_alpha:
            alpha_loss = -(log_alpha * (log_action_probs + target_entropy).detach()).mean()
            alpha_optimizer.zero_grad()
            alpha_loss.backward()
            alpha_optimizer.step()
            alpha = log_alpha.exp().item()

        # --- LOG DIAGNOSTIK ---
        if global_step % 2000 == 0: # Log setiap 2000 langkah
            logging.debug(f"TRAIN_CONSUME (Step: {global_step}): "
                          f"Sampled Rewards (Min/Mean/Max): {rewards.min():.4f}/{rewards.mean():.4f}/{rewards.max():.4f}, "
                          f"Q-Targets (Min/Mean/Max): {q_target.min():.4f}/{q_target.mean():.4f}/{q_target.max():.4f}, "
                          f"TD-Errors (Min/Mean/Max): {td_errors.min():.4f}/{td_errors.mean():.4f}/{td_errors.max():.4f}")
        # --- AKHIR LOG DIAGNOSTIK ---

        # --- Soft Update Target Network ---
        for target_param, param in zip(critic_target.parameters(), agent.parameters()):
            target_param.data.copy_(tau * param.data + (1.0 - tau) * target_param.data)

        if global_step % eval_freq == 0 and global_step > 0:
            sps = int(global_step / (time.time() - start_time))
            
            # --- Evaluation Phase ---
            agent.eval()
            val_state, _ = val_env.reset()
            val_done = False
            while not val_done:
                val_action = agent.get_action(val_state, device)
                val_state, _, val_terminated, val_truncated, _ = val_env.step(val_action)
                val_done = val_terminated or val_truncated
            
            current_val_reward = val_env.calculate_episode_sharpe()
            logging.info(f"--- Step: {global_step}/{total_timesteps} | SPS: {sps} | Val Consistency Score: {current_val_reward:.4f} | Best: {best_validation_reward:.4f} ---")

            # Check for improvement
            if current_val_reward > best_validation_reward + early_stopping_threshold:
                best_validation_reward = current_val_reward
                epochs_no_improve = 0
                if save_model:
                    # --- Anti-Race Condition Save Logic ---
                    # Save candidate models with unique names to avoid overwrites.
                    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                    model_filename = f"candidate_reward_{current_val_reward:.4f}_{timestamp}.pth"
                    model_path = os.path.join(local_model_dir, model_filename)
                    
                    architecture_params = {
                        'features_per_step': features_per_step, 'n_actions': n_actions,
                        'window_size': window_size, 'hidden_size': hidden_size,
                        'dropout_rate': dropout_rate
                    }
                    
                    torch.save({
                        'model_state_dict': agent.state_dict(),
                        'architecture_params': architecture_params
                    }, model_path)
                    logging.info(f"*** New candidate model saved to {model_path} with reward {current_val_reward:.4f} ***")
            else:
                epochs_no_improve += 1
            
            agent.train()

            # Early stopping check
            if epochs_no_improve >= early_stopping_patience:
                logging.info(f"Early stopping triggered after {epochs_no_improve} evaluations without improvement.")
                break
            
            # Pruning check for Optuna
            if optuna_trial:
                optuna_trial.report(current_val_reward, global_step)
                if optuna_trial.should_prune():
                    logging.info(f"Optuna trial {optuna_trial.number} pruned at step {global_step}.")
                    # Return a value that Optuna understands as pruned.
                    raise optuna.TrialPruned()


    # The final model is no longer saved here to prevent race conditions.
    # Use the 'promote_best_model.py' script to select the best candidate after all training runs are complete.
    env.close()
    val_env.close()
    
    # If the trial was pruned, this part won't be reached for that trial.
    # For completed trials, return the best reward found.
    return best_validation_reward
