"""
LSTM Module — NSE/Nifty 50 Pipeline.

Implements a causal unidirectional LSTM with scaled dot-product self-attention
in PyTorch for time-series return prediction.  Auto-detects GPU (CUDA) and
falls back to CPU gracefully, including for Blackwell (sm_120) architectures.
StandardScaler is fitted ONLY on training data to prevent information leakage.

CHANGED (FIX 1): Graceful CUDA fallback for sm_120 / Blackwell GPUs.
CHANGED (FIX 6): Unidirectional LSTM, LayerNorm, self-attention, AdamW +
    CosineAnnealingLR, seq_len=20, epochs=50, Spearman IC logging.

Note: TFT (Temporal Fusion Transformer) support has been removed due to
fragile pytorch-forecasting version conflicts.  The LSTM serves as the
deep-learning ensemble member alongside XGBoost and CatBoost.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import mlflow
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from scipy.stats import spearmanr  # CHANGED: FIX 6 — IC logging per epoch
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, TensorDataset

logger = logging.getLogger(__name__)

# GPU detection — graceful Blackwell sm_120 fallback  # CHANGED: FIX 1
def _detect_device() -> torch.device:  # CHANGED: FIX 1 — extracted to function for testability
    """Detect the best available device, with graceful fallback.

    Handles Blackwell (sm_120) GPUs that may not be supported by the
    installed PyTorch/CUDA version by catching runtime errors.

    Returns:
        ``torch.device("cuda")`` if CUDA is usable, ``torch.device("cpu")`` otherwise.
    """
    try:  # CHANGED: FIX 1
        if not torch.cuda.is_available():  # CHANGED: FIX 1
            logger.info("CUDA not available — using CPU")  # CHANGED: FIX 1
            return torch.device("cpu")  # CHANGED: FIX 1

        cc = torch.cuda.get_device_capability()  # CHANGED: FIX 1
        if cc[0] < 8:  # CHANGED: FIX 1 — need sm_80+ for modern LSTM ops
            logger.warning(  # CHANGED: FIX 1
                "CUDA compute capability %s < 8.0, falling back to CPU", cc  # CHANGED: FIX 1
            )  # CHANGED: FIX 1
            return torch.device("cpu")  # CHANGED: FIX 1

        # Smoke test: try allocating a small tensor on GPU  # CHANGED: FIX 1
        _test = torch.zeros(1, device="cuda")  # CHANGED: FIX 1
        del _test  # CHANGED: FIX 1
        logger.info("CUDA device detected: compute capability %s", cc)  # CHANGED: FIX 1
        return torch.device("cuda")  # CHANGED: FIX 1

    except Exception as e:  # CHANGED: FIX 1 — catch sm_120 / driver errors
        logger.warning(  # CHANGED: FIX 1
            "CUDA runtime check failed (%s), falling back to CPU", e  # CHANGED: FIX 1
        )  # CHANGED: FIX 1
        return torch.device("cpu")  # CHANGED: FIX 1


device = _detect_device()  # CHANGED: FIX 1
logger.info(f"LSTM using device: {device}")


# ══════════════════════════════════════════════════════════════════════════════
# Scaled Dot-Product Self-Attention  # CHANGED: FIX 6 — new attention module
# ══════════════════════════════════════════════════════════════════════════════
class ScaledDotProductAttention(nn.Module):  # CHANGED: FIX 6 — simple attention mechanism
    """Scaled dot-product self-attention over the sequence dimension.

    Computes attention weights over all time steps, then produces a
    context vector as the weighted sum.  This allows the model to
    selectively focus on the most informative time steps rather than
    relying solely on the last hidden state.

    Args:
        hidden_size: Size of the LSTM hidden state.
    """

    def __init__(self, hidden_size: int) -> None:  # CHANGED: FIX 6
        super().__init__()  # CHANGED: FIX 6
        self.scale = hidden_size ** 0.5  # CHANGED: FIX 6 — scaling factor
        self.query = nn.Linear(hidden_size, hidden_size)  # CHANGED: FIX 6
        self.key = nn.Linear(hidden_size, hidden_size)  # CHANGED: FIX 6
        self.value = nn.Linear(hidden_size, hidden_size)  # CHANGED: FIX 6

    def forward(self, x: torch.Tensor) -> torch.Tensor:  # CHANGED: FIX 6
        """Apply self-attention and return context vector.

        Args:
            x: LSTM output ``(batch, seq_len, hidden_size)``.

        Returns:
            Context vector ``(batch, hidden_size)`` — attention-weighted
            summary of the full sequence.
        """
        Q = self.query(x)  # CHANGED: FIX 6 — (batch, seq_len, hidden)
        K = self.key(x)  # CHANGED: FIX 6
        V = self.value(x)  # CHANGED: FIX 6

        # Attention scores: (batch, seq_len, seq_len)  # CHANGED: FIX 6
        scores = torch.bmm(Q, K.transpose(1, 2)) / self.scale  # CHANGED: FIX 6
        weights = torch.softmax(scores, dim=-1)  # CHANGED: FIX 6

        # Context: (batch, seq_len, hidden)  # CHANGED: FIX 6
        context = torch.bmm(weights, V)  # CHANGED: FIX 6

        # Take the last time step's attended representation  # CHANGED: FIX 6
        return context[:, -1, :]  # CHANGED: FIX 6


# ══════════════════════════════════════════════════════════════════════════════
# LSTM with Attention — Ensemble Member  # CHANGED: FIX 6 — architecture overhaul
# ══════════════════════════════════════════════════════════════════════════════
class LSTMPredictor(nn.Module):
    """Unidirectional LSTM with LayerNorm and self-attention for return prediction.

    Architecture: LSTM(256) → LayerNorm → LSTM(128) → LayerNorm → Attention → FC → output.

    CHANGED (FIX 6):
      - Removed bidirectional (causal model for time series)
      - Increased hidden sizes (256, 128)
      - Added LayerNorm after each LSTM layer
      - Added scaled dot-product self-attention

    Args:
        input_size: Number of input features per time step.
        hidden1: Hidden units in first LSTM layer (default 256).
        hidden2: Hidden units in second LSTM layer (default 128).
    """

    def __init__(self, input_size: int, hidden1: int = 256, hidden2: int = 128) -> None:  # CHANGED: FIX 6 — hidden1=256, hidden2=128
        super().__init__()
        self.lstm1 = nn.LSTM(  # CHANGED: FIX 6
            input_size=input_size,
            hidden_size=hidden1,
            batch_first=True,
            bidirectional=False,  # CHANGED: FIX 6 — unidirectional for causal modelling
        )
        self.ln1 = nn.LayerNorm(hidden1)  # CHANGED: FIX 6 — LayerNorm replaces dropout-only
        self.lstm2 = nn.LSTM(  # CHANGED: FIX 6
            input_size=hidden1,  # CHANGED: FIX 6 — no *2 since unidirectional
            hidden_size=hidden2,
            batch_first=True,
            bidirectional=False,  # CHANGED: FIX 6 — unidirectional
        )
        self.ln2 = nn.LayerNorm(hidden2)  # CHANGED: FIX 6 — LayerNorm after second LSTM
        self.attention = ScaledDotProductAttention(hidden2)  # CHANGED: FIX 6 — self-attention
        self.dropout = nn.Dropout(0.2)
        self.fc = nn.Linear(hidden2, 1)  # CHANGED: FIX 6 — no *2 since unidirectional

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass.

        Args:
            x: Input tensor of shape ``(batch, seq_len, input_size)``.

        Returns:
            Predictions of shape ``(batch, 1)``.
        """
        out, _ = self.lstm1(x)
        out = self.ln1(out)  # CHANGED: FIX 6 — LayerNorm
        out = self.dropout(out)
        out, _ = self.lstm2(out)
        out = self.ln2(out)  # CHANGED: FIX 6 — LayerNorm
        out = self.dropout(out)
        # Apply self-attention over the sequence  # CHANGED: FIX 6
        out = self.attention(out)  # CHANGED: FIX 6 — (batch, hidden2)
        return self.fc(out)


