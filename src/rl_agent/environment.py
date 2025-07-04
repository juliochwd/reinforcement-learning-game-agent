import gymnasium as gym
from gymnasium import spaces
import numpy as np
import pandas as pd
import logging

class TradingEnv(gym.Env):
    """
    Environment RL yang dirancang untuk mencegah kebocoran data secara struktural dengan
    menerima dataframe fitur dan target yang terpisah.
    """
    metadata = {'render.modes': ['human']}

    def __init__(self, features_df, targets_df, window_size=10,
                 initial_balance=2000000, bet_percentages=[0.01, 0.025],
                 payout_ratio=0.95, transaction_cost=1e-4,
                 reward_strategy="direct_pnl", reward_sharpe_window=30, hold_penalty=0.0):
        """
        Inisialisasi environment.
        
        Args:
            payout_ratio (float): Imbal hasil kotor untuk taruhan yang menang.
            transaction_cost (float): Biaya per transaksi sebagai persentase dari jumlah taruhan.
        """
        super(TradingEnv, self).__init__()

        self.window_size = window_size
        self.initial_balance = initial_balance
        self.bet_percentages = bet_percentages
        self.payout_ratio = payout_ratio
        self.transaction_cost = transaction_cost
        self.reward_strategy = reward_strategy
        self.reward_sharpe_window = reward_sharpe_window
        self.hold_penalty = hold_penalty
        self.returns_history = [] # Riwayat imbal hasil per taruhan
        
        # Pastikan kedua dataframe memiliki indeks yang selaras
        if not features_df.index.equals(targets_df.index):
            raise ValueError("Indeks Features dan Targets harus selaras.")

        self.features_df = features_df
        self.targets_df = targets_df
        
        self.features_per_step = len(self.features_df.columns)
        
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf,
            shape=(self.window_size, self.features_per_step),
            dtype=np.float32
        )
        
        self.action_space = spaces.Discrete(1 + 2 * len(self.bet_percentages))

        self.reset()

    def _get_observation(self):
        """
        Membangun observasi/state untuk agen HANYA dari features_df.
        """
        # Observasi untuk memutuskan pada 'current_step' harus berisi data HANYA SAMPAI 'current_step - 1'.
        start = self.current_step - self.window_size
        end = self.current_step # Slicing pandas tidak inklusif pada akhir, jadi ini benar
        
        observation_frame = self.features_df.iloc[start:end].values
        
        return observation_frame.astype(np.float32)

    def _get_actual_outcome(self):
        """Menentukan hasil permainan yang sebenarnya dari targets_df."""
        return self.targets_df['is_big'].iloc[self.current_step]

    def reset(self, seed=None, options=None):
        """Mereset environment."""
        super().reset(seed=seed)
        # Mulai pada langkah pertama di mana kita memiliki jendela data historis penuh
        self.current_step = self.window_size 
        self.balance = self.initial_balance
        self.total_reward = 0
        self.returns_history = [] # Reset riwayat di sini
        
        initial_observation = self._get_observation()
        info = {'balance': self.balance}
        
        return initial_observation, info

    def step(self, action):
        """Menjalankan satu langkah dalam environment."""
        actual_outcome = self._get_actual_outcome()
        
        previous_balance = self.balance
        bet_amount = 0
        
        if action > 0:  # Aksi taruhan
            num_bet_levels = len(self.bet_percentages)
            
            if 1 <= action <= num_bet_levels:
                bet_choice = 0  # Small
                percentage = self.bet_percentages[action - 1]
            else:
                bet_choice = 1  # Big
                percentage = self.bet_percentages[action - 1 - num_bet_levels]

            calculated_amount = self.balance * percentage
            bet_amount = max(1000, round(calculated_amount / 1000) * 1000)
            bet_amount = min(bet_amount, self.balance)

            if self.balance > 0 and bet_amount > 0:
                if bet_choice == actual_outcome:
                    # Kemenangan
                    profit = bet_amount * self.payout_ratio
                    self.balance += profit
                else:
                    # Kekalahan
                    self.balance -= bet_amount
        
        # --- Logika Reward yang Didesain Ulang ---
        current_return_pct = 0.0
        if bet_amount > 0: # Hanya jika ada taruhan
            # Hitung return sebagai persentase dari jumlah taruhan
            current_return_pct = (self.balance - previous_balance) / bet_amount
            self.returns_history.append(current_return_pct)
            if len(self.returns_history) > self.reward_sharpe_window:
                self.returns_history.pop(0)

        reward = 0.0
        # Pilar 1: Hitung reward konsistensi
        if self.reward_strategy == "sharpe_proxy":
            if len(self.returns_history) >= 2:
                returns_np = np.array(self.returns_history)
                # Reward adalah skor konsistensi (mean dibagi std dev)
                reward = np.mean(returns_np) / (np.std(returns_np) + 1e-9)
        else: # Fallback ke strategi lama (profit/loss langsung)
            reward = self.balance - previous_balance

        # Pilar 2: Terapkan penalti aktivitas
        if action == 0:
            reward -= self.hold_penalty
        
        # --- LOG DIAGNOSTIK ---
        if self.current_step % 200 == 0: # Log setiap 200 langkah untuk tidak membanjiri
            logging.debug(f"REWARD_CALC (Step: {self.current_step}): Action={action}, "
                          f"Return%={current_return_pct:.4f}, "
                          f"SharpeProxy={np.mean(self.returns_history) / (np.std(self.returns_history) + 1e-9):.4f} (dari {len(self.returns_history)} data), "
                          f"HoldPenaltyApplied={self.hold_penalty if action == 0 else 0}, "
                          f"FinalReward={reward:.4f}")
        # --- AKHIR LOG DIAGNOSTIK ---

        self.total_reward = self.balance - self.initial_balance
        self.current_step += 1

        done = (self.current_step >= len(self.features_df) -1) or (self.balance <= 0)
        terminated = done
        truncated = done

        next_observation = self._get_observation() if not done else np.zeros(self.observation_space.shape, dtype=np.float32)
        info = {'total_reward': self.total_reward, 'balance': self.balance, 'bet_amount': bet_amount}

        return next_observation, reward, terminated, truncated, info

    def calculate_episode_sharpe(self):
        """Menghitung Sharpe Ratio untuk seluruh episode."""
        if len(self.returns_history) < 2:
            return 0.0
        returns_np = np.array(self.returns_history)
        std_dev = np.std(returns_np)
        if std_dev < 1e-9: # Hindari pembagian dengan nol
            return 0.0
        return np.mean(returns_np) / std_dev
