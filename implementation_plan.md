# FinVoice — Technical Implementation Plan

> AI-Powered Portfolio Management for Every Indian Investor

## Goal

Build FinVoice from scratch as a full-stack application with:
- **Backend**: FastAPI (Python) — portfolio engine, ML inference, data pipeline
- **Frontend**: Next.js 14 + TypeScript + Tailwind CSS (PWA)
- **ML/RL**: XGBoost → LSTM → PPO/SAC ensemble for portfolio optimization
- **Voice**: Vapi.ai + Twilio for conversational AI
- **Data**: PostgreSQL + TimescaleDB, Redis, Airflow

Mandatory portfolio import is central to the onboarding flow. Reinforcement Learning (PPO/SAC via FinRL) enhances the portfolio optimizer for paid-tier users.

---

## Project Structure

```
d:\DevsHouse\FinVoice\
├── docker-compose.yml              # All services
├── .env.example                     # Environment template
├── README.md
│
├── backend/                         # FastAPI backend
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                      # App entry point + CORS + lifespan
│   ├── config.py                    # Settings (Pydantic BaseSettings)
│   ├── database.py                  # SQLAlchemy + TimescaleDB setup
│   │
│   ├── models/                      # SQLAlchemy ORM models
│   │   ├── user.py                  # User, RiskProfile, BehavioralBias
│   │   ├── portfolio.py             # Portfolio, Holding, Transaction
│   │   ├── asset.py                 # Asset, Price, Feature
│   │   └── recommendation.py       # Recommendation, Explanation
│   │
│   ├── schemas/                     # Pydantic request/response schemas
│   │   ├── user.py
│   │   ├── portfolio.py
│   │   ├── risk.py
│   │   └── recommendation.py
│   │
│   ├── api/                         # API route modules
│   │   ├── auth.py                  # /auth/* (Supabase JWT validation)
│   │   ├── onboarding.py            # /onboarding/* (questionnaire + risk score)
│   │   ├── portfolio.py             # /portfolio/* (import, analyze, drift)
│   │   ├── investment.py            # /investment/* (new money advisor)
│   │   ├── stress_test.py           # /stress-test/* (Monte Carlo, scenarios)
│   │   ├── recommendations.py      # /recommendations/* (ML-powered)
│   │   └── voice.py                 # /voice/* (Vapi webhook handlers)
│   │
│   ├── services/                    # Business logic
│   │   ├── risk_profiler.py         # Adaptive questionnaire scoring
│   │   ├── holdings_analyzer.py     # Exposure, concentration, correlation
│   │   ├── portfolio_optimizer.py   # MPT, Black-Litterman, CVaR, Risk Parity
│   │   ├── rl_optimizer.py          # FinRL PPO/SAC agent (paid tier)
│   │   ├── new_money_advisor.py     # 3-scenario allocation generator
│   │   ├── drift_detector.py        # Daily drift check + alerts
│   │   ├── crash_simulator.py       # Monte Carlo + historical replay
│   │   ├── explainer.py             # SHAP/LIME → NLG pipeline
│   │   └── sentiment.py             # FinBERT news/social scoring
│   │
│   ├── ml/                          # ML model training & inference
│   │   ├── feature_engineering.py   # RSI, MACD, Bollinger, macro features
│   │   ├── xgboost_model.py         # XGBoost return predictor
│   │   ├── lstm_model.py            # LSTM time-series model
│   │   ├── ensemble.py              # Stacking Regressor meta-learner
│   │   ├── regime_detector.py       # GMM regime classification
│   │   ├── rl_agent.py              # FinRL PPO/SAC training & inference
│   │   └── model_registry.py        # MLflow model versioning
│   │
│   ├── data/                        # Data pipeline
│   │   ├── ingestion.py             # NSE, BSE, MFAPI, RBI data fetchers
│   │   ├── validators.py            # Data quality checks
│   │   └── feature_store.py         # Feature computation & storage
│   │
│   ├── tasks/                       # Celery async tasks
│   │   ├── daily_drift.py           # Nightly portfolio drift check
│   │   ├── retrain_models.py        # Weekly model retraining
│   │   └── data_pipeline.py         # Daily data ingestion trigger
│   │
│   └── tests/                       # pytest test suite
│       ├── test_risk_profiler.py
│       ├── test_holdings_analyzer.py
│       ├── test_portfolio_optimizer.py
│       ├── test_rl_optimizer.py
│       ├── test_new_money_advisor.py
│       ├── test_crash_simulator.py
│       └── test_api_endpoints.py
│
├── ml_service/                      # Separate ML inference microservice
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                      # FastAPI inference endpoints
│   ├── models/                      # Saved model artifacts (.onnx, .pt)
│   └── serve.py                     # Model loading + prediction
│
├── frontend/                        # Next.js 14 frontend
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.ts
│   ├── public/
│   │   └── manifest.json            # PWA manifest
│   │
│   └── src/
│       ├── app/
│       │   ├── layout.tsx            # Root layout + fonts + metadata
│       │   ├── page.tsx              # Landing page
│       │   ├── dashboard/
│       │   │   └── page.tsx          # Main dashboard
│       │   ├── onboarding/
│       │   │   └── page.tsx          # 4-stage adaptive questionnaire
│       │   ├── portfolio/
│       │   │   ├── import/page.tsx   # Mandatory portfolio import
│       │   │   ├── analysis/page.tsx # Holdings analyzer results
│       │   │   └── drift/page.tsx    # Drift alerts
│       │   ├── invest/
│       │   │   └── page.tsx          # New money advisor
│       │   ├── stress-test/
│       │   │   └── page.tsx          # Crash simulation
│       │   └── chat/
│       │       └── page.tsx          # Voice/chat interface
│       │
│       ├── components/
│       │   ├── ui/                   # Reusable UI primitives
│       │   ├── charts/              # Recharts/D3 chart components
│       │   ├── portfolio/           # Portfolio-specific components
│       │   └── onboarding/          # Questionnaire step components
│       │
│       ├── lib/
│       │   ├── api.ts               # API client (axios/fetch wrapper)
│       │   ├── supabase.ts          # Supabase client config
│       │   └── utils.ts             # Formatters, helpers
│       │
│       └── types/
│           └── index.ts             # TypeScript interfaces
│
├── airflow/                         # Airflow DAGs
│   └── dags/
│       ├── daily_ingestion.py       # Nightly data pull DAG
│       ├── feature_engineering.py   # Feature computation DAG
│       └── model_retraining.py      # Weekly retrain DAG
│
└── data/                            # Local data storage
    ├── raw/                         # Raw parquet files
    └── models/                      # Trained model artifacts
```