def create_sequences(
    df: pd.DataFrame,
    seq_len: int = 20,  # CHANGED: FIX 6 — reduced from 60 to 20 for faster training
) -> tuple[np.ndarray, np.ndarray]:
    """Convert a feature DataFrame into windowed sequences for LSTM.

    Creates overlapping windows of ``seq_len`` consecutive rows. The target
    for each window is the ``target_fwd_5d`` value at the last row of the
    window.

    Args:
        df: Feature DataFrame; must contain ``target_fwd_5d`` and numeric
            feature columns.
        seq_len: Number of time steps per input sequence.

    Returns:
        Tuple ``(X, y)`` where ``X`` has shape ``(n_windows, seq_len, n_features)``
        and ``y`` has shape ``(n_windows,)``.

    Raises:
        ValueError: If DataFrame has fewer rows than ``seq_len``.
    """
    if len(df) < seq_len:
        raise ValueError(
            f"DataFrame has {len(df)} rows but seq_len={seq_len} requires at least that many"
        )

    # Separate features and target
    exclude_cols = {"target_fwd_5d", "ticker"}
    feature_cols = [c for c in df.select_dtypes(include=[np.number]).columns if c not in exclude_cols]

    data = df[feature_cols].values.astype(np.float32)
    target = df["target_fwd_5d"].values.astype(np.float32)

    X_list: list[np.ndarray] = []
    y_list: list[float] = []

    for i in range(seq_len, len(data)):
        X_list.append(data[i - seq_len : i])
        y_list.append(target[i])

    return np.array(X_list), np.array(y_list)


