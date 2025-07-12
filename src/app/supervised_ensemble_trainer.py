import logging
import os
import pickle
import pandas as pd
import numpy as np
from river import tree, metrics
from src.utils.feature_engineering import FeatureEngineer, engineer_features_number_full_anti_leakage
import threading
import time
import optuna
import json
import sys
import platform
import datetime
import inspect
import importlib.metadata
from typing import Optional, cast
import multiprocessing

MODEL_PATH = os.path.join('models', 'river_hoeffdingtree.pkl')
DATA_PATH = os.path.join('data', 'databaru_from_api.csv')
CONFIDENCE_THRESHOLD = 0.7
BEST_PARAMS_PATH = os.path.join('models', 'best_river_params.json')
BEST_PARAMS_META_PATH = os.path.join('models', 'best_river_params_meta.json')
LOG_PATH = os.path.join('logs', f'training_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.log')

class SupervisedEnsembleTrainer:
    def __init__(self, controller=None):
        self.model: Optional[tree.HoeffdingTreeClassifier] = None
        self.metric = metrics.Accuracy()
        self.feature_engineer = FeatureEngineer()
        self.classes = list(range(10))  # Target: Number 0-9
        self.is_trained = False
        self.gui_queue = None  # Untuk integrasi update prediksi ke GUI
        self.controller = controller
        self.n_jobs = self.get_optimal_n_jobs(2)  # Default maksimal 2 untuk laptop user

    @staticmethod
    def get_optimal_n_jobs(max_jobs: int = 2) -> int:
        """
        Auto-detect optimal n_jobs based on CPU cores, with a maximum limit.
        """
        try:
            cpu_count = multiprocessing.cpu_count()
            return min(cpu_count, max_jobs)
        except Exception:
            return 1

    def load_data(self):
        df = pd.read_csv(DATA_PATH)
        return df

    def prepare_data(self, df, test_size=0.2, n_lags=10):
        split_ratio = test_size
        if self.controller and hasattr(self.controller, 'training_settings'):
            split_ratio = self.controller.training_settings.get('split_ratio', test_size)
            n_lags = self.controller.training_settings.get('n_lags', n_lags)
        split_idx = int(len(df) * (1 - split_ratio))
        train_raw = df.iloc[:split_idx].copy()
        test_raw = df.iloc[split_idx:].copy()
        # Feature engineering hanya lag dari Number
        train_feat = engineer_features_number_full_anti_leakage(train_raw, n_lags=n_lags)
        test_feat = engineer_features_number_full_anti_leakage(test_raw, n_lags=n_lags)
        return train_feat, test_feat

    def log_environment(self):
        logging.info(f'Python version: {sys.version}')
        logging.info(f'Platform: {platform.platform()}')
        logging.info(f'Optuna version: {optuna.__version__}')
        river_version = importlib.metadata.version('river')
        logging.info(f'River version: {river_version}')

    def search_hyperparameters(self, n_trials: int = 30, n_jobs: Optional[int] = None) -> None:
        """
        Hyperparameter search dengan Optuna, mendukung parallel trials dengan n_jobs.
        """
        jobs: int = self.n_jobs if n_jobs is None else int(n_jobs)
        import gc
        from optuna.samplers import TPESampler
        import importlib.metadata
        optuna.logging.set_verbosity(optuna.logging.WARNING)
        # Logging ke file juga
        file_handler = logging.FileHandler(LOG_PATH)
        file_handler.setLevel(logging.INFO)
        logging.getLogger().addHandler(file_handler)
        self.log_environment()
        logging.info('Memulai hyperparameter search dengan Optuna 4.4.0...')
        df = self.load_data()
        # Ambil setting split_ratio dari controller jika ada
        split_ratio = 0.2
        n_trials_setting = n_trials
        window_sizes = [10, 30, 50]
        n_lags = 10
        threshold_corr = 0.65
        if self.controller and hasattr(self.controller, 'training_settings'):
            split_ratio = self.controller.training_settings.get('split_ratio', split_ratio)
            n_trials_setting = self.controller.training_settings.get('n_trials', n_trials)
            window_sizes = self.controller.training_settings.get('window_sizes', window_sizes)
            n_lags = self.controller.training_settings.get('n_lags', n_lags)
            threshold_corr = self.controller.training_settings.get('threshold_corr', threshold_corr)
        split_idx = int(len(df) * (1 - split_ratio))
        train_raw = df.iloc[:split_idx].copy()
        val_raw = df.iloc[split_idx:].copy()
        train_feat = engineer_features_number_full_anti_leakage(train_raw, n_lags=n_lags)
        val_feat = engineer_features_number_full_anti_leakage(val_raw, n_lags=n_lags)
        # --- BEST PRACTICE: Hanya gunakan fitur dari Number (tidak derived dari Premium, Big/Small, Color) ---
        X_cols = [c for c in train_feat.columns if c != 'Number']
        logging.info(f"[AUDIT] X_cols (fitur input, hanya lag Number): {X_cols}")
        y_col = 'Number'
        # --- AUDIT: Log fitur, distribusi label, dan shape ---
        logging.info(f"[AUDIT] X_cols (fitur input): {X_cols}")
        logging.info(f"[AUDIT] train_feat shape: {train_feat.shape}, val_feat shape: {val_feat.shape}")
        logging.info(f"[AUDIT] Distribusi label train:")
        logging.info(f"\n{train_feat[y_col].value_counts()}")
        logging.info(f"[AUDIT] Distribusi label val:")
        logging.info(f"\n{val_feat[y_col].value_counts()}")
        logging.info(f"[AUDIT] 5 baris pertama train_feat:\n{train_feat.head()}\n")
        logging.info(f"[AUDIT] 5 baris pertama val_feat:\n{val_feat.head()}\n")
        # Cek signature param yang didukung
        supported_params = list(inspect.signature(tree.HoeffdingTreeClassifier.__init__).parameters.keys())
        def objective(trial):
            params = {
                'max_depth': trial.suggest_int('max_depth', 3, 15),
                'grace_period': trial.suggest_int('grace_period', 10, 200),
            }
            if 'delta' in supported_params:
                params['delta'] = trial.suggest_float('delta', 1e-7, 1e-1, log=True)
            if 'tau' in supported_params:
                params['tau'] = trial.suggest_float('tau', 0.0, 1.0)
            model = tree.HoeffdingTreeClassifier(**params)
            # Training
            for idx, row in enumerate(train_feat.iterrows()):
                x = {col: row[1].get(col, 0) for col in X_cols}
                y = int(row[1][y_col])
                model.learn_one(x, y)
                if idx % 1000 == 0 and idx > 0:
                    logging.info(f"[Optuna] Trial {trial.number}: Training progress {idx}/{len(train_feat)}")
            # Akurasi train
            metric_train = metrics.Accuracy()
            for idx, row in enumerate(train_feat.iterrows()):
                x = {col: row[1].get(col, 0) for col in X_cols}
                y = int(row[1][y_col])
                y_pred = model.predict_one(x)
                if y_pred is not None:
                    metric_train.update(y, y_pred)
                if idx % 1000 == 0 and idx > 0:
                    logging.info(f"[Optuna] Trial {trial.number}: Train acc progress {idx}/{len(train_feat)}")
            train_acc = metric_train.get()
            # Akurasi val
            metric_val = metrics.Accuracy()
            for idx, row in enumerate(val_feat.iterrows()):
                x = {col: row[1].get(col, 0) for col in X_cols}
                y = int(row[1][y_col])
                y_pred = model.predict_one(x)
                if y_pred is not None:
                    metric_val.update(y, y_pred)
                if idx % 1000 == 0 and idx > 0:
                    logging.info(f"[Optuna] Trial {trial.number}: Validation progress {idx}/{len(val_feat)}")
            val_acc = metric_val.get()
            trial.report(val_acc, step=0)
            # Prune trial jika overfit
            if train_acc - val_acc > 0.1:
                raise optuna.TrialPruned(f"Overfitting detected: train={train_acc}, val={val_acc}")
            if trial.should_prune():
                raise optuna.TrialPruned()
            return 1 - val_acc  # minimize 1-acc
        def logging_callback(study, frozen_trial):
            # Log setiap trial selesai
            logging.info(f"Trial {frozen_trial.number} finished with value: {frozen_trial.value} and params: {frozen_trial.params}")
            previous_best_value = study.user_attrs.get("previous_best_value", None)
            if previous_best_value != study.best_value:
                study.set_user_attr("previous_best_value", study.best_value)
                logging.info(f"[BEST] Trial {frozen_trial.number} finished with new best value: {frozen_trial.value} and params: {frozen_trial.params}")
            # Update progress bar di GUI (jika ada)
            if self.gui_queue is not None:
                n_trials = study._n_trials if hasattr(study, '_n_trials') else study.trials[-1].number + 1
                progress = (frozen_trial.number + 1) / n_trials
                self.gui_queue.put({
                    'type': 'progress_update',
                    'value': progress,
                    'eta': f"Trial {frozen_trial.number+1}/{n_trials}",
                    'bar': None,
                    'label': None
                })
        # Simpan study ke SQLite agar bisa dipantau dashboard
        storage = "sqlite:///optuna_study.db"
        sampler = TPESampler(seed=42)
        study = optuna.create_study(direction='minimize', sampler=sampler, storage=storage)
        study.optimize(objective, n_trials=n_trials_setting, callbacks=[logging_callback], gc_after_trial=True, n_jobs=jobs)
        best_params = study.best_params
        best_acc = 1 - study.best_value
        river_version = importlib.metadata.version('river')
        meta = {
            'best_params': best_params,
            'best_acc': best_acc,
            'datetime': datetime.datetime.now().isoformat(),
            'optuna_version': optuna.__version__,
            'river_version': river_version,
            'python_version': sys.version,
            'platform': platform.platform(),
        }
        with open(BEST_PARAMS_PATH, 'w') as f:
            json.dump(best_params, f)
        with open(BEST_PARAMS_META_PATH, 'w') as f:
            json.dump(meta, f)
        logging.info(f"Best params: {best_params}, val acc={best_acc:.4f}")
        logging.info(f"Best params disimpan di {BEST_PARAMS_PATH}")
        logging.info(f"Meta best params disimpan di {BEST_PARAMS_META_PATH}")
        # Notifikasi ke GUI jika tuning selesai
        if self.gui_queue is not None:
            self.gui_queue.put({'type': 'log', 'record': f'Hyperparameter search selesai. Best params: {best_params}, val acc={best_acc:.4f}'})
        logging.getLogger().removeHandler(file_handler)

    def load_best_params(self):
        if os.path.exists(BEST_PARAMS_PATH):
            with open(BEST_PARAMS_PATH, 'r') as f:
                return json.load(f)
        return None

    def train_ensemble(self):
        """Training model dengan best params hasil tuning, logging, anti-leakage, anti-overfitting."""
        import importlib.metadata
        river_version = importlib.metadata.version('river')
        self.log_environment()
        df = self.load_data()
        train, _ = self.prepare_data(df)
        X_cols = [c for c in train.columns if c != 'Number']
        logging.info(f"[AUDIT] X_cols (fitur input, hanya lag Number): {X_cols}")
        best_params = self.load_best_params()
        if best_params:
            logging.info(f"Menggunakan best params hasil Optuna: {best_params}")
            self.model = tree.HoeffdingTreeClassifier(**best_params)
        else:
            self.model = tree.HoeffdingTreeClassifier(max_depth=7)
        n = 0
        for idx, row in train.iterrows():
            x = {col: row[col] for col in X_cols}
            y = int(row['Number'])
            self.model.learn_one(x, y)
            n += 1
            if n % 1000 == 0:
                logging.info(f"Trained on {n} samples...")
        with open(MODEL_PATH, 'wb') as f:
            pickle.dump(self.model, f)
        self.is_trained = True
        logging.info(f"Training selesai. Model disimpan di {MODEL_PATH}")
        # Simpan metadata training
        meta = {
            'params': best_params if best_params else {'max_depth': 7},
            'datetime': datetime.datetime.now().isoformat(),
            'optuna_version': optuna.__version__,
            'river_version': river_version,
            'python_version': sys.version,
            'platform': platform.platform(),
        }
        with open(MODEL_PATH + '.meta.json', 'w') as f:
            json.dump(meta, f)

    def retrain_on_all_data(self):
        """
        Retrain final model pada seluruh data (train+val), best practice untuk deployment.
        Tidak ada data masa depan, tetap anti-leakage (kronologis).
        """
        import importlib.metadata
        river_version = importlib.metadata.version('river')
        self.log_environment()
        df = self.load_data()
        # Gunakan seluruh data untuk training (tanpa split)
        full_feat = engineer_features_number_full_anti_leakage(df)
        X_cols = [c for c in full_feat.columns if c != 'Number']
        logging.info(f"[RETRAIN] X_cols (fitur input, hanya lag Number): {X_cols}")
        best_params = self.load_best_params()
        if best_params:
            logging.info(f"[RETRAIN] Menggunakan best params hasil Optuna: {best_params}")
            self.model = tree.HoeffdingTreeClassifier(**best_params)
        else:
            self.model = tree.HoeffdingTreeClassifier(max_depth=7)
        n = 0
        for idx, row in full_feat.iterrows():
            x = {col: row[col] for col in X_cols}
            y = int(row['Number'])
            self.model.learn_one(x, y)
            n += 1
            if n % 1000 == 0:
                logging.info(f"[RETRAIN] Trained on {n} samples...")
        with open(MODEL_PATH, 'wb') as f:
            pickle.dump(self.model, f)
        self.is_trained = True
        logging.info(f"[RETRAIN] Training selesai pada seluruh data. Model disimpan di {MODEL_PATH}")
        # Simpan metadata training
        meta = {
            'params': best_params if best_params else {'max_depth': 7},
            'datetime': datetime.datetime.now().isoformat(),
            'optuna_version': optuna.__version__,
            'river_version': river_version,
            'python_version': sys.version,
            'platform': platform.platform(),
            'retrain_on_all_data': True
        }
        with open(MODEL_PATH + '.meta.json', 'w') as f:
            json.dump(meta, f)
        if self.gui_queue is not None:
            self.gui_queue.put({'type': 'log', 'record': '[RETRAIN] Model berhasil dilatih ulang pada seluruh data dan disimpan.'})

    def get_train_accuracy(self, train, X_cols):
        metric = metrics.Accuracy()
        for idx, row in train.iterrows():
            x = {col: row[col] for col in X_cols}
            y = int(row['Number'])
            y_pred = self.model.predict_one(x) if self.model is not None else None
            if y_pred is not None:
                metric.update(y, y_pred)
        return metric.get()

    def load_model(self):
        if self.model is None and os.path.exists(MODEL_PATH):
            with open(MODEL_PATH, 'rb') as f:
                self.model = pickle.load(f)
            self.is_trained = True
            logging.info(f"Model loaded from {MODEL_PATH}")

    def evaluate_ensemble(self, threshold=0.7):
        logging.info('Evaluasi online River HoeffdingTreeClassifier...')
        self.load_model()
        df = self.load_data()
        _, test = self.prepare_data(df)
        X_cols = [c for c in test.columns if c not in ['Period', 'Number', 'Big/Small', 'Color', 'Premium']]
        metric = metrics.Accuracy()
        n = 0
        if self.model is None:
            logging.error('Model belum dilatih.')
            return
        for idx, row in test.iterrows():
            x = {col: row[col] for col in X_cols}
            y = int(row['Number'])
            y_pred = self.model.predict_one(x) if self.model is not None else None
            if y_pred is not None:
                metric.update(y, y_pred)
            n += 1
            if n % 1000 == 0:
                logging.info(f"Evaluated {n} samples...")
        test_acc = metric.get()
        logging.info(f"Akurasi online (test): {test_acc:.4f}")
        # Multi-number accuracy (top-N)
        multi_acc = self.evaluate_with_confidence_threshold(threshold=threshold)
        logging.info(f"Akurasi prediksi multi-number (threshold={threshold}): {multi_acc:.4f}")
        # Monitoring overfitting: hitung akurasi train
        df = self.load_data()
        train, _ = self.prepare_data(df)
        train_acc = self.get_train_accuracy(train, X_cols)
        logging.info(f"Akurasi training: {train_acc:.4f}")
        if train_acc - test_acc > 0.1:
            logging.warning(f"PERINGATAN: Gap akurasi train-test terlalu besar (overfitting). Train={train_acc:.4f}, Test={test_acc:.4f}")

    def predict_ensemble(self):
        logging.info('Prediksi satu data (online, threshold dinamis) dengan River HoeffdingTreeClassifier...')
        self.load_model()
        df = self.load_data()
        last_row = df.iloc[[-1]]
        last_feat = engineer_features_number_full_anti_leakage(last_row)
        X_cols = [c for c in last_feat.columns if c != 'Number']
        x = {col: last_feat.iloc[0][col] for col in X_cols}
        if self.model is None:
            logging.warning('Model belum pernah fit, prediksi tidak tersedia.')
            return [], 0.0
        proba = self.model.predict_proba_one(x)  # type: ignore[union-attr]
        if not proba:
            logging.warning('Model belum pernah fit, prediksi tidak tersedia.')
            return [], 0.0
        selected_numbers, total_conf = self._select_numbers_by_threshold(proba, CONFIDENCE_THRESHOLD)
        logging.info(f"Prediksi angka berikutnya (dinamis): {selected_numbers} (total confidence={total_conf:.2f})")
        return selected_numbers, total_conf

    def _select_numbers_by_threshold(self, proba_dict, threshold):
        sorted_items = sorted(proba_dict.items(), key=lambda x: x[1], reverse=True)
        selected = []
        total = 0.0
        for num, prob in sorted_items:
            selected.append(num)
            total += prob
            if total >= threshold:
                break
        return selected, total

    def process_new_data(self, X_dict, y=None):
        self.load_model()
        if self.model is None:
            logging.warning('Model belum pernah fit, prediksi tidak tersedia.')
            return [], 0.0
        proba = self.model.predict_proba_one(X_dict)  # type: ignore[union-attr]
        if not proba:
            logging.warning('Model belum pernah fit, prediksi tidak tersedia.')
            return [], 0.0
        selected_numbers, total_conf = self._select_numbers_by_threshold(proba, CONFIDENCE_THRESHOLD)
        logging.info(f"[Realtime] Prediksi angka (dinamis): {selected_numbers} (total confidence={total_conf:.2f})")
        if y is not None:
            self.model.learn_one(X_dict, y)
            with open(MODEL_PATH, 'wb') as f:
                pickle.dump(self.model, f)
            logging.info(f"Model otomatis di-update dengan data baru (label={y})")
        return selected_numbers, total_conf

    def show_feature_importance(self):
        self.load_model()
        if self.model is None:
            logging.info('Model belum pernah fit.')
            return
        # HoeffdingTreeClassifier di River 0.22.0 tidak punya feature_importances_ dan debug_one
        logging.info('Model tidak mendukung feature importance secara langsung.')

    def show_ensemble_analysis(self, threshold=0.7):
        """
        Analisis model dengan evaluasi multi-number (confidence threshold),
        sehingga confusion matrix dan classification report mencerminkan cara prediksi online.
        Sekaligus tampilkan akurasi prediksi multi-number (top-N accuracy).
        """
        self.load_model()
        df = self.load_data()
        _, test = self.prepare_data(df)
        X_cols = [c for c in test.columns if c not in ['Period', 'Number', 'Big/Small', 'Color', 'Premium']]
        y_true = []
        y_pred = []
        if not isinstance(self.model, tree.HoeffdingTreeClassifier):
            logging.info('Model belum pernah fit.')
            return
        for idx, row in enumerate(test.itertuples(index=False), 1):
            x = {col: getattr(row, col) for col in X_cols}
            y = int(getattr(row, 'Number'))
            if self.model is not None:
                proba = self.model.predict_proba_one(x)  # type: ignore[union-attr]
            else:
                proba = None
            if proba is None:
                continue
            # Pilih beberapa Number hingga total confidence >= threshold
            sorted_items = sorted(proba.items(), key=lambda x: x[1], reverse=True)
            selected = []
            total_conf = 0.0
            for num, prob in sorted_items:
                selected.append(num)
                total_conf += prob
                if total_conf >= threshold:
                    break
            # Untuk confusion matrix/report: prediksi = prediksi utama (top-1 di selected)
            y_pred.append(selected[0] if selected else None)
            y_true.append(y)
            if idx % 1000 == 0:
                logging.info(f"Analysed {idx} samples...")
            # Log prediksi multi-number (opsional, bisa diaktifkan jika ingin)
            # logging.info(f"True: {y}, Prediksi multi-number: {selected}")
        from sklearn.metrics import confusion_matrix, classification_report
        cm = confusion_matrix(y_true, y_pred, labels=self.classes)
        logging.info(f"Confusion Matrix (multi-number, threshold={threshold}):\n{cm}")
        logging.info(f"Classification Report (multi-number, threshold={threshold}):\n{classification_report(y_true, y_pred)}")
        # Multi-number accuracy (top-N)
        multi_acc = self.evaluate_with_confidence_threshold(threshold=threshold)
        logging.info(f"Akurasi prediksi multi-number (threshold={threshold}): {multi_acc:.4f}")

    def evaluate_with_confidence_threshold(self, threshold=0.7):
        """
        Evaluasi model dengan cara yang sama seperti prediksi online:
        - Untuk setiap data test, prediksi beberapa Number hingga total confidence >= threshold
        - Anggap benar jika label sebenarnya ada di list prediksi tersebut
        - Kembalikan akurasi (persentase label test yang tercover oleh list prediksi)
        """
        logging.info(f"Evaluasi online (multi-number, threshold={threshold}) dengan River HoeffdingTreeClassifier...")
        self.load_model()
        df = self.load_data()
        _, test = self.prepare_data(df)
        X_cols = [c for c in test.columns if c != 'Number']
        y_col = 'Number'
        correct = 0
        total = 0
        for idx, row in test.iterrows():
            x = {col: row[col] for col in X_cols}
            y_true = int(row[y_col])
            proba = self.model.predict_proba_one(x)
            # Pilih beberapa Number hingga total confidence >= threshold
            sorted_items = sorted(proba.items(), key=lambda x: x[1], reverse=True)
            selected = []
            total_conf = 0.0
            for num, prob in sorted_items:
                selected.append(num)
                total_conf += prob
                if total_conf >= threshold:
                    break
            if y_true in selected:
                correct += 1
            total += 1
            if total % 1000 == 0 and total > 0:
                logging.info(f"Evaluated {total} samples...")
        acc = correct / total if total > 0 else 0.0
        logging.info(f"Akurasi online (multi-number, threshold={threshold}): {acc:.4f}")
        return acc

    def show_multinumber_accuracy(self, threshold=0.7):
        """
        Tampilkan akurasi prediksi multi-number (top-N accuracy) ke log/console.
        Akurasi ini adalah persentase ronde di mana minimal satu prediksi benar.
        """
        acc = self.evaluate_with_confidence_threshold(threshold=threshold)
        print(f"Akurasi prediksi multi-number (threshold={threshold}): {acc:.4f}")
        logging.info(f"Akurasi prediksi multi-number (threshold={threshold}): {acc:.4f}")

    def start_csv_watcher(self, sleep_time=10):
        def watcher():
            logging.info('[Watcher] Memulai monitoring file CSV untuk data baru...')
            csv_path = DATA_PATH
            last_row_count = 0
            while True:
                try:
                    df = pd.read_csv(csv_path)
                    if len(df) > last_row_count:
                        new_rows = df.iloc[last_row_count:]
                        for _, row in new_rows.iterrows():
                            feat_new = engineer_features_number_full_anti_leakage(pd.DataFrame([row]))
                            X_cols = [c for c in feat_new.columns if c not in ['Period', 'Number', 'Big/Small', 'Color', 'Premium']]
                            X_dict = {col: feat_new.iloc[0][col] for col in X_cols}
                            label = int(row['Number']) if not pd.isnull(row['Number']) else None
                            selected_numbers, total_conf = self.process_new_data(X_dict, y=label)
                            logging.info(f"[Watcher] Prediksi angka dinamis: {selected_numbers} (confidence={total_conf:.2f})")
                            if self.gui_queue is not None:
                                self.gui_queue.put({
                                    'type': 'prediction_update',
                                    'numbers': selected_numbers,
                                    'confidence': total_conf
                                })
                        last_row_count = len(df)
                except Exception as e:
                    logging.error(f"[Watcher] Error: {e}")
                time.sleep(sleep_time)
        t = threading.Thread(target=watcher, daemon=True)
        t.start()
        logging.info('[Watcher] Thread watcher CSV berjalan di background.')

    def run_optuna_search(self, n_trials: int = 30, n_jobs: Optional[int] = None) -> None:
        """
        Wrapper untuk search_hyperparameters agar bisa dipanggil dari GUI/TaskOrchestrator.
        """
        jobs: int = self.n_jobs if n_jobs is None else int(n_jobs)
        self.search_hyperparameters(n_trials=n_trials, n_jobs=jobs) 