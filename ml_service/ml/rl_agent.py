"""
Reinforcement Learning Agent — SAC for Portfolio Optimisation.

Uses Soft Actor-Critic (SAC) from stable-baselines3 with a custom portfolio
environment.  When the agent's confidence (1 - std(action)) drops below a
threshold, a Mean-Variance (MPT) fallback is used instead.

Reward signal: per-step Sharpe ratio improvement.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import gymnasium as gym
import mlflow
import numpy as np
import pandas as pd
import torch
from scipy.optimize import minimize

logger = logging.getLogger(__name__)


def _detect_sac_device() -> torch.device:  # CHANGED
    """Detect best device for SAC, with CUDA fallback for sm_120."""  # CHANGED
    try:  # CHANGED
        if not torch.cuda.is_available():  # CHANGED
            return torch.device("cpu")  # CHANGED
        cc = torch.cuda.get_device_capability()  # CHANGED
        if cc[0] < 8:  # CHANGED
            logger.warning("CUDA compute capability %s < 8.0, using CPU for SAC", cc)  # CHANGED
            return torch.device("cpu")  # CHANGED
        _test = torch.zeros(1, device="cuda")  # CHANGED
        del _test  # CHANGED
        return torch.device("cuda")  # CHANGED
    except Exception as e:  # CHANGED
        logger.warning("CUDA check failed for SAC (%s), using CPU", e)  # CHANGED
        return torch.device("cpu")  # CHANGED


device = _detect_sac_device()  # CHANGED
logger.info(f"SAC using device: {device}")


# ══════════════════════════════════════════════════════════════════════════════
# Custom Portfolio Environment
# ══════════════════════════════════════════════════════════════════════════════
class PortfolioOptimizationEnv(gym.Env):
    """Gymnasium environment for portfolio weight optimisation.

    State: flattened feature vector for all assets at current time step.
    Action: continuous portfolio weights (normalised via softmax).
    Reward: change in running Sharpe ratio.

    Args:
        df: Feature DataFrame with a ``ticker`` column and ``ret_1d`` return.
        initial_amount: Starting portfolio value (default 1,000,000).
        commission: Transaction cost rate (default 0.001 = 10 bps).
    """

    metadata = {"render_modes": []}

    def __init__(
        self,
        df: pd.DataFrame,
        initial_amount: float = 1_000_000,
        commission: float = 0.001,
    ) -> None:
        super().__init__()

        self.df = df.copy()
        self.initial_amount = initial_amount
        self.commission = commission

        self.tickers = sorted(self.df["ticker"].unique().tolist())
        self.n_assets = len(self.tickers)

        if "ret_1d" not in self.df.columns:
            raise ValueError("DataFrame must contain 'ret_1d' column")

        self.dates = sorted(self.df.index.unique())
        self.return_matrix = self._build_return_matrix()

        exclude = {"target_fwd_5d", "ticker", "ret_1d"}
        feature_cols = [c for c in self.df.select_dtypes(include=[np.number]).columns if c not in exclude]
        self.feature_matrix = self._build_feature_matrix(feature_cols)

        n_features = self.feature_matrix.shape[1] if len(self.feature_matrix) > 0 else 10

        self.observation_space = gym.spaces.Box(
            low=-np.inf, high=np.inf, shape=(n_features,), dtype=np.float32,
        )
        self.action_space = gym.spaces.Box(
            low=0.0, high=1.0, shape=(self.n_assets,), dtype=np.float32,
        )

        self.current_step = 0
        self.portfolio_value = initial_amount
        self.returns_history: list[float] = []

    def _build_return_matrix(self) -> np.ndarray:
        """Pivot per-ticker returns into a (T, n_assets) matrix."""
        pivot = self.df.pivot_table(index=self.df.index, columns="ticker", values="ret_1d")
        pivot = pivot.reindex(columns=self.tickers).fillna(0.0)
        return pivot.values.astype(np.float32)

    def _build_feature_matrix(self, feature_cols: list[str]) -> np.ndarray:
        """Aggregate features across tickers for each date."""
        if not feature_cols:
            return np.zeros((len(self.dates), 10), dtype=np.float32)

        grouped = self.df.groupby(self.df.index)[feature_cols].mean()
        grouped = grouped.reindex(self.dates).fillna(0.0)
        return grouped.values.astype(np.float32)

    def reset(
        self,
        seed: int | None = None,
        options: dict | None = None,
    ) -> tuple[np.ndarray, dict]:
        """Reset environment to initial state."""
        super().reset(seed=seed)
        self.current_step = 0
        self.portfolio_value = self.initial_amount
        self.returns_history = []
        obs = self.feature_matrix[0] if len(self.feature_matrix) > 0 else np.zeros(self.observation_space.shape, dtype=np.float32)
        return obs, {}

    def step(self, action: np.ndarray) -> tuple[np.ndarray, float, bool, bool, dict]:
        """Execute one trading step."""
        weights = np.exp(action) / np.exp(action).sum()

        if self.current_step < len(self.return_matrix):
            asset_returns = self.return_matrix[self.current_step]
        else:
            asset_returns = np.zeros(self.n_assets, dtype=np.float32)

        portfolio_return = float(np.dot(weights, asset_returns))
        portfolio_return -= self.commission * float(np.sum(np.abs(weights - 1.0 / self.n_assets)))

        self.portfolio_value *= (1 + portfolio_return)
        self.returns_history.append(portfolio_return)

        if len(self.returns_history) > 1:
            returns_arr = np.array(self.returns_history)
            sharpe = returns_arr.mean() / (returns_arr.std() + 1e-8) * np.sqrt(252)
            prev_returns = np.array(self.returns_history[:-1])
            prev_sharpe = prev_returns.mean() / (prev_returns.std() + 1e-8) * np.sqrt(252)
            reward = float(sharpe - prev_sharpe)
        else:
            reward = portfolio_return

        self.current_step += 1
        terminated = self.current_step >= len(self.return_matrix)
        truncated = False

        obs = (
            self.feature_matrix[min(self.current_step, len(self.feature_matrix) - 1)]
            if len(self.feature_matrix) > 0
            else np.zeros(self.observation_space.shape, dtype=np.float32)
        )

        info = {
            "portfolio_value": self.portfolio_value,
            "portfolio_return": portfolio_return,
            "weights": weights.tolist(),
        }

        return obs, reward, terminated, truncated, info


# ══════════════════════════════════════════════════════════════════════════════
# Environment Builder
# ══════════════════════════════════════════════════════════════════════════════
def build_env(
    df: pd.DataFrame,
    initial_amount: float = 1_000_000,
    commission: float = 0.001,
) -> PortfolioOptimizationEnv:
    """Construct a portfolio optimisation environment from a feature DataFrame."""
    env = PortfolioOptimizationEnv(
        df=df,
        initial_amount=initial_amount,
        commission=commission,
    )
    logger.info(
        "Environment built: %d assets, %d time steps, initial=%.0f",
        env.n_assets, len(env.dates), initial_amount,
    )
    return env


# ══════════════════════════════════════════════════════════════════════════════
# SAC Training
# ══════════════════════════════════════════════════════════════════════════════
def train_sac(
    env: PortfolioOptimizationEnv,
    total_timesteps: int = 500_000,
) -> Any:
    """Train a Soft Actor-Critic agent on the portfolio environment.

    Falls back to CPU if CUDA fails at runtime (e.g. sm_120 not supported).

    Args:
        env: ``PortfolioOptimizationEnv`` instance.
        total_timesteps: Total training steps.

    Returns:
        Trained ``stable_baselines3.SAC`` model.
    """
    from stable_baselines3 import SAC

    def _create_and_train(sac_device: str) -> Any:  # CHANGED
        sac = SAC(  # CHANGED
            "MlpPolicy",
            env,
            batch_size=512,
            buffer_size=100_000,
            learning_rate=3e-4,
            learning_starts=1000,
            ent_coef="auto",
            policy_kwargs={"net_arch": [256, 256]},
            device=sac_device,  # CHANGED
            verbose=1,
        )
        sac.learn(total_timesteps=total_timesteps)  # CHANGED
        return sac  # CHANGED

    # Try preferred device first, fall back to CPU on CUDA errors  # CHANGED
    try:  # CHANGED
        sac = _create_and_train(str(device))  # CHANGED
    except Exception as e:  # CHANGED
        if "no kernel image" in str(e).lower() or "cuda" in str(e).lower():  # CHANGED
            logger.warning("SAC CUDA failed (%s), retrying on CPU", e)  # CHANGED
            sac = _create_and_train("cpu")  # CHANGED
        else:  # CHANGED
            raise  # CHANGED

    mlflow.set_experiment("nse-quant-pipeline")
    _nested = mlflow.active_run() is not None
    with mlflow.start_run(run_name="sac_agent", nested=_nested):
        mlflow.log_params({
            "total_timesteps": total_timesteps,
            "batch_size": 512,
            "buffer_size": 100_000,
            "learning_rate": 3e-4,
            "ent_coef": "auto",
            "net_arch": "[256, 256]",
            "device": str(sac.device),  # CHANGED
        })

        # Save model (atomic write)
        save_dir = Path("models") / "sac"
        save_dir.mkdir(parents=True, exist_ok=True)
        tmp_path = save_dir / "sac_model_tmp"
        sac.save(str(tmp_path))

        actual_tmp = Path(str(tmp_path) + ".zip")
        target_path = save_dir / "sac_model.zip"
        if actual_tmp.exists():
            actual_tmp.replace(target_path)
        else:
            sac.save(str(save_dir / "sac_model"))

        if target_path.exists():
            mlflow.log_artifact(str(target_path))

    logger.info("SAC training complete (%d timesteps)", total_timesteps)
    return sac


# ══════════════════════════════════════════════════════════════════════════════
# Prediction & MPT Fallback
# ══════════════════════════════════════════════════════════════════════════════
def predict_weights(
    sac_model: Any,
    state: np.ndarray,
    confidence_threshold: float = 0.6,
) -> np.ndarray:
    """Predict portfolio weights using SAC, with MPT fallback."""
    action, _ = sac_model.predict(state, deterministic=True)
    confidence = 1.0 - float(np.std(action))

    if confidence < confidence_threshold:  # CHANGED
        n_assets = len(action)  # CHANGED
        weights = np.ones(n_assets) / n_assets  # CHANGED
        return weights  # CHANGED

    weights = np.exp(action) / np.exp(action).sum()
    return weights


def mpt_fallback(
    expected_returns: np.ndarray,
    cov_matrix: np.ndarray,
) -> np.ndarray:
    """Compute minimum-variance portfolio weights via Mean-Variance optimisation."""
    n = len(expected_returns)

    def portfolio_variance(w: np.ndarray) -> float:
        return float(w @ cov_matrix @ w)

    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
    bounds = [(0.0, 1.0)] * n
    x0 = np.ones(n) / n

    result = minimize(
        portfolio_variance,
        x0,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
    )

    if result.success:
        return result.x.astype(np.float64)
    else:
        logger.warning("MPT optimisation did not converge: %s. Using equal weights.", result.message)
        return np.ones(n) / n


# ══════════════════════════════════════════════════════════════════════════════
# Backtesting
# ══════════════════════════════════════════════════════════════════════════════
def backtest(
    sac_model: Any,
    env_test: PortfolioOptimizationEnv,
    use_fallback: bool = True,
) -> dict[str, float]:
    """Run a backtest of the SAC agent on a test environment."""
    obs, info = env_test.reset()
    done = False
    returns: list[float] = []
    portfolio_values: list[float] = [env_test.initial_amount]

    if use_fallback:  # CHANGED
        action_probe, _ = sac_model.predict(obs, deterministic=True)  # CHANGED
        confidence = 1.0 - float(np.std(action_probe))  # CHANGED
        if confidence < 0.6:  # CHANGED
            logger.info(  # CHANGED
                "SAC confidence %.3f < threshold %.3f -- using MPT fallback",  # CHANGED
                confidence, 0.6,  # CHANGED
            )  # CHANGED

    while not done:
        if use_fallback:
            weights = predict_weights(sac_model, obs)
        else:
            action, _ = sac_model.predict(obs, deterministic=True)
            weights = np.exp(action) / np.exp(action).sum()

        obs, reward, terminated, truncated, info = env_test.step(weights)
        returns.append(info.get("portfolio_return", 0.0))
        portfolio_values.append(info.get("portfolio_value", portfolio_values[-1]))
        done = terminated or truncated

    returns_arr = np.array(returns)
    portfolio_arr = np.array(portfolio_values)

    sharpe = float(returns_arr.mean() / (returns_arr.std() + 1e-8) * np.sqrt(252))

    peak = np.maximum.accumulate(portfolio_arr)
    drawdown = (peak - portfolio_arr) / (peak + 1e-8)
    max_drawdown = float(drawdown.max())

    total_return = float((portfolio_arr[-1] / portfolio_arr[0]) - 1.0)

    metrics = {
        "sharpe": sharpe,
        "max_drawdown": max_drawdown,
        "total_return": total_return,
    }

    mlflow.set_experiment("nse-quant-pipeline")
    _nested = mlflow.active_run() is not None
    with mlflow.start_run(run_name="sac_backtest", nested=_nested):
        for k, v in metrics.items():
            mlflow.log_metric(k, v)

    if sharpe < 1.0:
        logger.warning(
            "Out-of-sample Sharpe %.2f < 1.0 threshold. "
            "Consider retraining with more data or tuning hyperparameters.",
            sharpe,
        )

    logger.info("Backtest results: sharpe=%.2f, max_dd=%.2f%%, return=%.2f%%",
                sharpe, max_drawdown * 100, total_return * 100)
    return metrics


# ──────────────────────────────────────────────────────────────────────────────
# Smoke Test
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logger.info("=== RL Agent Smoke Test ===")
    logger.info(f"Device: {device}")

    np.random.seed(42)
    n_days = 200
    tickers = ["STOCK_A", "STOCK_B", "STOCK_C"]
    rows = []
    dates = pd.date_range("2023-01-01", periods=n_days, freq="B")

    for ticker in tickers:
        ret = np.random.randn(n_days) * 0.02
        for i, d in enumerate(dates):
            rows.append({
                "date": d,
                "ticker": ticker,
                "ret_1d": ret[i],
                "close": 100 * np.exp(np.cumsum(ret[:i+1])[-1]),
                "volume": np.random.randint(100000, 1000000),
            })

    synth_df = pd.DataFrame(rows).set_index("date")

    split = int(n_days * 0.8)
    train_dates = dates[:split]
    test_dates = dates[split:]

    train_df = synth_df[synth_df.index.isin(train_dates)]
    test_df = synth_df[synth_df.index.isin(test_dates)]

    env_train = build_env(train_df)
    env_test = build_env(test_df)

    obs, info = env_train.reset()
    action = env_train.action_space.sample()
    obs2, reward, term, trunc, info2 = env_train.step(action)
    logger.info("Env step test: reward=%.4f, portfolio_value=%.2f", reward, info2["portfolio_value"])

    exp_ret = np.array([0.1, 0.05, 0.08])
    cov = np.array([
        [0.04, 0.006, 0.002],
        [0.006, 0.09, 0.004],
        [0.002, 0.004, 0.01],
    ])
    mpt_weights = mpt_fallback(exp_ret, cov)
    assert abs(mpt_weights.sum() - 1.0) < 1e-6, f"MPT weights don't sum to 1: {mpt_weights.sum()}"
    logger.info("MPT weights: %s", mpt_weights)

    logger.info("=== Smoke Test PASSED ===")
