import pytest
import torch
import pandas as pd
import numpy as np
import sys
import os
import joblib

# --- Path Setup ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.rl_agent.model import ActorCriticSAC_GRU
from src.rl_agent.decision_maker import DecisionMaker
from src.features.feature_engineering import create_features

# --- Test Fixtures ---

@pytest.fixture(scope="module")
def dummy_config_and_data(tmpdir_factory):
    """Creates a dummy config and dummy data for testing the decision pipeline."""
    model_dir = tmpdir_factory.mktemp("models")
    
    config = {
        'model_dir': str(model_dir),
        'best_model_name': 'dummy_model.pth', # Generic name for the test
        'scaler_name': 'dummy_scaler.joblib',
        'window_size': 5,
        'bet_percentages': [0.1]
    }
    
    # Create dummy historical data. Must be larger than the largest rolling window (30).
    data = {'Period': range(100), 'Premium': np.random.randint(1000, 9999, 100)}
    historical_data = pd.DataFrame(data)
    
    # Create and save a dummy scaler
    # In a real scenario, this would be the scaler from training
    dummy_scaler = joblib.load(os.path.join(project_root, 'models', 'feature_scaler.joblib')) # Use a real scaler for correct feature dimensions
    scaler_path = os.path.join(config['model_dir'], config['scaler_name'])
    joblib.dump(dummy_scaler, scaler_path)
    
    return config, historical_data

def create_and_save_dummy_model(model_path, n_actions, preferred_action_index):
    """Creates a dummy SAC model with a strong preference for a specific action."""
    # These params should match a real model's architecture
    params = {
        'features_per_step': 29, # Based on the latest run
        'n_actions': n_actions,
        'window_size': 5,
        'hidden_size': 128,
        'dropout_rate': 0.1
    }
    model = ActorCriticSAC_GRU(**params)
    
    # --- Force the Actor's output ---
    # Create logits where the preferred action has a very high value
    forced_logits = torch.full((n_actions,), -10.0)
    forced_logits[preferred_action_index] = 10.0
    
    # Manually set the weights and biases of the final layer of the actor head
    final_layer = model.actor_head[-1]
    final_layer.weight.data.fill_(0.0)
    final_layer.bias.data = forced_logits
    
    # Save the dummy model
    torch.save({
        'model_state_dict': model.state_dict(),
        'architecture_params': params
    }, model_path)

# --- Test Cases ---

def test_decision_pipeline_forces_hold(dummy_config_and_data):
    """
    Tests if the pipeline correctly outputs 'Hold' when the model is biased to do so.
    This proves the code is not stuck on 'Hold'.
    """
    config, historical_data = dummy_config_and_data
    model_path = os.path.join(config['model_dir'], config['best_model_name'])
    n_actions = 1 + 2 * len(config['bet_percentages']) # 1 Hold + 2 Bet types * 1 percentage level = 3
    
    # Create a model that strongly prefers action 0 (Hold)
    create_and_save_dummy_model(model_path, n_actions, preferred_action_index=0)
    
    # Initialize DecisionMaker and load the dummy model
    decision_maker = DecisionMaker(config)
    assert decision_maker.load_model(), "Failed to load the dummy 'Hold' model."
    
    # Get the action
    action_idx, action_str = decision_maker.get_action(historical_data)
    
    # Assert that the chosen action is 'Hold'
    assert action_idx == 0
    assert "Hold" in action_str

def test_decision_pipeline_forces_bet(dummy_config_and_data):
    """
    Tests if the pipeline correctly outputs a 'Bet' action when the model is biased to do so.
    This proves the action signal mechanism is working for all action types.
    """
    config, historical_data = dummy_config_and_data
    model_path = os.path.join(config['model_dir'], config['best_model_name'])
    n_actions = 1 + 2 * len(config['bet_percentages']) # 3 actions
    bet_action_index = 2 # Corresponds to 'Bet Big'
    
    # Create a model that strongly prefers the 'Bet Big' action
    create_and_save_dummy_model(model_path, n_actions, preferred_action_index=bet_action_index)
    
    # Initialize DecisionMaker and load the dummy model
    decision_maker = DecisionMaker(config)
    assert decision_maker.load_model(), "Failed to load the dummy 'Bet' model."
    
    # Get the action
    action_idx, action_str = decision_maker.get_action(historical_data)
    
    # Assert that the chosen action is the 'Bet Big' action
    assert action_idx == bet_action_index
    assert "Bet Big" in action_str