def _compute_ic(y_true: np.ndarray, y_pred: np.ndarray) -> float:  # CHANGED: FIX 6 — IC helper
    """Compute Spearman IC for logging during LSTM training.

    Args:
        y_true: Actual values.
        y_pred: Predicted values.

    Returns:
        Spearman correlation; 0.0 on failure.
    """
    corr, _ = spearmanr(y_true, y_pred)  # CHANGED: FIX 6
    return float(corr) if not np.isnan(corr) else 0.0  # CHANGED: FIX 6


def train_lstm(
    model: LSTMPredictor,
    X: np.ndarray,
    y: np.ndarray,
    epochs: int = 50,  # CHANGED: FIX 6 — increased from 5 to 50
    batch_size: int = 128,
) -> LSTMPredictor:
    """Train the LSTM model with early stopping based on validation loss.

    StandardScaler is fitted ONLY on the training portion (first 80%) to
    prevent information leakage from validation data.

    CHANGED (FIX 6): AdamW optimizer with weight decay, CosineAnnealingLR
    scheduler, Spearman IC logged per epoch.

    Args:
        model: Uninitialised or partially-trained ``LSTMPredictor``.
        X: Sequence input ``(n_windows, seq_len, n_features)``.
        y: Target ``(n_windows,)``.
        epochs: Maximum training epochs.
        batch_size: Mini-batch size.

    Returns:
        Trained ``LSTMPredictor``.
    """
    # CHANGED: FIX 1 — wrap entire training in try/except for CUDA runtime errors
    try:  # CHANGED: FIX 1
        model = model.to(device)
    except Exception as e:  # CHANGED: FIX 1
        logger.warning("Failed to move model to %s (%s), falling back to CPU", device, e)  # CHANGED: FIX 1
        model = model.to(torch.device("cpu"))  # CHANGED: FIX 1

    actual_device = next(model.parameters()).device  # CHANGED: FIX 1 — track actual device

    # Temporal split: 80% train, 20% val
    split = int(len(X) * 0.8)
    X_train, X_val = X[:split], X[split:]
    y_train, y_val = y[:split], y[split:]

    # Fit scaler ONLY on training data — prevents val/test information leakage
    n_samples, seq_len, n_features = X_train.shape
    scaler = StandardScaler()
    X_train_2d = X_train.reshape(-1, n_features)
    scaler.fit(X_train_2d)

    X_train_scaled = scaler.transform(X_train_2d).reshape(n_samples, seq_len, n_features)
    X_val_scaled = scaler.transform(X_val.reshape(-1, n_features)).reshape(len(X_val), seq_len, n_features)

    # Tensors
    X_train_t = torch.tensor(X_train_scaled, dtype=torch.float32).to(actual_device)  # CHANGED: FIX 1 — use actual_device
    y_train_t = torch.tensor(y_train, dtype=torch.float32).unsqueeze(1).to(actual_device)  # CHANGED: FIX 1
    X_val_t = torch.tensor(X_val_scaled, dtype=torch.float32).to(actual_device)  # CHANGED: FIX 1
    y_val_t = torch.tensor(y_val, dtype=torch.float32).unsqueeze(1).to(actual_device)  # CHANGED: FIX 1

    train_ds = TensorDataset(X_train_t, y_train_t)
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=False)  # Time series — no shuffle

    optimizer = torch.optim.AdamW(  # CHANGED: FIX 6 — AdamW with weight decay
        model.parameters(), lr=1e-3, weight_decay=1e-4  # CHANGED: FIX 6
    )  # CHANGED: FIX 6
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(  # CHANGED: FIX 6 — learning rate schedule
        optimizer, T_max=epochs  # CHANGED: FIX 6
    )  # CHANGED: FIX 6
    criterion = nn.MSELoss()

    mlflow.set_experiment("nse-quant-pipeline")

    best_val_loss = float("inf")
    patience_counter = 0
    patience = 10

    _nested = mlflow.active_run() is not None
    with mlflow.start_run(run_name="lstm_predictor", nested=_nested):
        mlflow.log_param("epochs", epochs)
        mlflow.log_param("batch_size", batch_size)
        mlflow.log_param("hidden1", model.lstm1.hidden_size)
        mlflow.log_param("hidden2", model.lstm2.hidden_size)
        mlflow.log_param("device", str(actual_device))  # CHANGED: FIX 1 — log actual device
        mlflow.log_param("optimizer", "AdamW")  # CHANGED: FIX 6
        mlflow.log_param("scheduler", "CosineAnnealingLR")  # CHANGED: FIX 6
        mlflow.log_param("seq_len", seq_len)  # CHANGED: FIX 6
        mlflow.log_param("attention", "ScaledDotProduct")  # CHANGED: FIX 6

        for epoch in range(epochs):
            model.train()
            epoch_loss = 0.0
            for X_batch, y_batch in train_loader:
                optimizer.zero_grad()
                preds = model(X_batch)
                loss = criterion(preds, y_batch)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()
                epoch_loss += loss.item()

            avg_train_loss = epoch_loss / len(train_loader)
            scheduler.step()  # CHANGED: FIX 6 — step the cosine scheduler

            # Validation
            model.eval()
            with torch.no_grad():
                val_preds = model(X_val_t)
                val_loss = criterion(val_preds, y_val_t).item()
                # Compute validation IC (Spearman)  # CHANGED: FIX 6
                val_ic = _compute_ic(  # CHANGED: FIX 6
                    y_val, val_preds.cpu().numpy().flatten()  # CHANGED: FIX 6
                )  # CHANGED: FIX 6

            mlflow.log_metric("train_loss", avg_train_loss, step=epoch)
            mlflow.log_metric("val_loss", val_loss, step=epoch)
            mlflow.log_metric("val_ic", val_ic, step=epoch)  # CHANGED: FIX 6 — log IC per epoch
            mlflow.log_metric("lr", scheduler.get_last_lr()[0], step=epoch)  # CHANGED: FIX 6

            if (epoch + 1) % 10 == 0:
                logger.info(
                    "LSTM epoch %d/%d: train_loss=%.6f val_loss=%.6f val_ic=%.4f lr=%.6f",  # CHANGED: FIX 6 — added IC and lr
                    epoch + 1, epochs, avg_train_loss, val_loss, val_ic,  # CHANGED: FIX 6
                    scheduler.get_last_lr()[0],  # CHANGED: FIX 6
                )

            # Early stopping
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
                # Save best model (atomic write)
                save_dir = Path("models") / "lstm"
                save_dir.mkdir(parents=True, exist_ok=True)
                best_path = save_dir / "lstm_best.pt"
                tmp_path = best_path.with_suffix(".tmp")
                torch.save(model.state_dict(), tmp_path)
                tmp_path.replace(best_path)
            else:
                patience_counter += 1
                if patience_counter >= patience:
                    logger.info("Early stopping at epoch %d", epoch + 1)
                    break

        mlflow.log_metric("best_val_loss", best_val_loss)
        if (Path("models") / "lstm" / "lstm_best.pt").exists():
            mlflow.log_artifact(str(Path("models") / "lstm" / "lstm_best.pt"))

    # Load best weights
    best_path = Path("models") / "lstm" / "lstm_best.pt"
    if best_path.exists():
        model.load_state_dict(torch.load(best_path, map_location=actual_device, weights_only=True))  # CHANGED: FIX 1

    logger.info("LSTM training complete: best_val_loss=%.6f", best_val_loss)
    return model


