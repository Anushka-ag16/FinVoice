# FinVoice — AI-Powered Auto-Trading Platform
### *"Your money. Your rules. AI does the rest."*

---

## 🎯 Slide 1: The Problem

> **90% of retail Indian investors lose money** because they trade on emotions, miss exits, and can't analyze data like institutions.

| Pain Point | Impact |
|---|---|
| 😰 **Emotional Trading** | Buy high on FOMO, sell low in panic — the #1 wealth destroyer |
| 📉 **No Exit Strategy** | Investors hold losing stocks hoping they'll recover — losses snowball |
| 🧠 **Information Overload** | 500+ stocks, 1000s of news articles daily — impossible to process manually |
| 💸 **No Capital Protection** | Small investors risk everything on one trade and get wiped out |
| 🔒 **Institutional Advantage** | Hedge funds use AI & algorithms — retail investors are left behind |

> **₹12 lakh crore** was lost by retail investors in India in 2024 alone.
> — *SEBI Circular, 2024*

---

## 💡 Slide 2: The Solution — FinVoice

> **FinVoice is an AI-powered auto-trading platform** that gives every retail investor
> the same tools that hedge funds use — automated strategies, risk protection, and
> explainable AI — all without needing any financial knowledge.

### What makes us different:

| Feature | What it means for the user |
|---|---|
| 🤖 **AI Auto-Trading** | 5 custom algorithms analyze your portfolio and trade automatically |
| 🛡️ **Capital Protection** | "Invest ₹1L, risk only ₹20K" — your safe money is NEVER touched |
| 🎯 **Stop Loss & Take Profit** | Automatic exits — never miss a sell again |
| 🧠 **Explainable AI** | Every decision explained in simple English — "why am I buying this?" |
| 📰 **Real-time Sentiment** | AI reads financial news and acts before the crowd |
| 🗣️ **Voice-First Interface** | Manage your portfolio by just talking (Vapi.ai integration) |

---

## 🏗️ Slide 3: How It Works (User Journey)

```
┌─────────────────────────────────────────────────────────────────────┐
│  1. ONBOARD             2. PLAN                3. AUTO-TRADE        │
│  ───────────           ──────────             ───────────────       │
│  Risk profiling        "Invest ₹1L,           AI runs 5 algo       │
│  Behavioral analysis    risk only ₹20K"       strategies per stock  │
│  Voice or text          Set stop-loss          Trades execute        │
│                         & take-profit          automatically         │
│                                                                     │
│  4. PROTECT             5. EXPLAIN             6. GROW              │
│  ───────────           ──────────             ──────────            │
│  Capital protection    "Why did AI buy        Profits compound      │
│  Trailing stops         HDFC Bank?"           into trading pool     │
│  Circuit breakers      XAI dashboard          Protected capital     │
│                        with SHAP bars          stays untouched      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🧠 Slide 4: The AI Engine (Technical Deep Dive)

### Multi-Model ML Ensemble

```
Market Data (OHLCV)           Financial News
       │                            │
       ▼                            ▼
┌──────────────┐          ┌────────────────┐
│  Feature     │          │   FinBERT      │
│  Engineering │          │   Sentiment    │
│  (18 features│          │   Analysis     │
│  RSI, MACD,  │          │  (HuggingFace) │
│  Bollinger,  │          │                │
│  ATR, OBV)   │          └───────┬────────┘
└──────┬───────┘                  │
       │                          │
       ▼                          ▼
┌──────────────┬──────────────┬──────────────┐
│    LSTM      │   XGBoost    │  AutoGluon   │
│  (Sequence)  │  (Tabular)   │  (AutoML)    │
│              │              │  6 models:   │
│              │              │  XGB+LGBM+   │
│              │              │  CatBoost+NN │
└──────┬───────┴──────┬───────┴──────┬───────┘
       │              │              │
       ▼              ▼              ▼
┌────────────────────────────────────────────┐
│         Meta-Learner Ensemble              │
│   IC-weighted stacking + sentiment adj.    │
│   Confidence = model agreement score       │
└────────────────────┬───────────────────────┘
                     │
                     ▼
            5-Day Return Prediction
              + Confidence Score
