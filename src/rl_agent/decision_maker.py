import logging
import os
import torch
import joblib
from src.utils.model_helpers import load_model_robust
from src.features.feature_engineering import create_features

class DecisionMaker:
    def __init__(self, config):
        self.config = config
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.policy_net = None
        self.scaler = None
        self.action_map = self._create_action_map()

    def _create_action_map(self):
        """Membuat pemetaan dari indeks aksi ke string yang dapat dibaca manusia."""
        bet_percentages = self.config.get('bet_percentages', [0.01, 0.025])
        action_map = {0: 'Hold'}
        num_bet_levels = len(bet_percentages)
        for i in range(num_bet_levels):
            action_map[i + 1] = f"Bet Small ({bet_percentages[i]*100:.1f}%)"
            action_map[i + 1 + num_bet_levels] = f"Bet Big ({bet_percentages[i]*100:.1f}%)"
        return action_map

    def load_model(self):
        """Memuat model RL dan scaler fitur."""
        logging.info("Memuat model Decision Maker dan scaler...")
        model_path = os.path.join(self.config['model_dir'], self.config['best_model_name'])
        self.policy_net = load_model_robust(model_path, self.device)
        if self.policy_net is None:
            logging.error("Gagal memuat model policy network. DecisionMaker tidak dapat berfungsi.")
            return False

        scaler_path = os.path.join(self.config['model_dir'], self.config.get('scaler_name', 'feature_scaler.joblib'))
        if os.path.exists(scaler_path):
            self.scaler = joblib.load(scaler_path)
            logging.info("Feature scaler berhasil dimuat.")
        else:
            logging.error(f"Feature scaler tidak ditemukan di {scaler_path}. Agen tidak dapat berjalan tanpanya.")
            return False
        
        return True

    def get_action(self, historical_data):
        """Mendapatkan aksi dari model berdasarkan data historis."""
        if self.policy_net is None or self.scaler is None:
            logging.error("Model atau scaler tidak dimuat. Mengembalikan 'Hold'.")
            return 0, "Hold (Model Error)"

        try:
            # 1. Buat fitur dari data historis
            features_df, _ = create_features(historical_data.copy())
            
            # 2. Scaling fitur
            scaled_features_np = self.scaler.transform(features_df)
            
            # 3. Dapatkan state terbaru (baris terakhir)
            state = scaled_features_np[-1]
            
            # 4. Konversi ke tensor PyTorch
            state_tensor = torch.tensor(state, dtype=torch.float32, device=self.device).unsqueeze(0)
            
            # 5. Dapatkan aksi dari policy network
            with torch.no_grad():
                action_idx = self.policy_net(state_tensor).max(1)[1].item()
            
            action_str = self.action_map.get(action_idx, "Unknown")
            logging.info(f"DecisionMaker memilih aksi: {action_str} (indeks: {action_idx})")
            
            return action_idx, action_str
        except Exception as e:
            logging.error(f"Gagal mendapatkan aksi dari model: {e}", exc_info=True)
            return 0, "Hold (Decision Error)"