---

## Proposed Changes

### Component 1: Project Scaffolding & Infrastructure

#### [NEW] [docker-compose.yml](file:///d:/DevsHouse/FinVoice/docker-compose.yml)
Docker Compose with services: `postgres` (TimescaleDB image), `redis`, `backend` (FastAPI), `ml_service`, `frontend` (Next.js), `airflow-webserver`, `airflow-scheduler`, `celery-worker`.

#### [NEW] [.env.example](file:///d:/DevsHouse/FinVoice/.env.example)
Template for: `DATABASE_URL`, `REDIS_URL`, `SUPABASE_URL`, `SUPABASE_KEY`, `ANGEL_ONE_API_KEY`, `VAPI_API_KEY`, `MLFLOW_TRACKING_URI`, `RAZORPAY_KEY`.

---

### Component 2: Database Schema

#### [NEW] [backend/models/user.py](file:///d:/DevsHouse/FinVoice/backend/models/user.py)
```python
# Key tables:
# - User: id, email, supabase_uid, tier (free/paid), created_at
# - RiskProfile: user_id, risk_score (0-100), investor_type, 
#   behavioral_bias, last_computed, questionnaire_responses (JSON)
# - BehavioralSignal: user_id, signal_type, timestamp
```

#### [NEW] [backend/models/portfolio.py](file:///d:/DevsHouse/FinVoice/backend/models/portfolio.py)
```python
# - Portfolio: id, user_id, name, created_at
# - Holding: portfolio_id, asset_id, quantity, buy_price, buy_date
# - TargetAllocation: portfolio_id, asset_class, target_pct
# - Transaction: portfolio_id, asset_id, type, quantity, price, date
```

#### [NEW] [backend/models/asset.py](file:///d:/DevsHouse/FinVoice/backend/models/asset.py)
```python
# - Asset: id, symbol, name, asset_class, sector, market_cap_tier
# - Price: asset_id, date, open, high, low, close, volume (TimescaleDB hypertable)
# - Feature: asset_id, date, rsi, macd, bollinger_pos, beta, ... (50+ cols)
```

---

### Component 3: Data Pipeline