```

### Key ML Components

| Component | Technology | Purpose |
|---|---|---|
| **LSTM** | PyTorch | Captures sequential price patterns |
| **XGBoost** | XGBoost | Tabular feature relationships |
| **AutoGluon** | AutoML | Auto-trains 6+ models, picks the best ensemble |
| **FinBERT** | HuggingFace Transformers | Sentiment scoring of financial news |
| **Regime Detector** | Hidden Markov Model | Identifies Bull / Bear / Sideways markets |
| **Meta-Learner** | Custom stacking | Combines all models with adaptive IC-based weights |

---

## 📊 Slide 5: 5 Custom Trading Algorithms

| # | Algorithm | Strategy | Weight |
|---|---|---|---|
| 1 | **Momentum** | Ride the winners, cut the losers | 20% |
| 2 | **Mean Reversion** | Buy the dip, sell the peak | 15% |
| 3 | **Sentiment Alpha** | Trade on news before the crowd | 20% |
| 4 | **ML Ensemble** | Let 6 AI models vote together | 30% |
| 5 | **Smart Rebalancer** | Auto-fix portfolio drift | 15% |

### How the Algorithm Orchestrator Works

```
Each strategy produces:  BUY (+1) / SELL (-1) / HOLD (0) + confidence

Strategy votes are weighted:
  Momentum:      BUY  × 0.78 strength × 0.20 weight = +0.156
  Mean Reversion: HOLD × 0.50 strength × 0.15 weight =  0.000
  Sentiment:     BUY  × 0.85 strength × 0.20 weight = +0.170
  ML Ensemble:   BUY  × 0.82 strength × 0.30 weight = +0.246
  Rebalancer:    HOLD × 0.50 strength × 0.15 weight =  0.000
                                                        ──────
  Final Score:                                          +0.572 → BUY ✅
```

---

## 🛡️ Slide 6: Capital Protection Engine (USP)

> **"Invest ₹1,00,000. Risk only ₹20,000."**

```
┌─────────────────────────────────────────────────────┐
│              Total Investment: ₹1,00,000             │
│                                                      │
│  ┌──────────────────┐   ┌─────────────────────────┐ │
│  │  PROTECTED        │   │  RISK POOL              │ │
│  │  ₹80,000          │   │  ₹20,000                │ │
│  │                   │   │                          │ │
│  │  ✅ Never touched  │   │  🤖 AI trades with this │ │
│  │  ✅ Earns FD rate  │   │  📈 Profits compound    │ │
│  │  ✅ Fully safe     │   │  🛑 Floor: ₹5,000      │ │
│  │                   │   │                          │ │
│  │  Gains locked in: │   │  If profit ₹3,000:      │ │
│  │  30% of profits → │←──│  70% → back to pool     │ │
│  │  come here        │   │  30% → locked safe      │ │
│  └──────────────────┘   └─────────────────────────┘ │
│                                                      │
│  ⚡ If risk pool hits ₹5,000 → ALL TRADING STOPS    │
│  💰 Protected capital ALWAYS stays safe              │
└─────────────────────────────────────────────────────┘
```

### What this means for investors:

- **Worst case**: Risk pool drops to ₹5,000. Total = ₹85,000. You lose max ₹15,000.
- **Best case**: Risk pool grows to ₹60,000 via compounding. Total = ₹1,40,000+.
- **Your ₹80,000 is NEVER at risk** — that's the guarantee.

---

## 🎯 Slide 7: Stop Loss & Take Profit System

### 4 Order Types

| Type | What It Does | Real Example |
|---|---|---|
| **Stop Loss** | Auto-sell when price drops | Bought RELIANCE ₹2,580 → SL at ₹2,451 (−5%) |
| **Take Profit** | Auto-sell when target reached | Same stock → TP at ₹2,838 (+10%) |
| **Trailing Stop** | Follows price up, sells on reversal | Trail 3% → rode ₹2,580→₹2,800, sold at ₹2,716 |
| **OCO** | SL + TP together | Whichever triggers first, other cancels |

### Trailing Stop Visualization

```
Price
₹2,800 ─────────●─── Peak
                ╱ ╲
