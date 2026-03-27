# FinVoice 🎯

> **AI-Powered Portfolio Management for Every Indian Investor**

FinVoice is a three-tier AI-powered financial advisor that combines Modern Portfolio Theory, ML predictions, Reinforcement Learning, voice interaction, and Explainable AI to deliver institutional-grade portfolio management for India's 140M+ retail investors.

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- Node.js 18+ (for frontend)

### 1. Clone & Setup
```bash
cd d:\DevsHouse\FinVoice
cp .env.example .env
# Edit .env with your API keys
```

### 2. Start with Docker Compose
```bash
docker-compose up -d
```

This starts:
- **PostgreSQL + TimescaleDB** (port 5432)
- **Redis** (port 6379)
- **Backend API** (port 8000)
- **ML Service** (port 8001)
- **Celery Worker + Beat** (background)
- **Frontend** (port 3000)

### 3. Local Development (without Docker)
```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

### 4. Run Data Pipeline
```bash
cd backend
python -m data.ingestion
```

## 📁 Project Structure

```
FinVoice/
├── backend/           # FastAPI backend
│   ├── api/           # REST API routes (auth, portfolio, investment, etc.)
│   ├── models/        # SQLAlchemy ORM models (12 tables)
│   ├── schemas/       # Pydantic request/response schemas
│   ├── services/      # Business logic (8 core services)
│   ├── ml/            # ML models (XGBoost, LSTM, Ensemble, GMM, RL)
│   ├── data/          # Data pipeline (ingestion, features)
│   └── tasks/         # Celery async tasks (drift detection, retraining)
├── ml_service/        # Separate ML inference microservice
├── frontend/          # Next.js 14 + TypeScript + Tailwind
├── airflow/           # Airflow DAGs (data pipeline orchestration)
└── data/              # Raw data & trained models
```

## 🔌 API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/auth/register` | POST | Register user |
| `/auth/me` | GET | Get current user |
| `/onboarding/questionnaire` | POST | Submit adaptive risk questionnaire |
| `/onboarding/risk-profile` | GET | Get risk profile |
| `/portfolio/import` | POST | Mandatory portfolio import (JSON) |
| `/portfolio/import-csv` | POST | Import portfolio from CSV |
| `/portfolio/analyze` | POST | Holdings analysis |
| `/portfolio/drift` | GET | Drift alerts |
| `/investment/allocate` | POST | New money advisor (3 scenarios) |
| `/investment/optimize` | POST | Portfolio optimizer (MPT/RL) |
| `/stress-test/monte-carlo` | POST | Monte Carlo simulation |
| `/stress-test/historical` | POST | Historical crash replay |
| `/recommendations/latest` | GET | ML-ranked recommendations |
| `/recommendations/{id}/explain` | GET | XAI explanation |

## 🧠 ML Models

- **XGBoost**: Tabular return prediction (IC > 0.05 target)
- **LSTM**: Sequential return prediction with confidence intervals
- **Ensemble**: Stacking Regressor with rolling IC-based weights
- **GMM Regime Detector**: Bull/Bear/Sideways/High-Vol classification
- **PPO/SAC (RL)**: Dynamic portfolio optimization via FinRL

## 💰 Tier System

| Feature | Free | Paid (₹299/mo) |
|---|---|---|
| Risk Assessment | ✅ Full | ✅ + Behavioral re-scoring |
| Portfolio Analysis | Basic | Full stock-level + ₹ rebalancing |
| Optimizer | MPT | RL Agent (PPO/SAC) |
| Crash Simulation | ❌ | ✅ Monte Carlo + Historical |
| Drift Detection | Weekly | Daily + Push notifications |

## ⚖️ Compliance

Every recommendation includes SEBI disclaimer:
> *"FinVoice is a decision-support tool. Invest at your own risk. Consult a SEBI-registered advisor for personalized advice."*

---

**Built with ML, Powered by Data, Designed for Bharat** 🇮🇳