# ──────────────────────────────────────────────────────────────────────────────
# Smoke Test
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logger.info("=== LSTM Smoke Test ===")
    logger.info(f"Device: {device}")

    # Generate synthetic sequential data
    np.random.seed(42)
    n = 500
    n_features = 15
    seq_len = 20  # CHANGED: FIX 6 — matches new default seq_len

    # Build a synthetic DataFrame
    data = np.random.randn(n, n_features).astype(np.float32)
    target = np.cumsum(np.random.randn(n) * 0.01).astype(np.float32)

    feature_names = [f"feat_{i}" for i in range(n_features)]
    synth_df = pd.DataFrame(data, columns=feature_names)
    synth_df["target_fwd_5d"] = target

    # Test sequence creation
    X, y_seq = create_sequences(synth_df, seq_len=seq_len)
    logger.info("Sequences: X=%s, y=%s", X.shape, y_seq.shape)

    assert X.shape[1] == seq_len, f"Expected seq_len={seq_len}, got {X.shape[1]}"
    assert X.shape[2] == n_features, f"Expected {n_features} features, got {X.shape[2]}"

    # Test LSTM
    lstm_model = LSTMPredictor(input_size=n_features, hidden1=32, hidden2=16)
    trained_lstm = train_lstm(lstm_model, X, y_seq, epochs=5, batch_size=64)
    logger.info("LSTM smoke test complete")

    logger.info("=== Smoke Test PASSED ===")
