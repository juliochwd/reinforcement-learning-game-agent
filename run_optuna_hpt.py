import optuna
import logging
import yaml
from src.rl_agent.train import train

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load configuration
with open("config.yaml", 'r') as f:
    config = yaml.safe_load(f)

def objective(trial):
    """
    Defines the objective function for Optuna to optimize.
    A trial represents a single call to this function with a specific set of hyperparameters.
    """
    # Define the hyperparameter search space from config
    hp_config = config['hyperparameters']
    lr = trial.suggest_float("lr", hp_config['lr']['low'], hp_config['lr']['high'], log=True)
    gamma = trial.suggest_float("gamma", hp_config['gamma']['low'], hp_config['gamma']['high'])
    hidden_size = trial.suggest_categorical("hidden_size", hp_config['hidden_size'])
    dropout_rate = trial.suggest_float("dropout_rate", hp_config['dropout_rate']['low'], hp_config['dropout_rate']['high'])
    batch_size = trial.suggest_categorical("batch_size", hp_config['batch_size'])
    eps_decay = trial.suggest_int("eps_decay", hp_config['eps_decay']['low'], hp_config['eps_decay']['high'])

    # Use number of episodes for HPT from config
    num_episodes = config['num_episodes_trial']

    logging.info(f"Starting trial {trial.number} with params: lr={lr:.6f}, gamma={gamma:.4f}, hidden_size={hidden_size}, dropout_rate={dropout_rate:.4f}, batch_size={batch_size}, eps_decay={eps_decay}")

    # Call the training function with the suggested hyperparameters.
    # We set save_model=False because we only care about the validation score during HPT.
    # The final model will be trained separately with the best hyperparameters.
    validation_reward = train(
        lr=lr,
        gamma=gamma,
        hidden_size=hidden_size,
        dropout_rate=dropout_rate,
        batch_size=batch_size,
        eps_decay=eps_decay,
        num_episodes=num_episodes,
        save_model=False  # Don't save intermediate models during HPT
    )

    # Optuna will try to maximize this value
    return validation_reward

def run_hyperparameter_tuning():
    """
    Runs the Optuna hyperparameter tuning study and returns the best parameters.
    """
    # Create a study object. We want to maximize the validation_reward.
    # The pruner helps to stop unpromising trials early.
    pruner = optuna.pruners.MedianPruner()
    study = optuna.create_study(direction="maximize", pruner=pruner)

    # Start the optimization using n_trials from config
    try:
        study.optimize(objective, n_trials=config['n_trials'])
    except KeyboardInterrupt:
        logging.info("Optimization stopped manually.")
    except Exception as e:
        logging.error(f"An error occurred during optimization: {e}")
        return None # Return None if optimization fails

    # --- Print and Return Results ---
    logging.info("\n" + "="*40)
    logging.info("Optuna Hyperparameter Tuning Finished")
    logging.info("="*40)
    logging.info(f"Number of finished trials: {len(study.trials)}")

    best_trial = study.best_trial
    logging.info(f"Best trial value (Validation Reward): {best_trial.value:.4f}")
    logging.info("Best Parameters found:")
    for key, value in best_trial.params.items():
        logging.info(f"    {key}: {value}")
    logging.info("="*40)

    return best_trial.params


def main():
    """
    Main function to run the HPT process and print the results.
    This part is for when the script is run directly.
    """
    best_params = run_hyperparameter_tuning()
    if best_params:
        logging.info("\n" + "="*40)
        logging.info("Hyperparameter tuning complete. Starting final model training.")
        logging.info(f"Best parameters found: {best_params}")
        logging.info("="*40)

        # Train the final model with the best parameters
        final_episodes = config.get('num_episodes_final', 100)
        train(
            **best_params,
            num_episodes=final_episodes,
            save_model=True
        )
        logging.info("Final model training finished.")

if __name__ == "__main__":
    main()