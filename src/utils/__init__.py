import pandas as pd
import os
import logging
import joblib
from sklearn.preprocessing import MinMaxScaler
from src.features.feature_engineering import create_features

def prepare_data_splits(data_path, train_ratio=0.7, val_ratio=0.15):
    """
    Loads raw data, creates features, and performs a chronological split.
    This function NO LONGER handles scaling. It returns unscaled dataframes.
    The calling script is responsible for handling the scaler lifecycle.

    Args:
        data_path (str): Path to the raw CSV data.
        train_ratio (float): Proportion of data to use for training.
        val_ratio (float): Proportion of data to use for validation.

    Returns:
        tuple: A tuple containing (train_X, train_y, val_X, val_y, test_X, test_y).
               These are unscaled dataframes.
    """
    try:
        raw_df = pd.read_csv(data_path)
    except FileNotFoundError:
        logging.error(f"Data file not found at: {data_path}")
        raise
    
    logging.info("Creating features and targets from raw data...")
    features_df, targets_df = create_features(raw_df)
    logging.info(f"Feature creation complete. {len(features_df)} usable rows.")
    
    # Split both dataframes synchronously (chronologically)
    train_end_idx = int(len(features_df) * train_ratio)
    val_end_idx = train_end_idx + int(len(features_df) * val_ratio)
    
    train_X = features_df.iloc[:train_end_idx]
    val_X = features_df.iloc[train_end_idx:val_end_idx]
    test_X = features_df.iloc[val_end_idx:]
    
    train_y = targets_df.iloc[:train_end_idx]
    val_y = targets_df.iloc[train_end_idx:val_end_idx]
    test_y = targets_df.iloc[val_end_idx:]
    
    logging.info(f"Data split: {len(train_X)} training, {len(val_X)} validation, {len(test_X)} test samples.")
    
    return train_X, train_y, val_X, val_y, test_X, test_y