₹2,716 ──────╱───╲──── 🔔 Trailing stop triggers (+₹1,360 profit!)
            ╱       ╲
₹2,580 ──●─────────── Entry price (bought here)
          ╱
₹2,451 ──────────── Fixed stop-loss (if price crashed)
```

> **Result**: Trailing stop captured ₹1,360 profit vs. ₹0 with fixed TP (target ₹2,838 never reached).

---

## 🧠 Slide 8: Explainable AI Dashboard

> Every single trade decision is explained in **plain English** — no jargon.

### Three-Panel Layout

| Panel | Content |
|---|---|
| **Left: AI Agent** | Streams its thinking: "Reading news... Good news for HDFC Bank... AI predicts +2.3%..." |
| **Center: Trade Decisions** | Cards for each BUY/SELL/HOLD with confidence scores |
| **Right: Why This Trade?** | SHAP factor bars, sentiment gauge, safety checklist |

### Example Explanation (not technical jargon):

> *"HDFC Bank is getting very positive news — their bad loans are at an all-time low,*
> *which means the bank is healthier than ever. The stock isn't overpriced right now,*
> *and the banking sector as a whole is doing well. Our AI expects the price to*
> *go up about 2.3% this week."*

### Factor Attribution (plain English):

| Factor | Impact |
|---|---|
| 📰 News is very positive | 👍 28% influence |
| 🏦 Banking sector is strong | 👍 15% influence |
| 📈 Growing steadily for weeks | 👍 11% influence |
| 💰 Investors purchasing more | 👍 9% influence |
| ✅ Not overpriced | 👍 8% influence |
| ⚖️ Slight price swings | 👎 3% influence |

---

## 🏛️ Slide 9: Technical Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    FRONTEND                               │
│   Next.js (Dashboard) + Trading Agent UI (DOM Engine)     │
│   Voice Interface (Vapi.ai)                               │
└─────────────────────┬────────────────────────────────────┘
                      │ REST API
┌─────────────────────▼────────────────────────────────────┐
│                 BACKEND (FastAPI)                          │
│                                                           │
│  ┌─────────┐ ┌────────────┐ ┌────────────┐ ┌──────────┐ │
│  │  Auth   │ │  Portfolio  │ │  Trading   │ │  Stop    │ │
│  │  RBAC   │ │  Optimizer  │ │  Engine    │ │  Loss    │ │
│  │Supabase │ │  MPT + RL   │ │  Paper/Live│ │  Engine  │ │
│  └─────────┘ └────────────┘ └────────────┘ └──────────┘ │
│                                                           │
│  ┌─────────┐ ┌────────────┐ ┌────────────┐ ┌──────────┐ │
│  │  5 Algo │ │  Capital   │ │  Risk      │ │ Crash    │ │
│  │ Strats  │ │ Protection │ │ Controls   │ │ Simulator│ │
│  │Orchestr.│ │  Engine    │ │ 6 checks   │ │ Stress   │ │
│  └─────────┘ └────────────┘ └────────────┘ └──────────┘ │
│                                                           │
│  ┌───────────────────────────────────────────────────┐   │
│  │              ML Pipeline                           │   │
│  │  LSTM + XGBoost + AutoGluon + FinBERT + HMM       │   │
│  │  Feature Engineering (18 indicators)               │   │
│  │  Ensemble Meta-Learner with IC weights             │   │
│  └───────────────────────────────────────────────────┘   │
└──────────────────┬───────────────┬───────────────────────┘
                   │               │
        ┌──────────▼──┐    ┌───────▼────────┐
        │ PostgreSQL  │    │  Angel One     │
        │ (Supabase)  │    │  SmartAPI      │
        │             │    │  (Live Broker) │
        └─────────────┘    └────────────────┘
```

### Full Tech Stack