#### [NEW] [backend/data/ingestion.py](file:///d:/DevsHouse/FinVoice/backend/data/ingestion.py)
Unified ingestion service pulling from:
- `yfinance` — NIFTY50 + top 100 stocks (`.NS` suffix)
- `mfapi` — mutual fund NAVs for top 500 funds
- RBI DBIE — repo rate, CPI, G-Sec yields (CSV download)
- BSE India API — corporate actions

Stores raw data as parquet in `data/raw/` and inserts into TimescaleDB `prices` hypertable.

#### [NEW] [backend/ml/feature_engineering.py](file:///d:/DevsHouse/FinVoice/backend/ml/feature_engineering.py)
Computes 50+ features per asset per day:

| Category | Features |
|---|---|
| **Technical** | RSI(14), MACD(12,26,9), Bollinger Band position, ATR, OBV, Williams %R, Stochastic, ADX |
| **Fundamental** | PE, PB, Debt/Equity, ROE, Promoter holding %, FII holding %, Dividend yield |
| **Macro** | Repo rate, CPI, USD/INR, 10Y G-Sec, India VIX, FII/DII net flows |
| **Market** | Delivery volume %, 52-week high/low distance, sector momentum rank |
| **Sentiment** | FinBERT score, Reddit mentions, Google Trends index |

#### [NEW] [airflow/dags/daily_ingestion.py](file:///d:/DevsHouse/FinVoice/airflow/dags/daily_ingestion.py)
Airflow DAG scheduled at `45 15 * * 1-5` (3:45 PM IST, weekdays). Tasks: `fetch_prices → validate_data → store_raw → compute_features → update_feature_store`.

---

### Component 4: ML Models

#### [NEW] [backend/ml/xgboost_model.py](file:///d:/DevsHouse/FinVoice/backend/ml/xgboost_model.py)
- Train on tabular features (technical + fundamental + macro)
- Predict forward returns (1-day, 5-day, 21-day)
- Target: IC > 0.05, ICIR > 0.5
- Walk-forward validation: train 2003–2020, validate 2021, test 2022–2024
- SHAP values computed at inference for explainability

#### [NEW] [backend/ml/lstm_model.py](file:///d:/DevsHouse/FinVoice/backend/ml/lstm_model.py)
- PyTorch LSTM with 2 layers, hidden size 128
- Input: 30-day OHLCV + macro window per asset
- Asset class embeddings (not one model per stock)
- Output: return probability distribution (mean + variance)

#### [NEW] [backend/ml/ensemble.py](file:///d:/DevsHouse/FinVoice/backend/ml/ensemble.py)
- Stacking Regressor combining LSTM + XGBoost predictions
- Model weights updated by rolling 30-day Sharpe contribution
- Output: Expected Return vector + Covariance Matrix → optimizer

#### [NEW] [backend/ml/regime_detector.py](file:///d:/DevsHouse/FinVoice/backend/ml/regime_detector.py)
- Gaussian Mixture Model (scikit-learn) on VIX + breadth + momentum
- 4 regimes: Bull / Bear / Sideways / High-Volatility
- Allocation shifts condition on detected regime

---

### Component 5: Reinforcement Learning

#### [NEW] [backend/ml/rl_agent.py](file:///d:/DevsHouse/FinVoice/backend/ml/rl_agent.py)
FinRL-based RL agent for dynamic portfolio optimization (paid tier):

```python
# Environment:
#   State: [holdings_weights, OHLCV_features, macro_features, risk_score]
#   Action: target allocation weights (continuous, sum to 1)
#   Reward: sharpe_ratio - lambda1 * transaction_cost - lambda2 * drift_penalty

# Training:
#   Algorithm: PPO (primary) via Stable-Baselines3
#   Alternative: SAC for exploration-heavy evaluation
#   Data: 2003-2020 train, 2021 val, 2022-2024 test (walk-forward)
#   Episodes: simulate full trading periods

# Inference:
#   Load trained model → observe current state → output new weights
#   Compare with MPT output → use RL if confidence > threshold
```

#### [NEW] [backend/services/rl_optimizer.py](file:///d:/DevsHouse/FinVoice/backend/services/rl_optimizer.py)
Service that wraps the RL agent for API use:
- Loads pre-trained PPO/SAC model
- Takes user portfolio + market state as input
- Returns optimized allocation weights
- Falls back to MPT if RL model unavailable or low confidence

---

### Component 6: Portfolio Engine Services

#### [NEW] [backend/services/portfolio_optimizer.py](file:///d:/DevsHouse/FinVoice/backend/services/portfolio_optimizer.py)
- **Free tier**: MPT (efficient frontier, max Sharpe) + Black-Litterman with ML views + CVaR
- **Paid tier**: RL agent (PPO/SAC) for dynamic optimization
- Uses PyPortfolioOpt for traditional methods
- Ledoit-Wolf covariance shrinkage

