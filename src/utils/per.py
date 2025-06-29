# Standard library imports
import random
import numpy as np
from collections import namedtuple

# Define the Transition tuple, which will be used by the memory buffer
Transition = namedtuple('Transition', ('state', 'action', 'next_state', 'reward'))

class SumTree:
    """
    A SumTree data structure for efficient sampling based on priorities.
    This is a key component for Prioritized Experience Replay.
    The tree is represented as a single array.
    """
    write = 0

    def __init__(self, capacity):
        self.capacity = capacity
        # The tree has capacity-1 internal nodes and capacity leaf nodes.
        self.tree = np.zeros(2 * capacity - 1)
        # The data (transitions) are stored at the leaf nodes.
        self.data = np.zeros(capacity, dtype=object)
        self.n_entries = 0

    def _propagate(self, idx, change):
        """Propagate a change in priority up the tree."""
        parent = (idx - 1) // 2
        self.tree[parent] += change
        if parent != 0:
            self._propagate(parent, change)

    def _retrieve(self, idx, s):
        """Find the sample index for a given priority value."""
        left = 2 * idx + 1
        right = left + 1

        if left >= len(self.tree):
            return idx

        if s <= self.tree[left]:
            return self._retrieve(left, s)
        else:
            return self._retrieve(right, s - self.tree[left])

    def total(self):
        """Return the total priority of all entries."""
        return self.tree[0]

    def add(self, p, data):
        """Add a new entry with a given priority."""
        idx = self.write + self.capacity - 1
        self.data[self.write] = data
        self.update(idx, p)

        self.write += 1
        if self.write >= self.capacity:
            self.write = 0

        if self.n_entries < self.capacity:
            self.n_entries += 1

    def update(self, idx, p):
        """Update the priority of an entry."""
        change = p - self.tree[idx]
        self.tree[idx] = p
        self._propagate(idx, change)

    def get(self, s):
        """Get an entry (priority, data, index) by its priority value."""
        idx = self._retrieve(0, s)
        data_idx = idx - self.capacity + 1
        return (self.tree[idx], self.data[data_idx], idx)


class PrioritizedReplayMemory:
    """
    A Replay Memory that uses a SumTree to implement Prioritized Experience Replay.
    """
    e = 0.01  # Small constant to ensure non-zero priority
    a = 0.6   # Alpha: controls how much prioritization is used (0: uniform, 1: full)
    beta = 0.4 # Beta: importance-sampling correction, anneals to 1
    beta_increment_per_sampling = 0.001

    def __init__(self, capacity):
        self.tree = SumTree(capacity)
        self.capacity = capacity

    def _get_priority(self, error):
        """Calculate priority from TD-error."""
        return (np.abs(error) + self.e) ** self.a

    def push(self, error, *args):
        """Store a new transition in the memory with its initial priority."""
        p = self._get_priority(error)
        self.tree.add(p, Transition(*args))

    def sample(self, batch_size):
        """
        Sample a batch of transitions, returning the transitions, their indices,
        and importance-sampling weights.
        """
        batch = []
        idxs = []
        segment = self.tree.total() / batch_size
        priorities = []

        self.beta = np.min([1., self.beta + self.beta_increment_per_sampling])

        for i in range(batch_size):
            a = segment * i
            b = segment * (i + 1)
            s = random.uniform(a, b)
            (p, data, idx) = self.tree.get(s)
            priorities.append(p)
            batch.append(data)
            idxs.append(idx)

        sampling_probabilities = np.array(priorities) / self.tree.total()
        # Importance-sampling weights
        is_weight = np.power(self.tree.n_entries * sampling_probabilities, -self.beta)
        is_weight /= is_weight.max() # Normalize for stability

        return batch, idxs, is_weight

    def update(self, idx, error):
        """Update the priority of a transition after it has been used in training."""
        p = self._get_priority(error)
        self.tree.update(idx, p)

    def __len__(self):
        return self.tree.n_entries