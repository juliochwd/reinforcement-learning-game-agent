import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.distributions import Categorical

class ActorCriticSAC_GRU(nn.Module):
    """
    An Actor-Critic model for SAC-Discrete, using a GRU layer to process sequential state information.
    This version is correctly adapted for discrete action spaces.
    """
    def __init__(self, features_per_step, n_actions, window_size, hidden_size=256, dropout_rate=0.2):
        """
        Args:
            features_per_step (int): The number of features for each time step in the window.
            n_actions (int): The number of possible discrete actions.
            window_size (int): The number of time steps in the state.
            hidden_size (int): The size of the GRU's hidden memory and intermediate FC layers.
            dropout_rate (float): The dropout rate to apply for regularization.
        """
        super(ActorCriticSAC_GRU, self).__init__()
        self.window_size = window_size
        self.features_per_step = features_per_step
        self.n_actions = n_actions

        # --- Shared GRU Backbone ---
        self.gru = nn.GRU(
            input_size=features_per_step,
            hidden_size=hidden_size,
            num_layers=1,
            batch_first=True
        )
        self.dropout = nn.Dropout(dropout_rate)
        
        # --- Actor Head ---
        # Outputs logits for the categorical policy distribution.
        self.actor_head = nn.Sequential(
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, n_actions)
        )
        
        # --- Twin Q-Critics Heads ---
        # Each critic outputs a Q-value for each possible action.
        self.critic1_head = nn.Sequential(
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, n_actions)
        )
        self.critic2_head = nn.Sequential(
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, n_actions)
        )

    def _get_base_features(self, state):
        """
        Processes the input state through the shared GRU backbone.
        Handles reshaping of the input state.
        """
        # Input state shape can be (batch, features) or (batch, window, features_per_step)
        if state.dim() == 2:
            state = state.view(-1, self.window_size, self.features_per_step)
        
        _, h_n = self.gru(state)
        base_features = h_n.squeeze(0)
        base_features = self.dropout(base_features)
        return base_features

    def get_action(self, state, device):
        """
        Gets an action from the policy for a given state during rollouts.
        Handles both batched (3D) and unbatched (2D) states.
        """
        if not isinstance(state, torch.Tensor):
            state = torch.tensor(state, dtype=torch.float32, device=device)
        else:
            state = state.to(device)

        # Add batch dimension if it's a single observation
        if state.dim() == 2:
            state = state.unsqueeze(0)

        base_features = self._get_base_features(state)
        
        action_logits = self.actor_head(base_features)
        policy_dist = Categorical(logits=action_logits)
        
        action = policy_dist.sample()
        
        return action.item()

    def forward(self, state):
        """
        Performs a full forward pass, returning policy and Q-values.
        Used during the update step.
        """
        base_features = self._get_base_features(state)
        
        # Actor pass
        action_logits = self.actor_head(base_features)
        policy_dist = Categorical(logits=action_logits)
        
        # Critics pass
        q1_values = self.critic1_head(base_features)
        q2_values = self.critic2_head(base_features)
        
        return policy_dist, q1_values, q2_values