| Layer | Technologies |
|---|---|
| **Frontend** | Next.js, TypeScript, Tailwind CSS, Vapi.ai (Voice) |
| **Backend** | FastAPI, Python 3.11, SQLAlchemy (async), Pydantic |
| **ML/AI** | PyTorch (LSTM), XGBoost, AutoGluon, HuggingFace Transformers (FinBERT) |
| **Database** | PostgreSQL via Supabase |
| **Broker** | Angel One SmartAPI (live trading) |
| **Auth** | Supabase Auth + JWT + RBAC (Free/Paid tiers) |
| **Payments** | Razorpay |

---

## 📡 Slide 10: API Surface (40+ Endpoints)

| Module | Endpoints | Key Features |
|---|---|---|
| 🔐 Auth | 6 | Register, login, JWT, RBAC, tier management |
| 📋 Onboarding | 3 | Risk profiling, behavioral analysis |
| 💼 Portfolio | 8 | CRUD, holdings, drift detection, optimization |
| 📈 Trading | 9 | Paper/live execution, order management, broker sync |
| 🤖 Algorithms | 3 | Run 5 strategies, backtest, list strategies |
| 🛡️ Smart Invest | 8 | Capital protection plans, simulate, add capital |
| 🎯 Stop Orders | 8 | SL, TP, trailing stop, OCO, simulate, history |
| 💡 Recommendations | 3 | AI-driven invest suggestions with explanations |
| 🧪 Stress Test | 2 | Crash simulation (2008, COVID, custom) |
| 💰 Investment | 3 | New money allocation advisor |

---

## 🛡️ Slide 11: Security & Safety

### 6 Risk Control Checks on Every Trade

| # | Check | Purpose |
|---|---|---|
| 1 | ⏰ Market Hours | Only trade during NSE 9:15 AM – 3:30 PM |
| 2 | 📏 Max Order Size | No single trade > 25% of portfolio |
| 3 | 📊 Daily Loss Limit | Halt all trades if daily loss > 3% |
| 4 | 🔢 Max Trades/Day | Cap at 20 trades per day |
| 5 | 🧩 Concentration | No single stock > 30% of portfolio |
| 6 | ⏳ Cooldown | Prevent panic re-trading same stock |

### Security Stack

- **Supabase Auth** with JWT tokens
- **RBAC**: Free tier (paper), Paid tier (live trading)
- **Master Kill Switch** — one config flag halts ALL trading
- **Capital Protection Floor** — auto-halt when risk pool depleted
- **Rate limiting** + CORS + input validation (Pydantic)

---

## 💰 Slide 12: Business Model

### SaaS — Freemium + Premium

| Tier | Price | Features |
|---|---|---|
| **Free** | ₹0 | Paper trading, basic algorithms, portfolio tracking, XAI explanations |
| **Pro** | ₹499/month | Live trading, all 5 algorithms, capital protection, trailing stops, voice |
| **Elite** | ₹1,999/month | RL optimization, priority signals, advanced backtesting, API access |

### Revenue Streams

| Stream | Description |
|---|---|
| 🔄 **Subscriptions** | Monthly SaaS fees (primary) |
| 📊 **Broker Commissions** | Revenue share with Angel One on live trades |
| 📡 **API Access** | Developers/fintechs pay for algorithm API |
| 📚 **Premium Signals** | Curated buy/sell signals for passive investors |

### Market Opportunity

| Metric | Value |
|---|---|
| 🇮🇳 Indian retail investors | **12+ crore** demat accounts (CDSL, 2024) |
| 📈 Growth rate | 40% YoY new demat accounts |
| 💰 Addressable market | ₹50,000+ crore/year in trading fees |
| 🎯 Target niche | First-time investors (18–35, tier 2/3 cities) |

---

## 🏆 Slide 13: What We've Built (Demo-Ready)

### ✅ Fully Functional

