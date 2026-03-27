"""
FinVoice — LSTM Time-Series Model
PyTorch LSTM for return prediction using sequential OHLCV + macro features.
"""

import logging
import numpy as np
import torch
import torch.nn as nn
from pathlib import Path

logger = logging.getLogger(__name__)

MODEL_DIR = Path("data/models")
MODEL_DIR.mkdir(parents=True, exist_ok=True)


class LSTMReturnPredictor(nn.Module):
    """
    LSTM model for time-series return prediction.
    Input: 30-day window of OHLCV + macro features per asset.
    Output: predicted return (mean + variance for confidence).
    """

    def __init__(
        self,
        input_size: int = 18,    # Number of features per time step
        hidden_size: int = 128,
        num_layers: int = 2,
        dropout: float = 0.2,
    ):
        super().__init__()

        self.hidden_size = hidden_size
        self.num_layers = num_layers

        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
        )

        self.fc_mean = nn.Sequential(
            nn.Linear(hidden_size, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, 1),
        )

        self.fc_var = nn.Sequential(
            nn.Linear(hidden_size, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, 1),
            nn.Softplus(),  # Ensure positive variance
        )

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass.
        x: (batch, seq_len, input_size)
        Returns: (mean, variance) each of shape (batch, 1)
        """
        lstm_out, _ = self.lstm(x)
        last_hidden = lstm_out[:, -1, :]  # Take last time step

        mean = self.fc_mean(last_hidden)
        var = self.fc_var(last_hidden) + 1e-6  # Numerical stability

        return mean, var


class LSTMTrainer:
    """Training and inference wrapper for LSTM model."""

    def __init__(
        self,
        input_size: int = 18,
        sequence_length: int = 30,
        device: str = None,
    ):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.sequence_length = sequence_length
        self.model = LSTMReturnPredictor(input_size=input_size).to(self.device)

    def train(
        self,
        train_sequences: np.ndarray,
        train_targets: np.ndarray,
        val_sequences: np.ndarray = None,
        val_targets: np.ndarray = None,
        epochs: int = 50,
        batch_size: int = 64,
        learning_rate: float = 1e-3,
    ) -> dict:
        """
        Train the LSTM model.
        train_sequences: (N, seq_len, features)
        train_targets: (N,)
        """
        from torch.utils.data import DataLoader, TensorDataset

        X = torch.FloatTensor(train_sequences).to(self.device)
        y = torch.FloatTensor(train_targets).unsqueeze(1).to(self.device)

        dataset = TensorDataset(X, y)
        loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

        optimizer = torch.optim.Adam(self.model.parameters(), lr=learning_rate)
        best_val_loss = float("inf")
        history = {"train_loss": [], "val_loss": []}

        for epoch in range(epochs):
            self.model.train()
            epoch_loss = 0.0

            for batch_X, batch_y in loader:
                optimizer.zero_grad()
                mean, var = self.model(batch_X)

                # Gaussian negative log-likelihood loss
                loss = 0.5 * (torch.log(var) + (batch_y - mean) ** 2 / var).mean()

                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                optimizer.step()

                epoch_loss += loss.item()

            avg_loss = epoch_loss / len(loader)
            history["train_loss"].append(avg_loss)

            # Validation
            if val_sequences is not None:
                val_loss = self._validate(val_sequences, val_targets)
                history["val_loss"].append(val_loss)

                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    self.save()

                if (epoch + 1) % 10 == 0:
                    logger.info(
                        f"Epoch {epoch + 1}/{epochs}: "
                        f"train_loss={avg_loss:.6f}, val_loss={val_loss:.6f}"
                    )
            else:
                if (epoch + 1) % 10 == 0:
                    logger.info(f"Epoch {epoch + 1}/{epochs}: train_loss={avg_loss:.6f}")

        return history

    def predict(self, sequences: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """
        Predict returns with confidence.
        Returns: (mean_predictions, variance_predictions)
        """
        self.model.eval()
        X = torch.FloatTensor(sequences).to(self.device)

        with torch.no_grad():
            mean, var = self.model(X)

        return mean.cpu().numpy().flatten(), var.cpu().numpy().flatten()

    def _validate(self, val_sequences: np.ndarray, val_targets: np.ndarray) -> float:
        self.model.eval()
        X = torch.FloatTensor(val_sequences).to(self.device)
        y = torch.FloatTensor(val_targets).unsqueeze(1).to(self.device)

        with torch.no_grad():
            mean, var = self.model(X)
            loss = 0.5 * (torch.log(var) + (y - mean) ** 2 / var).mean()

        return loss.item()

    def save(self, path: str = None):
        path = path or str(MODEL_DIR / "lstm_return_predictor.pt")
        torch.save(self.model.state_dict(), path)

    def load(self, path: str = None):
        path = path or str(MODEL_DIR / "lstm_return_predictor.pt")
        self.model.load_state_dict(torch.load(path, map_location=self.device))
