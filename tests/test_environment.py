import pytest
import pandas as pd
import numpy as np
import sys
import os

# --- Path Setup ---
# This allows the test to find the 'rl_agent' package
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from rl_agent.environment import TradingEnv

@pytest.fixture
def sample_data():
    """
    Membuat data fitur dan target sampel yang telah dipisahkan untuk pengujian.
    """
    data = {
        'Period': range(20),
        'Number':  [1, 6, 2, 8, 3, 9, 4, 5, 0, 7, 1, 6, 2, 8, 3, 9, 4, 5, 0, 7], # S, B, S, B, S, B, S, B, S, B...
        'feature_1': np.linspace(0, 1, 20),
        'feature_2': np.linspace(1, 0, 20)
    }
    df = pd.DataFrame(data)
    
    # Buat features_df
    features_df = df[['feature_1', 'feature_2']].copy()
    
    # Buat targets_df
    targets_df = pd.DataFrame(index=df.index)
    targets_df['is_big'] = (df['Number'] >= 5).astype(int)
    
    return features_df, targets_df

@pytest.fixture
def trading_env(sample_data):
    """
    Membuat instance TradingEnv dengan parameter yang disederhanakan untuk pengujian.
    """
    features_df, targets_df = sample_data
    return TradingEnv(
        features_df=features_df,
        targets_df=targets_df,
        window_size=5,
        bet_percentages=[0.1], # Satu level taruhan untuk kesederhanaan
        initial_balance=10000,
        loss_penalty_multiplier=2.0, # Penalti 2x untuk kerugian
        win_bonus=0.01,
        time_decay_penalty=0.001,
        transaction_cost=0.0
    )

def test_env_initialization(trading_env, sample_data):
    """Menguji apakah environment diinisialisasi dengan benar."""
    features_df, targets_df = sample_data
    assert trading_env.window_size == 5
    assert trading_env.features_df.equals(features_df)
    assert trading_env.targets_df.equals(targets_df)
    
    # Aksi: 0=Tahan, 1=Taruhan Kecil (10%), 2=Taruhan Besar (10%)
    assert trading_env.action_space.n == 3
    
    # Observasi: (window_size, jumlah_fitur)
    assert trading_env.observation_space.shape == (5, 2)

def test_reset(trading_env, sample_data):
    """Menguji metode reset."""
    features_df, _ = sample_data
    obs, info = trading_env.reset()
    
    assert trading_env.current_step == 5
    assert trading_env.balance == 10000
    assert info['balance'] == 10000
    
    # Verifikasi bentuk dan konten observasi awal
    assert obs.shape == (5, 2)
    expected_obs = features_df.iloc[0:5].values
    np.testing.assert_array_equal(obs, expected_obs.astype(np.float32))

def test_step_logic_and_rewards(trading_env):
    """Menguji metode step untuk berbagai aksi dan hasil."""
    obs, info = trading_env.reset()
    initial_balance = trading_env.initial_balance

    # --- Langkah 1 (current_step=5) ---
    # Hasil Sebenarnya: Nomor adalah 9 (Besar, is_big=1)
    # Aksi: Taruhan Besar (2) -> Taruhan Benar
    bet_amount = initial_balance * 0.1 # 1000
    profit = bet_amount * 0.95 # 950
    expected_reward = (profit / initial_balance) + trading_env.win_bonus # (950/10000) + 0.01 = 0.095 + 0.01 = 0.105
    
    obs, reward, _, _, info = trading_env.step(2)
    assert pytest.approx(reward) == expected_reward
    assert info['balance'] == initial_balance + profit # 10950
    assert trading_env.current_step == 6

    # --- Langkah 2 (current_step=6) ---
    # Hasil Sebenarnya: Nomor adalah 4 (Kecil, is_big=0)
    # Aksi: Taruhan Besar (2) -> Taruhan Salah
    current_balance = info['balance'] # 10950
    bet_amount = current_balance * 0.1 # 1095
    bet_amount = round(bet_amount / 1000) * 1000 # 1000
    expected_reward = - (bet_amount / initial_balance) * trading_env.loss_penalty_multiplier # -(1000/10000) * 2 = -0.2
    
    obs, reward, _, _, info = trading_env.step(2)
    assert pytest.approx(reward) == expected_reward
    assert info['balance'] == current_balance - bet_amount # 10950 - 1000 = 9950
    assert trading_env.current_step == 7

    # --- Langkah 3 (current_step=7) ---
    # Hasil Sebenarnya: Nomor adalah 5 (Besar, is_big=1)
    # Aksi: Tahan (0)
    current_balance = info['balance'] # 9950
    expected_reward = -trading_env.time_decay_penalty # -0.001
    
    obs, reward, _, _, info = trading_env.step(0)
    assert pytest.approx(reward) == expected_reward
    assert info['balance'] == current_balance # Saldo tidak berubah
    assert trading_env.current_step == 8

def test_episode_end(trading_env, sample_data):
    """Menguji apakah episode berakhir dengan benar."""
    features_df, _ = sample_data
    trading_env.reset()
    
    # Atur langkah saat ini ke titik di mana langkah berikutnya akan menjadi yang terakhir.
    # len(features_df) = 20. Langkah terakhir yang valid adalah di indeks 19.
    # Kondisi done adalah `current_step >= 19`.
    # Kita atur current_step ke 18. Setelah step(), itu akan menjadi 19.
    end_step = len(features_df)
    trading_env.current_step = end_step - 2 # current_step = 18

    # Langkah ini akan memproses data di indeks 18, lalu menaikkan step ke 19.
    # Pada titik ini, kondisi done (19 >= 19) terpenuhi.
    obs, reward, terminated, truncated, info = trading_env.step(0)
    
    # Episode seharusnya berakhir sekarang.
    assert terminated, "Episode seharusnya berakhir setelah langkah ini."
    assert truncated, "Episode seharusnya terpotong setelah langkah ini."
    assert trading_env.current_step == end_step - 1 # step dinaikkan menjadi 19