#### [NEW] [backend/services/holdings_analyzer.py](file:///d:/DevsHouse/FinVoice/backend/services/holdings_analyzer.py)
- Classify holdings by sector, asset class, market cap, geography
- Flag concentration risk (single stock > 20%, sector > 35%)
- Pairwise correlation analysis (1-year rolling, flag r > 0.75)
- Portfolio beta vs Nifty 50
- LP solver (scipy.optimize) for rupee-level rebalancing

#### [NEW] [backend/services/new_money_advisor.py](file:///d:/DevsHouse/FinVoice/backend/services/new_money_advisor.py)
- Input: amount, max loss, goal, horizon, tax bracket
- Generate 3 scenarios: Conservative / Balanced / Aggressive
- Exact rupee allocation per asset (e.g., ₹40K Nifty50 ETF, ₹25K SGB...)
- XAI explanation for each allocation

#### [NEW] [backend/services/crash_simulator.py](file:///d:/DevsHouse/FinVoice/backend/services/crash_simulator.py)
- Monte Carlo: 10,000 paths via Cholesky decomposition
- Historical replay: 2008, 2020, 2022 actual returns applied
- Custom shocks: user-defined scenario ("Nifty drops 30%")
- Output: max drawdown, time to recovery, probability of ruin

#### [NEW] [backend/services/drift_detector.py](file:///d:/DevsHouse/FinVoice/backend/services/drift_detector.py)
- Celery task at 11 PM IST nightly
- Compare actual vs target allocation
- Severity: INFO (1–3%), WARN (3–5%), ALERT (>5%)
- Push notification for paid / weekly digest for free

---

### Component 7: Onboarding & Risk Profiling

#### [NEW] [backend/services/risk_profiler.py](file:///d:/DevsHouse/FinVoice/backend/services/risk_profiler.py)
- 4-stage adaptive questionnaire scoring
- Stage routing based on detected knowledge level
- Risk score (0–100) + Investor Type + Behavioral Bias tag
- Dynamic re-scoring: 90-day refresh + behavioral signal adjustment
- Behavioral signals: panic sell attempts, frequent checking, etc.

#### [NEW] [backend/api/onboarding.py](file:///d:/DevsHouse/FinVoice/backend/api/onboarding.py)
Endpoints:
- `POST /onboarding/questionnaire` — submit answers, get risk profile
- `POST /onboarding/portfolio-import` — mandatory portfolio import
- `GET /onboarding/risk-profile` — fetch current risk profile
- `POST /onboarding/refresh-risk` — trigger re-evaluation

---

### Component 8: XAI Layer

#### [NEW] [backend/services/explainer.py](file:///d:/DevsHouse/FinVoice/backend/services/explainer.py)
- SHAP TreeExplainer for XGBoost — feature importance waterfall
- LIME for LSTM — perturbation-based explanation
- Factor attribution (Barra-style): market beta, sector tilt, stock alpha
- NLG: LLM converts SHAP values → plain-language explanation
- 3 tiers: Short (free), Medium (paid), Full PDF report (paid)

---

### Component 9: API Endpoints Summary

All endpoints follow RESTful conventions with SEBI disclaimer auto-appended.

| Endpoint | Method | Description | Tier |
|---|---|---|---|
| `/auth/login` | POST | Supabase OAuth/JWT | All |
| `/onboarding/questionnaire` | POST | Submit adaptive questionnaire | All |
| `/onboarding/portfolio-import` | POST | Mandatory portfolio import | All |
| `/portfolio/analyze` | POST | Holdings analysis | Free: basic / Paid: full |
| `/portfolio/drift` | GET | Current drift status | Free: weekly / Paid: daily |
| `/investment/allocate` | POST | New money advisor | Free: basic / Paid: ML-optimized |
| `/investment/optimize` | POST | Portfolio optimization | Free: MPT / Paid: RL |
| `/stress-test/monte-carlo` | POST | Crash simulation | Paid |
| `/stress-test/historical` | POST | Historical replay | Paid |
| `/recommendations/latest` | GET | ML-ranked suggestions | Paid |
| `/recommendations/explain` | GET | XAI explanation | Free: short / Paid: full |
| `/voice/webhook` | POST | Vapi.ai webhook | All |
| `/trading/paper/order` | POST | Paper trade | Paid |
| `/trading/live/order` | POST | Live trade (Angel One) | Paid |

