import optuna
from optuna.pruners import MedianPruner
import logging
import sys
import os
import time
import json
import hashlib
import argparse
import multiprocessing as mp
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.rl_agent.train import train as train_sac
from src.utils.model_helpers import load_config
from src.utils import prepare_data_splits

def objective(trial, config, search_space, preprocessed_data):
    """
    The objective function for Optuna to optimize for SAC.
    It now accepts preprocessed data to avoid reloading it in every trial.
    """
    hpt_config = config.get('sac_hyperparameters', {})
    
    # Suggest hyperparameters for SAC from the search space
    lr = trial.suggest_float('lr', search_space['lr']['low'], search_space['lr']['high'], log=True)
    gamma = trial.suggest_float('gamma', search_space['gamma']['low'], search_space['gamma']['high'])
    hidden_size = trial.suggest_categorical('hidden_size', search_space['hidden_size'])
    dropout_rate = trial.suggest_float('dropout_rate', search_space['dropout_rate']['low'], search_space['dropout_rate']['high'])
    batch_size = trial.suggest_categorical('batch_size', search_space['batch_size'])
    tau = trial.suggest_float('tau', search_space['tau']['low'], search_space['tau']['high'])
    
    total_timesteps_trial = hpt_config.get('total_timesteps_trial', 20000)

    logging.info(f"--- Starting Trial {trial.number} ---")
    
    # Run the SAC training function, passing the trial object and preprocessed data
    validation_reward = train_sac(
        lr=lr,
        gamma=gamma,
        hidden_size=hidden_size,
        dropout_rate=dropout_rate,
        batch_size=batch_size,
        tau=tau,
        total_timesteps=total_timesteps_trial,
        save_model=False,
        optuna_trial=trial,
        preprocessed_data=preprocessed_data
    )
    
    logging.info(f"--- Trial {trial.number} Finished | Validation Reward: {validation_reward} ---")
    
    return validation_reward

def main(n_jobs_override=None):
    """
    Main function to run the hyperparameter search using Optuna.
    Accepts an override for n_jobs for programmatic execution.
    """
    logging.info("--- Starting Hyperparameter Search with Optuna (with Pruning & Parallel Support) ---")
    config = load_config()
    hpt_config = config.get('sac_hyperparameters', {})
    search_space = hpt_config.get('search_space', {})
    n_trials = hpt_config.get('n_trials', 50)
    
    # Determine n_jobs: override > config > default
    if n_jobs_override is not None:
        n_jobs = n_jobs_override
    else:
        n_jobs = hpt_config.get('n_jobs', 1)
    
    logging.info(f"Executing with n_jobs = {n_jobs}")

    # --- Pre-load and process data ONCE ---
    logging.info("Preprocessing data once before starting trials...")
    try:
        # The scaler is now handled inside the train() function, so we just need the splits.
        train_X, train_y, val_X, val_y, _, _ = prepare_data_splits(
            data_path=config['data_path']
        )
        # The train function will handle scaling, so we pass the unscaled data.
        preprocessed_data = (train_X, train_y, val_X, val_y)
        logging.info("Data successfully preprocessed.")
    except Exception as e:
        logging.error(f"Failed to preprocess data. Aborting HPT. Error: {e}")
        return
    
    # --- Dynamic Study Name based on Search Space ---
    # To prevent errors when the search space changes in the config,
    # we create a unique study name based on a hash of the search space.
    search_space_str = json.dumps(search_space, sort_keys=True)
    search_space_hash = hashlib.md5(search_space_str.encode()).hexdigest()[:8]
    
    # Setup storage for parallel trials
    storage_name = "sqlite:///hpt_study.db"
    study_name = f"sac-study-{search_space_hash}"
    logging.info(f"Using study name: {study_name} (based on search space hash)")
    
    # Create a study object with a pruner and specify storage
    study = optuna.create_study(
        study_name=study_name,
        storage=storage_name,
        load_if_exists=True, # Allows continuing a previous study
        direction='maximize',
        pruner=MedianPruner(n_startup_trials=5, n_warmup_steps=hpt_config.get('eval_freq', 10000) // 2)
    )
    
    start_time = time.time()

    # --- Progress Callback ---
    def progress_callback(study, trial):
        """
        Callback to print progress after each trial.
        This is used to update the GUI when running on a VM.
        """
        # We start at 50% and go to 80% for the HPT phase
        base_progress = 50
        hpt_progress_range = 30  # (80% - 50%)
        
        # Calculate completion ratio for HPT
        completed_trials = trial.number + 1
        total_trials = n_trials
        
        # Calculate the progress within the HPT phase's allocated range
        current_hpt_progress = (completed_trials / total_trials) * hpt_progress_range
        
        # Total progress is the base + current HPT progress
        total_progress = base_progress + current_hpt_progress
        
        # Print in a format that the orchestrator can parse
        print(f"PROGRESS: {int(total_progress)}%")
        # Flush the output to ensure it's sent immediately
        sys.stdout.flush()

    # The objective function now needs the config, search_space, and data passed to it
    objective_with_args = lambda trial: objective(trial, config, search_space, preprocessed_data)

    # Start the optimization with the callback
    study.optimize(
        objective_with_args, 
        n_trials=n_trials, 
        n_jobs=n_jobs,
        callbacks=[progress_callback]
    )

    # --- Log the results ---
    total_duration = time.time() - start_time
    total_duration_formatted = time.strftime('%H:%M:%S', time.gmtime(total_duration))
    logging.info(f"--- Hyperparameter Search Finished in {total_duration_formatted} ---")
    logging.info(f"Number of finished trials: {len(study.trials)}")
    
    best_trial = study.best_trial
    logging.info("Best trial:")
    logging.info(f"  Value (Max Validation Reward): {best_trial.value:.4f}")
    
    logging.info("  Params: ")
    for key, value in best_trial.params.items():
        logging.info(f"    {key}: {value}")

    # --- Save the best parameters to a file ---
    model_dir = config.get('model_dir', 'models/')
    if not os.path.exists(model_dir):
        os.makedirs(model_dir)
        logging.info(f"Created directory: {model_dir}")

    best_params_path = os.path.join(model_dir, config.get('best_params_name', 'best_sac_params.json'))
    with open(best_params_path, 'w') as f:
        json.dump(best_trial.params, f, indent=4)
    logging.info(f"Best parameters saved to {best_params_path}")
    
    logging.info("\nTo run in parallel, execute this script in multiple terminals simultaneously.")

if __name__ == "__main__":
    # Force 'spawn' start method for multiprocessing to ensure stability on Linux/macOS,
    # especially when using libraries like PyTorch that are not fork-safe.
    try:
        mp.set_start_method('spawn', force=True)
    except RuntimeError:
        # This can happen if the context is already set. We'll log a warning.
        logging.warning("Multiprocessing context already set. Assuming it's configured correctly.")

    # Setup basic logging for direct script execution
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    parser = argparse.ArgumentParser(description="Run Optuna Hyperparameter Search for SAC.")
    parser.add_argument(
        '--n_jobs', 
        type=int, 
        default=None, 
        help='Number of parallel jobs for Optuna. Overrides config file setting.'
    )
    args = parser.parse_args()
    
    main(n_jobs_override=args.n_jobs)
