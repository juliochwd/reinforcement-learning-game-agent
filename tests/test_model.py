import pytest
import torch
import sys
import os

# --- Path Setup ---
# This allows the test to find the 'rl_agent' package
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from rl_agent.model import GRU_DQN

@pytest.fixture
def model_params():
    """Provides a standard set of model parameters for testing."""
    return {
        'features_per_step': 1,
        'n_actions': 3,
        'window_size': 10,
        'hidden_size': 64,
        'dropout_rate': 0.5
    }

@pytest.fixture
def gru_model(model_params):
    """Creates an instance of the GRU_DQN model."""
    return GRU_DQN(**model_params)

def test_model_initialization(gru_model, model_params):
    """Tests if the model layers are initialized with correct dimensions."""
    assert gru_model.window_size == model_params['window_size']
    assert gru_model.features_per_step == model_params['features_per_step']
    
    # Check GRU layer
    assert gru_model.gru.input_size == model_params['features_per_step']
    assert gru_model.gru.hidden_size == model_params['hidden_size']
    
    # Check Dueling Streams
    # Value stream should start with hidden_size and end with 1
    assert gru_model.value_stream[0].in_features == model_params['hidden_size']
    assert gru_model.value_stream[-1].out_features == 1
    
    # Advantage stream should start with hidden_size and end with n_actions
    assert gru_model.advantage_stream[0].in_features == model_params['hidden_size']
    assert gru_model.advantage_stream[-1].out_features == model_params['n_actions']

def test_forward_pass_shape(gru_model, model_params):
    """Tests the forward pass for a single item and a batch of items."""
    window_size = model_params['window_size']
    features_per_step = model_params['features_per_step']
    n_actions = model_params['n_actions']

    # --- Test with a single item (batch size = 1) ---
    # Input state should be flat, like the environment provides
    single_input = torch.randn(1, window_size * features_per_step)
    output = gru_model(single_input)
    
    assert output.shape == (1, n_actions), f"Expected shape (1, {n_actions}) for single input, but got {output.shape}"

    # --- Test with a batch of items (batch size = 32) ---
    batch_size = 32
    batch_input = torch.randn(batch_size, window_size * features_per_step)
    batch_output = gru_model(batch_input)

    assert batch_output.shape == (batch_size, n_actions), f"Expected shape ({batch_size}, {n_actions}) for batch input, but got {batch_output.shape}"

def test_model_on_device(model_params):
    """Tests if the model can be moved to and run on a CUDA device if available."""
    if not torch.cuda.is_available():
        pytest.skip("CUDA not available, skipping device test.")
    
    device = torch.device("cuda")
    model = GRU_DQN(**model_params).to(device)
    
    # Create a tensor on the same device
    input_tensor = torch.randn(4, model_params['window_size'] * model_params['features_per_step']).to(device)
    
    # This should run without errors
    try:
        output = model(input_tensor)
        assert output.device.type == 'cuda'
    except Exception as e:
        pytest.fail(f"Model failed to run on CUDA device: {e}")