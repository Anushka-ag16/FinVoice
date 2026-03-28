#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# setup.sh — Environment setup for the NSE Quant Pipeline
#
# Creates a Python virtual environment, installs dependencies, and sets up
# MLflow + TimescaleDB.
#
# Usage:
#   bash scripts/setup.sh
# ──────────────────────────────────────────────────────────────────────────────

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV_DIR="${PROJECT_ROOT}/venv"

echo "================================================================"
echo "  NSE Quant Pipeline — Setup"
echo "================================================================"
echo ""

# ── Python venv ──────────────────────────────────────────────────────────────
echo "[1/5] Creating Python virtual environment..."
if [ ! -d "${VENV_DIR}" ]; then
    python3 -m venv "${VENV_DIR}"
    echo "  Created: ${VENV_DIR}"
else
    echo "  Already exists: ${VENV_DIR}"
fi

source "${VENV_DIR}/bin/activate" 2>/dev/null || source "${VENV_DIR}/Scripts/activate" 2>/dev/null
echo "  Activated: $(which python)"

# ── Dependencies ─────────────────────────────────────────────────────────────
echo ""
echo "[2/5] Installing Python dependencies..."
pip install --upgrade pip setuptools wheel -q
pip install -r "${PROJECT_ROOT}/requirements.txt" -q
echo "  Done — $(pip list 2>/dev/null | wc -l) packages installed"

# ── CUDA check ───────────────────────────────────────────────────────────────
echo ""
echo "[3/5] Checking GPU/CUDA availability..."
python3 -c "
import torch
if torch.cuda.is_available():
    print(f'  CUDA available: {torch.cuda.get_device_name(0)}')
    print(f'  CUDA version: {torch.version.cuda}')
    print(f'  cuDNN version: {torch.backends.cudnn.version()}')
else:
    print('  WARNING: CUDA not available — falling back to CPU')
" 2>/dev/null || echo "  WARNING: PyTorch not yet installed or import failed"

# ── Directory structure ──────────────────────────────────────────────────────
echo ""
echo "[4/5] Creating directory structure..."
mkdir -p "${PROJECT_ROOT}/data/raw"
mkdir -p "${PROJECT_ROOT}/data/processed"
mkdir -p "${PROJECT_ROOT}/models/tft"
mkdir -p "${PROJECT_ROOT}/models/lstm"
mkdir -p "${PROJECT_ROOT}/models/sac"
mkdir -p "${PROJECT_ROOT}/models/ensemble"
mkdir -p "${PROJECT_ROOT}/models/feature_importance"
mkdir -p "${PROJECT_ROOT}/mlartifacts"
echo "  Directories ready"

# ── .env file ────────────────────────────────────────────────────────────────
echo ""
echo "[5/5] Environment configuration..."
if [ ! -f "${PROJECT_ROOT}/.env" ]; then
    cp "${PROJECT_ROOT}/.env.example" "${PROJECT_ROOT}/.env"
    echo "  Created .env from .env.example — please update with your credentials"
else
    echo "  .env already exists — skipping"
fi

# ── MLflow setup ─────────────────────────────────────────────────────────────
echo ""
echo "Setting up MLflow..."
python3 -c "
import mlflow
mlflow.set_tracking_uri('sqlite:///mlflow.db')
mlflow.set_experiment('nse-quant-pipeline')
print('  MLflow experiment created: nse-quant-pipeline')
print(f'  Tracking URI: sqlite:///mlflow.db')
" 2>/dev/null || echo "  WARNING: MLflow setup failed — run manually"

echo ""
echo "================================================================"
echo "  Setup Complete!"
echo ""
echo "  Next steps:"
echo "    1. Edit .env with your API keys"
echo "    2. python scripts/collect_data.py"
echo "    3. python scripts/train_pipeline.py"
echo "    4. python scripts/validate_features.py"
echo "================================================================"
echo ""
