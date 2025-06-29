import torch
import torch.nn as nn
import torch.nn.functional as F

class GRU_DQN(nn.Module):
    """
    A Dueling DQN that uses a GRU layer to process sequential state information.
    This architecture separates the estimation of state value V(s) and action advantages A(s,a).
    """
    def __init__(self, features_per_step, n_actions, window_size, hidden_size=64, dropout_rate=0.5):
        """
        Args:
            features_per_step (int): The number of features for each time step in the window.
            n_actions (int): The number of possible actions.
            window_size (int): The number of time steps in the state.
            hidden_size (int): The size of the GRU's hidden memory and the intermediate FC layers.
            dropout_rate (float): The dropout rate to apply for regularization.
        """
        super(GRU_DQN, self).__init__()
        self.window_size = window_size
        self.features_per_step = features_per_step
        self.n_actions = n_actions

        # Shared GRU layer to process sequence
        self.gru = nn.GRU(
            input_size=features_per_step,
            hidden_size=hidden_size,
            num_layers=1,
            batch_first=True
        )
        
        self.dropout = nn.Dropout(dropout_rate)
        
        # Dueling Streams
        # 1. Value Stream: Estimates V(s) - the value of being in a certain state.
        self.value_stream = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 2),
            nn.ReLU(),
            nn.Linear(hidden_size // 2, 1)
        )
        
        # 2. Advantage Stream: Estimates A(s,a) - the advantage of taking a specific action.
        self.advantage_stream = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 2),
            nn.ReLU(),
            nn.Linear(hidden_size // 2, n_actions)
        )

    def forward(self, state):
        """
        Forward pass for the Dueling DQN.
        """
        batch_size = state.shape[0]
        # Reshape flat state into (batch_size, sequence_length, features_per_step) for GRU
        gru_input = state.view(batch_size, self.window_size, self.features_per_step)
        
        # Get the final hidden state from the GRU
        _, h_n = self.gru(gru_input)
        last_hidden_state = h_n.squeeze(0)
        last_hidden_state = self.dropout(last_hidden_state)

        # Get Value and Advantage from their respective streams
        value = self.value_stream(last_hidden_state)  # Shape: (batch_size, 1)
        advantages = self.advantage_stream(last_hidden_state)  # Shape: (batch_size, n_actions)
        
        # Combine V(s) and A(s,a) to get final Q(s,a)
        # Q(s,a) = V(s) + (A(s,a) - mean(A(s,a')))
        # This ensures the advantages sum to zero, improving stability.
        q_values = value + (advantages - advantages.mean(dim=1, keepdim=True))
        
        return q_values