| Component | Status | Files |
|---|---|---|
| FastAPI Backend | ✅ Live | 45+ Python files |
| ML Pipeline (LSTM + XGBoost + AutoGluon) | ✅ Working | 7 ML modules |
| FinBERT Sentiment Analysis | ✅ Working | Integrated with ensemble |
| 5 Trading Algorithms + Orchestrator | ✅ Working | Tested via API |
| Capital Protection Engine | ✅ Working | Simulation endpoint live |
| Stop Loss / Take Profit / Trailing / OCO | ✅ Working | Simulation tested |
| AI Trading Agent Dashboard (XAI) | ✅ Working | Interactive DOM-based UI |
| Risk Controls (6 checks) | ✅ Working | Integrated in trading engine |
| Paper Trading Simulator | ✅ Working | Virtual ₹10L account |
| Angel One Live Broker Integration | ✅ Ready | SmartAPI connected |
| Next.js Frontend | ✅ Working | Dashboard, portfolio, onboarding |

### Code Stats

| Metric | Value |
|---|---|
| **Total files** | 80+ |
| **Backend Python LOC** | ~8,000 |
| **API endpoints** | 40+ |
| **ML models** | 6 (LSTM, XGBoost, LightGBM, CatBoost, NN, FinBERT) |
| **Trading strategies** | 5 custom algorithms |
| **Safety checks** | 12 (6 risk controls + 4 stop types + capital floor + kill switch) |

---

## 🚀 Slide 14: Competitive Advantage

| Feature | Zerodha | Groww | Smallcase | **FinVoice** |
|---|---|---|---|---|
| Auto-trading algorithms | ❌ | ❌ | ❌ | ✅ 5 strategies |
| Capital protection | ❌ | ❌ | ❌ | ✅ "Risk only X" |
| Explainable AI | ❌ | ❌ | ❌ | ✅ Plain English |
| Stop-loss automation | Basic | Basic | ❌ | ✅ 4 types + OCO |
| News sentiment trading | ❌ | ❌ | ❌ | ✅ FinBERT |
| ML predictions | ❌ | ❌ | ❌ | ✅ 6-model ensemble |
| Voice interface | ❌ | ❌ | ❌ | ✅ Vapi.ai |
| Paper trading | ❌ | ❌ | ❌ | ✅ Virtual ₹10L |

> **FinVoice is the ONLY platform** that combines auto-trading, capital protection,
> and explainable AI for Indian retail investors.

---

## 🗺️ Slide 15: Roadmap

| Quarter | Milestone |
|---|---|
| **Q2 2026** | Beta launch (paper trading), onboard 1,000 users |
| **Q3 2026** | Live trading with Angel One, Pro tier launch |
| **Q4 2026** | Mobile app (React Native), voice-first experience |
| **Q1 2027** | Multi-broker support (Zerodha, Upstox), SEBI compliance |
| **Q2 2027** | Options & F&O strategies, Elite tier launch |

---

## 🙋 Slide 16: The Team

> *Built in 36 hours at DevsHouse Hackathon*

- **Backend**: FastAPI + PostgreSQL + Supabase
- **ML/AI**: PyTorch + AutoGluon + HuggingFace
- **Frontend**: Next.js + Trading Agent Dashboard
- **70+ files**, production-grade architecture

---

## ❓ Slide 17: Q&A

### Anticipated Questions:

**Q: Is this SEBI-compliant?**
> A: FinVoice is a decision-support tool. We clearly disclaim that we don't provide financial advice. For live trading, users connect their own Angel One accounts. We're exploring SEBI RIA registration.

**Q: What if the AI is wrong?**
> A: That's exactly why we have 12 safety layers — capital protection floor, stop-losses, daily loss limits, max trade caps. Even if the AI is wrong, your downside is capped.

**Q: How is this different from algo-trading platforms?**
> A: Existing platforms require coding (Streak, AlgoTrader). FinVoice is zero-code — it explains every decision in plain English and protects your capital automatically.

**Q: Revenue potential?**
> A: With 12 crore demat accounts in India, even 0.01% adoption = 12,000 paying users = ₹72L MRR at ₹499/month. Target: ₹5 crore ARR in Year 1.

---

> ### *"FinVoice: Because your money deserves AI that explains itself."* 🚀
