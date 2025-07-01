import pytest
import torch
import pandas as pd
import numpy as np
import sys
import os
import yaml
import joblib

# --- Path Setup ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from src.utils import prepare_data_splits
from src.utils.model_helpers import load_model_robust
from src.rl_agent.train import train as train_sac
from src.rl_agent.model import ActorCriticSAC_GRU

# --- Test Fixtures ---

@pytest.fixture(scope="module")
def dummy_data_path(tmpdir_factory):
    """Creates a dummy CSV data file for testing."""
    data = {
        'Period': range(100),
        'Premium': np.random.randint(1000, 9999, 100)
    }
    df = pd.DataFrame(data)
    path = tmpdir_factory.mktemp("data").join("dummy_data.csv")
    df.to_csv(path, index=False)
    return str(path)

@pytest.fixture(scope="module")
def dummy_config(tmpdir_factory, dummy_data_path):
    """Creates a dummy config dictionary for testing."""
    model_dir = tmpdir_factory.mktemp("models")
    return {
        'data_path': dummy_data_path,
        'model_dir': str(model_dir),
        'scaler_name': 'test_scaler.joblib',
        'best_model_name': 'test_sac_model.pth',
        'window_size': 5,
        'bet_percentages': [0.1],
        'loss_penalty_multiplier': 1.5,
        'win_bonus': 0.01,
        'time_decay_penalty': 0.001,
        'transaction_cost': 0.0
    }

# --- Test Cases ---

def test_data_pipeline(dummy_data_path, tmpdir):
    """
    Tests the data splitting functionality.
    Note: This test no longer checks for the scaler, as that responsibility
    has been moved to the training and evaluation scripts.
    """
    train_X, train_y, val_X, val_y, test_X, test_y = prepare_data_splits(
        data_path=dummy_data_path,
        train_ratio=0.7,
        val_ratio=0.15
    )
    
    # Check if all splits are created and are pandas DataFrames
    assert isinstance(train_X, pd.DataFrame)
    assert isinstance(val_X, pd.DataFrame)
    assert isinstance(test_X, pd.DataFrame)
    assert len(train_X) > 0
    assert len(val_X) > 0
    assert len(test_X) > 0

def test_short_training_run(dummy_config):
    """
    Tests if the SAC training loop can run for a few steps without crashing.
    This is a core integration test.
    """
    # Override the default config loader to use our dummy config
    def mock_load_config():
        return dummy_config

    # Monkeypatch the load_config function in the train module
    from src.rl_agent import train
    train.load_config = mock_load_config
    
    try:
        # Run training for a very short duration
        final_reward = train_sac(
            total_timesteps=20,
            learning_starts=10,
            batch_size=4,
            eval_freq=15, # Ensure at least one evaluation
            save_model=True # Ensure model saving is tested
        )
        # The test passes if it completes without errors
        assert isinstance(final_reward, float)
    except Exception as e:
        pytest.fail(f"Short training run failed with an exception: {e}")

def test_model_save_and_load(dummy_config):
    """
    Tests if a trained model can be saved and then loaded back correctly.
    """
    # --- Setup: Run a short training to generate a model file ---
    def mock_load_config():
        return dummy_config
    
    from src.rl_agent import train
    train.load_config = mock_load_config
    
    # Adjust parameters to ensure the evaluation loop runs at least once
    train_sac(
        total_timesteps=25, 
        learning_starts=5, 
        batch_size=4, 
        eval_freq=15, # This will trigger an evaluation at step 15
        save_model=True
    )
    
    model_path = os.path.join(dummy_config['model_dir'], dummy_config['best_model_name'])
    assert os.path.exists(model_path), "Model file was not created after training."

    # --- Test: Load the model back ---
    device = torch.device("cpu")
    loaded_model = load_model_robust(model_path, device)
    
    assert loaded_model is not None, "Failed to load the saved model."
    # Use string comparison for class name to avoid import path issues in pytest
    assert loaded_model.__class__.__name__ == 'ActorCriticSAC_GRU', "Loaded model is not of the correct class."
    
    # Check if it can perform a forward pass
    try:
        dummy_state = torch.randn(1, dummy_config['window_size'], 20) # Assuming feature count
        # The number of features is dynamic, let's get it from the loaded model
        n_features = loaded_model.features_per_step
        dummy_state = torch.randn(1, dummy_config['window_size'], n_features)
        
        loaded_model.get_action(dummy_state, device)
    except Exception as e:
        pytest.fail(f"Forward pass on loaded model failed: {e}")
