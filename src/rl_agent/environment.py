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
                 loss_penalty_multiplier=1.5, win_bonus=1e-5,
                 time_decay_penalty=1e-6, transaction_cost=1e-4):
        """
        Inisialisasi environment.
        
        Args:
            loss_penalty_multiplier (float): Pengali untuk kerugian. Nilai > 1.0 membuat agen lebih menghindari risiko.
                                             Diturunkan dari 2.0 menjadi 1.5 untuk mengurangi keengganan risiko yang ekstrem.
            win_bonus (float): Bonus reward kecil yang diberikan untuk setiap tebakan yang benar, mendorong partisipasi.
            time_decay_penalty (float): Penalti kecil yang diterapkan untuk setiap langkah 'Hold', mendorong agen untuk aktif.
                                        Menggantikan 'hold_reward' positif sebelumnya.
        """
        super(TradingEnv, self).__init__()

        self.window_size = window_size
        self.initial_balance = initial_balance
        self.bet_percentages = bet_percentages
        self.loss_penalty_multiplier = loss_penalty_multiplier
        self.win_bonus = win_bonus
        self.time_decay_penalty = time_decay_penalty
        self.transaction_cost = transaction_cost
        
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
        
        initial_observation = self._get_observation()
        info = {'balance': self.balance}
        
        return initial_observation, info

    def step(self, action):
        """Menjalankan satu langkah dalam environment."""
        actual_outcome = self._get_actual_outcome()
        
        previous_balance = self.balance
        bet_amount = 0
        reward = 0

        if action == 0:  # Aksi 'Tahan'
            # Terapkan penalti kecil untuk mendorong aksi (menghindari stagnasi)
            reward = -self.time_decay_penalty
        else:  # Aksi taruhan
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
                # Terapkan biaya transaksi untuk setiap taruhan
                self.balance -= bet_amount * self.transaction_cost

                if bet_choice == actual_outcome:
                    # Kemenangan: imbalan adalah persentase dari keuntungan + bonus kemenangan
                    profit = bet_amount * 0.95
                    self.balance += profit
                    # Imbalan dinormalisasi + bonus kecil untuk mendorong kemenangan
                    reward = (profit / self.initial_balance) + self.win_bonus
                else:
                    # Kekalahan: penalti adalah persentase dari kerugian, dikalikan dengan pengganda penalti
                    self.balance -= bet_amount
                    # Penalti yang lebih besar untuk kerugian untuk mendorong kehati-hatian
                    reward = - (bet_amount / self.initial_balance) * self.loss_penalty_multiplier
        
        self.total_reward = self.balance - self.initial_balance  # Lacak total profit secara terpisah
        self.current_step += 1

        done = (self.current_step >= len(self.features_df) -1) or (self.balance <= 0)
        terminated = done
        truncated = done

        next_observation = self._get_observation() if not done else np.zeros(self.observation_space.shape, dtype=np.float32)
        info = {'total_reward': self.total_reward, 'balance': self.balance, 'bet_amount': bet_amount}

        return next_observation, reward, terminated, truncated, info