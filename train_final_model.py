import logging
import json
import os
import sys

# --- Path Setup ---
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.rl_agent.train import train
from src.utils.model_helpers import load_config

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    """
    Main entry point for training the final model with the best hyperparameters
    found during the Optuna search.
    """
    config = load_config()
    model_dir = config.get('model_dir', 'models/')
    best_params_filename = config.get('best_params_name', 'best_sac_params.json')
    best_params_path = os.path.join(model_dir, best_params_filename)

    try:
        with open(best_params_path, 'r') as f:
            best_params = json.load(f)
    except FileNotFoundError:
        logging.error(f"Error: Best parameter file not found at {best_params_path}")
        logging.error("Please run the hyperparameter search first (run_hpt_local.sh).")
        return
    except json.JSONDecodeError:
        logging.error(f"Error: Could not decode JSON from {best_params_path}.")
        return

    logging.info("Starting final training with the best hyperparameters from HPT:")
    for key, value in best_params.items():
        logging.info(f"  {key.replace('_', ' ').title()}: {value}")
    
    sac_config = config.get('sac_hyperparameters', {})
    final_timesteps = sac_config.get('total_timesteps_final', 200000)
    
    # --- Load all relevant parameters from config ---
    train_params = {
        'lr': best_params['lr'],
        'gamma': best_params['gamma'],
        'hidden_size': best_params['hidden_size'],
        'dropout_rate': best_params['dropout_rate'],
        'batch_size': best_params['batch_size'],
        'tau': best_params['tau'],
        'total_timesteps': final_timesteps,
        'eval_freq': sac_config.get('eval_freq', 5000),
        'learning_starts': sac_config.get('learning_starts', 2500),
        'buffer_size': sac_config.get('buffer_size', 1_000_000),
        'early_stopping_patience': sac_config.get('early_stopping_patience', 5),
        'early_stopping_threshold': sac_config.get('early_stopping_threshold', 0.01),
        'autotune_alpha': sac_config.get('autotune_alpha', True),
        'save_model': True  # Ensure the final model is saved
    }

    logging.info("Final training parameters:")
    for key, value in train_params.items():
        logging.info(f"  {key.replace('_', ' ').title()}: {value}")

    # Call the SAC training function with the complete set of parameters
    train(**train_params)

    logging.info("Final model training complete.")

if __name__ == "__main__":
    main()
