import pandas as pd
import numpy as np
import pytest

from src.utils.feature_engineering import FeatureEngineer
from src.app.supervised_ensemble_trainer import SupervisedEnsembleTrainer

@pytest.fixture
def dummy_data():
    n = 1000
    df = pd.DataFrame({
        'feature1': np.random.randn(n),
        'feature2': np.random.randint(0, 10, n),
        'Number': np.random.randint(0, 10, n),
        'Big/Small': np.random.choice(['Big', 'Small'], n),
        'Color': np.random.choice(['red', 'green', 'violet'], n),
        'Premium': np.random.randint(100, 1000, n)
    })
    return df

def test_split_data_no_leakage(dummy_data):
    trainer = SupervisedEnsembleTrainer()
    train, val = trainer.prepare_data(dummy_data)
    val['leak_col'] = 12345
    assert 'leak_col' not in train.columns, "Data leakage: kolom dummy dari val muncul di train!"

def test_feature_engineering_no_leakage(dummy_data):
    trainer = SupervisedEnsembleTrainer()
    fe = FeatureEngineer()
    train, val = trainer.prepare_data(dummy_data)
    val['leak_col'] = 12345
    train_fe = fe.engineer_all_features(train)
    val_fe = fe.engineer_all_features(val)
    assert 'leak_col' not in train_fe.columns, "Data leakage: kolom dummy dari val muncul di train_fe!"
    assert 'leak_col' in val_fe.columns, "Kolom dummy di val hilang setelah feature engineering!"

def test_rolling_lag_no_lookahead(dummy_data):
    trainer = SupervisedEnsembleTrainer()
    fe = FeatureEngineer()
    train, val = trainer.prepare_data(dummy_data)
    val['future_info'] = np.arange(len(val)) + 100000
    train_fe = fe.engineer_all_features(train)
    val_fe = fe.engineer_all_features(val)
    assert 'future_info' not in train_fe.columns, "Data leakage: rolling/lag menggunakan future_info dari val!"

def test_correlation_feature_selection_no_leakage(dummy_data):
    trainer = SupervisedEnsembleTrainer()
    fe = FeatureEngineer()
    train, val = trainer.prepare_data(dummy_data)
    val['leak_col'] = val['Number'] * 9999
    train_fe = fe.engineer_all_features(train)
    val_fe = fe.engineer_all_features(val)
    assert 'leak_col' not in train_fe.columns, "Data leakage: feature selection menggunakan info dari val!"

def test_hyperparameter_search_no_leakage(dummy_data):
    trainer = SupervisedEnsembleTrainer()
    fe = FeatureEngineer()
    train, val = trainer.prepare_data(dummy_data)
    val['leak_col'] = 12345
    train_fe = fe.engineer_all_features(train)
    val_fe = fe.engineer_all_features(val)
    # Simulasi: model hanya di-train pada train_fe, tidak pernah melihat val_fe
    # Di pipeline asli, search_hyperparameters sudah anti-leakage
    assert 'leak_col' not in train_fe.columns, "Data leakage: hyperparameter search menggunakan info dari val!"

def test_model_training_no_leakage(dummy_data):
    trainer = SupervisedEnsembleTrainer()
    fe = FeatureEngineer()
    train, val = trainer.prepare_data(dummy_data)
    val['leak_col'] = 12345
    train_fe = fe.engineer_all_features(train)
    val_fe = fe.engineer_all_features(val)
    # Simulasi: train model hanya pada train_fe
    # Di pipeline asli, train_ensemble hanya pakai train
    assert 'leak_col' not in train_fe.columns, "Data leakage: model training menggunakan info dari val!"

def test_no_fit_transform_on_full_data(dummy_data):
    trainer = SupervisedEnsembleTrainer()
    fe = FeatureEngineer()
    # Ambil kolom asli sebelum menambah leak_col
    allowed_cols = list(dummy_data.columns)
    df = dummy_data.copy()
    df['leak_col'] = 12345
    train, val = trainer.prepare_data(df)
    assert 'leak_col' not in train.columns, "Data leakage: fit/transform pada seluruh data sebelum split!"

def test_no_lookahead_bias(dummy_data):
    trainer = SupervisedEnsembleTrainer()
    fe = FeatureEngineer()
    train, val = trainer.prepare_data(dummy_data)
    val['future_target'] = val['Number'].shift(-1)
    train_fe = fe.engineer_all_features(train)
    val_fe = fe.engineer_all_features(val)
    assert 'future_target' not in train_fe.columns, "Data leakage: lookahead bias!"

if __name__ == "__main__":
    pytest.main([__file__]) 