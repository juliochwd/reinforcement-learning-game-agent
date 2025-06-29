import pandas as pd
from statsmodels.sandbox.stats.runs import runstest_1samp
import yaml
import os
import logging

def load_config():
    """Loads the configuration from config.yaml."""
    # Path is relative to this script's location (src/rl_agent)
    config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config.yaml')
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config

def perform_randomness_test(file_path, column_name):
    """
    Performs the Wald-Wolfowitz runs test for randomness on a specified column.

    Args:
        file_path (str): The path to the CSV file.
        column_name (str): The name of the column to test.
    """
    try:
        # 1. Read the data
        df = pd.read_csv(file_path)
        
        if column_name not in df.columns:
            logging.error(f"Error: Column '{column_name}' not found in the file.")
            return

        data_sequence = df[column_name].map({'Big': 1, 'Small': 0}).dropna()
        
        if data_sequence.empty:
            logging.error("Error: The data sequence is empty after processing. Check the column values.")
            return

        logging.info(f"--- Menganalisis Kolom: '{column_name}' ---")
        logging.info(f"Jumlah total data poin: {len(data_sequence)}")
        logging.info(f"Jumlah 'Big' (1): {data_sequence.sum()}")
        logging.info(f"Jumlah 'Small' (0): {len(data_sequence) - data_sequence.sum()}")
        
        z_stat, p_value = runstest_1samp(data_sequence, correction=False)

        logging.info(f"--- Hasil Uji Keacakan (Wald-Wolfowitz Runs Test) ---")
        logging.info(f"Z-Statistic: {z_stat:.4f}")
        logging.info(f"P-value: {p_value:.4f}")
        
        alpha = 0.05
        if p_value < alpha:
            logging.info(f"Kesimpulan: P-value ({p_value:.4f}) < {alpha}. Hipotesis nol ditolak. Data NON-ACAK (Go).")
        else:
            logging.info(f"Kesimpulan: P-value ({p_value:.4f}) >= {alpha}. Gagal menolak hipotesis nol. Data ACAK (No-Go).")

    except FileNotFoundError:
        logging.error(f"Error: File tidak ditemukan di '{file_path}'")
    except Exception as e:
        logging.error(f"Terjadi kesalahan: {e}", exc_info=True)

def main():
    """Main function to run the randomness test."""
    config = load_config()
    # Construct the absolute path from the project root
    project_root = os.path.join(os.path.dirname(__file__), '..', '..')
    data_file = os.path.join(project_root, config['data_path'])
    
    logging.info(f"Running randomness test on: {data_file}")
    perform_randomness_test(data_file, 'Big/Small')

if __name__ == '__main__':
    # Note: This script is now part of a package.
    # To run it, use `python -m rl_agent.randomness_test` from the root directory.
    import logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    main()