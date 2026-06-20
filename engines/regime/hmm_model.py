import os
import pickle
import numpy as np
import pandas as pd
from hmmlearn import hmm
from typing import Dict, Any
import warnings

from sklearn.preprocessing import StandardScaler
from core.base_engine import BaseEngine
from core.types import DataPacket, EngineType

# Suppress sklearn/hmmlearn warnings for cleaner output
warnings.filterwarnings("ignore")

class RegimeHMM(BaseEngine):
    """
    Hidden Markov Model for Market Regime Detection.
    Classifies the market into 5 latent states with probabilistic outputs,
    using strictly filtered probabilities to prevent look-ahead bias.
    """
    
    def __init__(self):
        super().__init__(engine_type=EngineType.REGIME)
        self.n_components = 5
        self.model = hmm.GaussianHMM(
            n_components=self.n_components, 
            covariance_type="full", 
            n_iter=100,
            random_state=42
        )
        self.scaler = StandardScaler()
        self.state_map = {}
        self.is_trained = False
        self.recent_probabilities = []
        
    def train(self, features_df: pd.DataFrame):
        """
        Trains the HMM. In a walk-forward setting, features_df contains ONLY
        data up to the current time T.
        
        Expected 8 features for Indian Markets:
        [nifty_20d_ret, nifty_60d_ret, vix_lvl, vix_10d_roc, 
         usdinr_20d_roc, bank_rs, midcap_rs, bond_yield_10y]
        """
        if features_df.shape[1] != 8:
            raise ValueError(f"Expected 8 features, got {features_df.shape[1]}")
            
        # 1. Scale features to force EM algorithm convergence
        scaled_features = self.scaler.fit_transform(features_df.values)
        
        # 2. Train Gaussian HMM
        self.model.fit(scaled_features)
        
        # 3. Deterministically sort the states to fix label switching
        self._map_states()
        
        self.is_trained = True

    def load_model(self, model_path: str):
        """Loads a pre-trained serialized model."""
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"HMM model not found at {model_path}")
            
        with open(model_path, 'rb') as f:
            data = pickle.load(f)
            
        self.model = data['model']
        self.scaler = data['scaler']
        self.state_map = data['state_map']
        self.is_trained = True
        
    def _map_states(self):
        """
        hmmlearn assigns states randomly. We sort them deterministically:
        Highest mean Nifty return = S1 (Bull), Lowest = S5 (Crisis).
        """
        # model.means_ has shape (n_components, n_features). index 0 is nifty_20d_ret
        nifty_returns = self.model.means_[:, 0]
        sorted_indices = np.argsort(nifty_returns)[::-1] # Highest to lowest
        self.state_map = {internal: ordered for ordered, internal in enumerate(sorted_indices)}
        
    def evaluate(self, data_packet: DataPacket, recent_history_df: pd.DataFrame = None) -> Dict[str, Any]:
        """
        Predicts current regime probabilities using the sequence of recent history 
        up to today (Filtered Probabilities).
        """
        if not self.is_trained:
            raise ValueError("RegimeHMM must be trained before evaluation.")
            
        # For true filtered probabilities, hmmlearn needs a sequence of observations
        # ending with the current observation. We extract the posterior of the LAST step.
        if recent_history_df is None or recent_history_df.empty:
            raise ValueError("Recent history DataFrame is required to evaluate the HMM.")
        else:
            recent_features = recent_history_df.values
            
        # Apply the fitted scaler to live data
        scaled_features = self.scaler.transform(recent_features)
            
        # predict_proba returns the posterior probability of each state for each time step
        posterior_sequence = self.model.predict_proba(scaled_features)
        raw_probs = posterior_sequence[-1] # Only use the latest step (filtered)
        
        # Map random internal probabilities to our deterministic S1 -> S5 order
        ordered_probs = np.zeros(self.n_components)
        for internal_idx, prob in enumerate(raw_probs):
            ordered_probs[self.state_map[internal_idx]] = prob
            
        current_probs = ordered_probs
        
        self.recent_probabilities.append(current_probs)
        if len(self.recent_probabilities) > 5:
            self.recent_probabilities.pop(0)
            
        transition_active = self._detect_rapid_transition()
        dominant_state = int(np.argmax(current_probs))
        
        weights = self._calculate_continuous_weights(current_probs)
        
        # Apply uncertainty penalty for transitioning markets
        transition_penalty = 15 if transition_active else 0
        
        return {
            "probabilities": {
                "S1_Bull_Trending": float(current_probs[0]),
                "S2_Bull_Volatile": float(current_probs[1]),
                "S3_Sideways": float(current_probs[2]),
                "S4_Bear_Declining": float(current_probs[3]),
                "S5_Crisis": float(current_probs[4])
            },
            "dominant_state": dominant_state,
            "transition_active": transition_active,
            "engine_weights": weights,
            "transition_penalty": transition_penalty
        }
        
    def _detect_rapid_transition(self) -> bool:
        """Flags if any state probability shifted > 0.25 in 5 days."""
        if len(self.recent_probabilities) < 5:
            return False
            
        current = self.recent_probabilities[-1]
        oldest = self.recent_probabilities[0]
        
        shifts = np.abs(current - oldest)
        return bool(np.any(shifts > 0.25))
        
    def _calculate_continuous_weights(self, probs: np.ndarray) -> Dict[str, float]:
        """
        Calculates Bull and Bear base weights as a continuous function of the posterior.
        """
        # Based on corrected specification mapping
        bull_w = (0.65 * probs[0] + 0.50 * probs[1] + 0.45 * probs[2] + 
                  0.25 * probs[3] + 0.15 * probs[4])
                  
        bear_w = (0.25 * probs[0] + 0.35 * probs[1] + 0.40 * probs[2] + 
                  0.60 * probs[3] + 0.70 * probs[4])
                  
        total = bull_w + bear_w
        return {
            "bull_base_weight": float(bull_w / total),
            "bear_base_weight": float(bear_w / total)
        }
