import pytest
import torch
import sys
import os

# --- Path Setup ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from rl_agent.model import ActorCriticSAC_GRU

@pytest.fixture
def model_params():
    """Provides a standard set of model parameters for testing."""
    return {
        'features_per_step': 5,
        'n_actions': 3,
        'window_size': 10,
        'hidden_size': 64,
        'dropout_rate': 0.1
    }

@pytest.fixture
def sac_model(model_params):
    """Creates an instance of the ActorCriticSAC_GRU model."""
    return ActorCriticSAC_GRU(**model_params)

def test_model_initialization(sac_model, model_params):
    """Tests if the SAC model layers are initialized correctly."""
    assert sac_model.window_size == model_params['window_size']
    assert sac_model.features_per_step == model_params['features_per_step']
    
    # Check GRU layer in one of the heads (e.g., actor's)
    # Note: In the new design, GRU is part of the main class, not separate heads.
    assert sac_model.gru.input_size == model_params['features_per_step']
    assert sac_model.gru.hidden_size == model_params['hidden_size']
    
    # Check output dimensions of the heads
    assert sac_model.actor_head[-1].out_features == model_params['n_actions']
    assert sac_model.critic1_head[-1].out_features == model_params['n_actions']
    assert sac_model.critic2_head[-1].out_features == model_params['n_actions']

def test_forward_pass_shape(sac_model, model_params):
    """Tests the forward pass for a batch of items."""
    batch_size = 32
    window_size = model_params['window_size']
    features_per_step = model_params['features_per_step']
    n_actions = model_params['n_actions']

    # Input state should be shaped (batch, window, features)
    batch_input = torch.randn(batch_size, window_size, features_per_step)
    
    policy_dist, q1_values, q2_values = sac_model(batch_input)

    assert q1_values.shape == (batch_size, n_actions)
    assert q2_values.shape == (batch_size, n_actions)
    
    # Check policy distribution
    assert policy_dist.batch_shape == (batch_size,)
    assert policy_dist.event_shape == ()
    # Check that the logits have the correct shape
    assert policy_dist.logits.shape == (batch_size, n_actions)


def test_get_action(sac_model, model_params):
    """Tests the get_action method."""
    window_size = model_params['window_size']
    features_per_step = model_params['features_per_step']
    
    # Input for a single state
    single_input = torch.randn(window_size, features_per_step)
    
    action = sac_model.get_action(single_input, device=torch.device('cpu'))
    
    assert isinstance(action, int)
    assert 0 <= action < model_params['n_actions']

def test_model_on_device(model_params):
    """Tests if the model can be moved to and run on a CUDA device if available."""
    if not torch.cuda.is_available():
        pytest.skip("CUDA not available, skipping device test.")
    
    device = torch.device("cuda")
    model = ActorCriticSAC_GRU(**model_params).to(device)
    
    # Create a tensor on the same device
    input_tensor = torch.randn(4, model_params['window_size'], model_params['features_per_step']).to(device)
    
    # This should run without errors
    try:
        policy_dist, q1, q2 = model(input_tensor)
        assert q1.device.type == 'cuda'
        assert q2.device.type == 'cuda'
        assert policy_dist.logits.device.type == 'cuda'
    except Exception as e:
        pytest.fail(f"Model failed to run on CUDA device: {e}")
