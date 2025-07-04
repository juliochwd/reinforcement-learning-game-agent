import os
import re
import shutil
import logging
from src.utils.model_helpers import load_config

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def find_best_candidate_model(model_dir):
    """
    Finds the candidate model with the highest reward from its filename.

    Args:
        model_dir (str): The directory where candidate models are stored.

    Returns:
        str: The path to the best candidate model file, or None if no candidates are found.
    """
    # Regex to find candidate files and extract the reward score
    candidate_regex = re.compile(r"candidate_reward_(-?\d+\.\d+)_(\d{8}-\d{6})\.pth")
    
    best_model_path = None
    highest_reward = -float('inf')

    logging.info(f"Scanning directory '{model_dir}' for candidate models...")

    if not os.path.isdir(model_dir):
        logging.warning(f"Model directory '{model_dir}' does not exist. No models to promote.")
        return None

    for filename in os.listdir(model_dir):
        match = candidate_regex.match(filename)
        if match:
            reward = float(match.group(1))
            file_path = os.path.join(model_dir, filename)
            logging.info(f"Found candidate: {filename} (Reward: {reward:.4f})")
            
            if reward > highest_reward:
                highest_reward = reward
                best_model_path = file_path

    if best_model_path:
        logging.info(f"Best candidate found: {os.path.basename(best_model_path)} with reward {highest_reward:.4f}")
    else:
        logging.warning("No candidate models found to promote.")

    return best_model_path

def main():
    """
    Main function to find the best candidate model and promote it to be the
    official best model by copying it.
    """
    logging.info("--- Starting Model Promotion Process ---")
    config = load_config()
    model_dir = config.get('model_dir', 'models/')
    final_model_name = config.get('best_model_name', 'sac_model.pth')
    
    best_candidate_path = find_best_candidate_model(model_dir)
    
    if best_candidate_path:
        final_model_path = os.path.join(model_dir, final_model_name)
        try:
            shutil.copy(best_candidate_path, final_model_path)
            logging.info(f"Successfully promoted best candidate to '{final_model_path}'")
        except Exception as e:
            logging.error(f"Failed to copy the best model. Error: {e}")
    else:
        logging.info("No model was promoted.")

if __name__ == "__main__":
    main()
