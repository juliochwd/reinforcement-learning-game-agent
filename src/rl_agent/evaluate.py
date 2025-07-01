import torch
import pandas as pd
import logging
import yaml
import os
import matplotlib.pyplot as plt
import numpy as np
import joblib

# --- Path setup for utils ---
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import prepare_data_splits
from src.utils.model_helpers import load_config, load_model_robust, create_environment

def main():
    """
    Main function to evaluate the best trained model on the unseen test set.
    """
    logging.info("--- Starting Final Evaluation on Test Set ---")
    config = load_config()

    # --- Path Handling for Local Execution ---
    local_data_path = config['data_path']
    local_model_dir = config['model_dir']
    local_log_dir = config['log_dir']
    os.makedirs(local_model_dir, exist_ok=True)
    os.makedirs(local_log_dir, exist_ok=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    model_path = os.path.join(local_model_dir, "sac_model.pth") # Use the new model name
    
    policy_net = load_model_robust(model_path, device)
    if policy_net is None:
        logging.error(f"Failed to load model from {model_path}. Aborting evaluation.")
        return

    try:
        # 1. Get unscaled data splits
        _, _, _, _, test_X_unscaled, test_y = prepare_data_splits(local_data_path)
        if test_X_unscaled.empty:
            logging.error("Test data is empty. Aborting evaluation.")
            return
        
        # 2. Load the scaler that was saved during training
        scaler_path = os.path.join(local_model_dir, config['scaler_name'])
        scaler = joblib.load(scaler_path)
        
        # 3. Transform the test data using the loaded scaler
        test_X = pd.DataFrame(scaler.transform(test_X_unscaled), columns=test_X_unscaled.columns, index=test_X_unscaled.index)

    except FileNotFoundError as e:
        logging.error(f"Data or scaler file not found. Please run training first. Error: {e}")
        return

    test_env = create_environment(test_X, test_y, config)
    bet_percentages = config['bet_percentages']
    
    actions_taken = []
    rewards_over_time = []
    correct_bets = 0
    total_bets = 0

    state, _ = test_env.reset()
    done = False
    total_steps = len(test_env.features_df) - test_env.window_size
    log_interval = max(1, total_steps // 20)

    while not done:
        with torch.no_grad():
            action = policy_net.get_action(state, device)
        
        actions_taken.append(action)
        observation, reward, terminated, truncated, _ = test_env.step(action)
        
        if action > 0: # Any action other than Hold is a bet
            total_bets += 1
            if reward > 0: # A positive reward means a winning bet
                correct_bets += 1
        
        rewards_over_time.append(test_env.total_reward)
        state = observation
        done = terminated or truncated

        current_step = test_env.current_step
        if current_step % log_interval == 0 or done:
            logging.info(f"Evaluating step {current_step}/{total_steps}")

    total_reward = test_env.total_reward
    win_rate = (correct_bets / total_bets) * 100 if total_bets > 0 else 0

    action_labels = ['Hold'] + \
                    [f'Small({p*100:.1f}%)' for p in bet_percentages] + \
                    [f'Big({p*100:.1f}%)' for p in bet_percentages]
    action_counts = pd.Series(actions_taken).value_counts().reindex(range(len(action_labels)), fill_value=0)
    action_dist = {label: action_counts.get(i, 0) for i, label in enumerate(action_labels)}

    logging.info("--- Evaluation Finished ---")
    logging.info(f"Final Balance on Test Set: {test_env.balance:,.2f}")
    logging.info(f"Total Profit on Test Set: {total_reward:,.2f}")
    if total_bets > 0:
        logging.info(f"Win Rate on Bets: {win_rate:.2f}% ({correct_bets}/{total_bets})")
    else:
        logging.info("Win Rate on Bets: N/A (No bets were made)")
    logging.info(f"Action Distribution on Test Set: {action_dist}")

    # --- Plotting ---
    if total_bets > 0:
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), gridspec_kw={'height_ratios': [1, 2]})

        num_bet_levels = len(bet_percentages)
        colors = ['gray'] + ['blue'] * num_bet_levels + ['green'] * num_bet_levels
        ax1.bar(action_dist.keys(), action_dist.values(), color=colors)
        ax1.set_title('Action Distribution on Test Set')
        ax1.set_ylabel('Frequency')
        ax1.tick_params(axis='x', rotation=45)
        
        ax2.plot(rewards_over_time, label='Cumulative Reward')
        ax2.set_title('Cumulative Reward During Test Evaluation')
        ax2.set_xlabel('Step')
        ax2.set_ylabel('Total Reward')
        ax2.grid(True)
        
        plt.tight_layout()
        plot_path = os.path.join(local_log_dir, 'test_evaluation_summary.png')
        plt.savefig(plot_path)
        logging.info(f"Test evaluation summary plot saved to {plot_path}")
        plt.close()
    else:
        logging.info("Skipping plot generation as no actions were taken.")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    main()
