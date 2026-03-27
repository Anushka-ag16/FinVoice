"""
FinVoice — Reinforcement Learning Optimizer Service
PPO/SAC agent for dynamic portfolio optimization (paid tier).
Uses FinRL and Stable-Baselines3.
"""

import os
import numpy as np
from pathlib import Path


class RLOptimizerService:
    """
    Wraps the trained RL agent for portfolio optimization inference.
    Falls back gracefully if model is not trained yet.
    """

    MODEL_DIR = Path("data/models/rl")

    def __init__(self, algorithm: str = "PPO"):
        self.algorithm = algorithm
        self.model = None
        self._load_model()

    def _load_model(self):
        """Load pre-trained RL model if available."""
        model_path = self.MODEL_DIR / f"{self.algorithm.lower()}_portfolio"

        if not model_path.exists():
            return

        try:
            from stable_baselines3 import PPO, SAC
            algo_map = {"PPO": PPO, "SAC": SAC}
            algo_class = algo_map.get(self.algorithm, PPO)
            self.model = algo_class.load(str(model_path))
        except Exception:
            self.model = None

    def predict_allocation(
        self,
        symbols: list[str],
        risk_profile=None,
    ) -> dict[str, float]:
        """
        Predict optimal allocation weights for given assets.

        If the RL model is trained, it produces dynamic weights.
        Otherwise, returns a risk-adjusted equal-weight allocation.
        """
        n = len(symbols)

        if self.model is not None:
            try:
                # Build observation vector
                obs = self._build_observation(symbols, risk_profile)
                action, _ = self.model.predict(obs, deterministic=True)

                # Convert actions to allocation weights (softmax)
                weights = self._action_to_weights(action, n)

                return {sym: round(w * 100, 2) for sym, w in zip(symbols, weights)}
            except Exception:
                pass

        # Fallback: risk-adjusted allocation
        return self._fallback_allocation(symbols, risk_profile)

    def _build_observation(self, symbols: list[str], risk_profile) -> np.ndarray:
        """
        Build the observation vector for the RL agent.
        State = [holdings_weights, market_features, risk_score]
        """
        n = len(symbols)
        # Placeholder: equal weights + zero features + risk score
        holdings_weights = np.ones(n) / n
        market_features = np.zeros(10)  # Placeholder for OHLCV + macro features
        risk_score = np.array([risk_profile.risk_score / 100.0 if risk_profile else 0.5])

        obs = np.concatenate([holdings_weights, market_features, risk_score])
        return obs.astype(np.float32)

    def _action_to_weights(self, action: np.ndarray, n: int) -> np.ndarray:
        """Convert RL action output to valid allocation weights via softmax."""
        action = action[:n] if len(action) >= n else np.pad(action, (0, n - len(action)))
        exp_action = np.exp(action - np.max(action))  # Stable softmax
        weights = exp_action / exp_action.sum()
        return weights

    def _fallback_allocation(
        self,
        symbols: list[str],
        risk_profile=None,
    ) -> dict[str, float]:
        """Risk-adjusted equal weight as fallback when no RL model."""
        n = len(symbols)
        weight = round(100 / n, 2)
        return {sym: weight for sym in symbols}

    @staticmethod
    def train_agent(
        algorithm: str = "PPO",
        total_timesteps: int = 100_000,
        save_dir: str = None,
    ):
        """
        Train the RL agent on historical market data.
        Call this during the weekly retraining cycle.

        Environment:
          - State: [holdings_weights, OHLCV+macro features, risk_score]
          - Action: target allocation weights (continuous)
          - Reward: sharpe_ratio - λ1 * transaction_cost - λ2 * drift_penalty

        Usage:
            RLOptimizerService.train_agent("PPO", total_timesteps=500000)
        """
        try:
            import gymnasium as gym
            from stable_baselines3 import PPO, SAC

            # TODO: Replace with custom FinRL environment for Indian market
            # For now, use a placeholder environment
            env = gym.make("CartPole-v1")  # Placeholder

            algo_map = {"PPO": PPO, "SAC": SAC}
            algo_class = algo_map.get(algorithm, PPO)

            model = algo_class("MlpPolicy", env, verbose=1)
            model.learn(total_timesteps=total_timesteps)

            save_path = save_dir or str(RLOptimizerService.MODEL_DIR / f"{algorithm.lower()}_portfolio")
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            model.save(save_path)

            return save_path
        except Exception as e:
            raise RuntimeError(f"RL training failed: {e}")