---

### Component 10: Next.js Frontend

#### [NEW] [frontend/](file:///d:/DevsHouse/FinVoice/frontend/)
Next.js 14 (App Router) + TypeScript + Tailwind CSS with:
- **Landing page**: Hero with value prop, feature showcase, pricing tiers
- **Onboarding**: 4-step wizard with adaptive questions, mandatory portfolio import (CSV upload or manual entry)
- **Dashboard**: Portfolio overview, allocation donut chart, performance line chart, drift alerts, risk score gauge
- **Holdings Analysis**: Sector/asset pie charts, concentration flags, correlation matrix heatmap, rebalancing recommendations
- **New Money Advisor**: Amount input → 3 scenario cards with projected returns → XAI explanation
- **Stress Test**: Monte Carlo distribution chart, historical scenario comparison, drawdown visualization
- **Chat**: Split-screen with message list + portfolio context sidebar, real-time streaming via Socket.io

Design system: dark mode primary, glassmorphism cards, smooth micro-animations, Inter/Outfit fonts, premium gradient accents.

---

### Component 11: Voice AI

#### [NEW] [backend/api/voice.py](file:///d:/DevsHouse/FinVoice/backend/api/voice.py)
- Vapi.ai webhook handler for tool calling
- Intent classification: portfolio-check / new-investment / explain / crash-sim
- Session context: preload user's risk profile + holdings + alerts
- Hindi/Hinglish detection + response
- SEBI disclaimer injection

---

### Component 12: Security & Payments

#### Security measures across all components:
- AES-256 at rest, TLS 1.3 in transit
- PostgreSQL Row-Level Security per user
- `slowapi` rate limiting on all endpoints
- JWT validation middleware
- No PAN/Aadhaar stored — hashed KYC identifiers only

#### [NEW] Payment integration:
- Razorpay subscription for ₹299/month paid tier
- Feature flags in `user.tier` column
- Tier-checking middleware on protected endpoints

---

## Verification Plan

### Automated Tests

Each component will have pytest tests in `backend/tests/`. Run all tests with:
```bash
cd d:\DevsHouse\FinVoice\backend
pytest tests/ -v --tb=short
```

| Test File | What It Verifies |
|---|---|
| `test_risk_profiler.py` | Questionnaire scoring, risk score ranges (0–100), bias detection, dynamic re-scoring |
| `test_holdings_analyzer.py` | Concentration flags at thresholds, correlation detection, beta computation, rebalancing output |
| `test_portfolio_optimizer.py` | MPT returns valid weights (sum to 1), Black-Litterman with mock views, CVaR non-negative |
| `test_rl_optimizer.py` | RL agent returns valid weights, fallback to MPT when model unavailable, confidence thresholding |
| `test_new_money_advisor.py` | 3 scenarios generated, allocations sum to input amount, rupee-level precision |
| `test_crash_simulator.py` | Monte Carlo output shape (10K × T matrix), historical replay with known crashes, drawdown calc |
| `test_api_endpoints.py` | All API endpoints return correct status codes, auth middleware rejects invalid tokens, SEBI disclaimer present |

### Data Pipeline Validation
```bash
# Verify data ingestion and quality
cd d:\DevsHouse\FinVoice\backend
python -m data.ingestion --validate --symbols RELIANCE.NS,TCS.NS,HDFCBANK.NS --days 30
```
- Checks: no missing dates, OHLCV non-negative, volume > 0, no duplicate rows

### ML Model Validation
```bash
# Evaluate XGBoost on test set
cd d:\DevsHouse\FinVoice\backend
python -m ml.xgboost_model --evaluate --test-year 2023
# Target: IC > 0.05, ICIR > 0.5
```

### Frontend Verification
- Run `npm run dev` in `frontend/` and verify:
  - Onboarding flow completes with mandatory portfolio import
  - Dashboard renders with mock data
  - All pages responsive on mobile (PWA)
- Browser-based visual checks using the browser agent tool

### Integration Tests
```bash
# Start all services and run end-to-end flow
docker-compose up -d
cd d:\DevsHouse\FinVoice\backend
pytest tests/test_api_endpoints.py -v
```

### Manual Verification (User)
1. Complete the onboarding questionnaire and verify risk score makes sense
2. Import a sample portfolio and review the holdings analysis
3. Enter "I want to invest ₹1L" in the new money advisor and verify 3 scenario output
4. Check that SEBI disclaimer appears on every recommendation
