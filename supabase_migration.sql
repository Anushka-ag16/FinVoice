-- ============================================================================
-- FinVoice — Supabase Database Migration
-- Run this in: Supabase Dashboard → SQL Editor → New Query
-- ============================================================================
-- Order matters: referenced tables must exist before foreign keys are added.
-- Extensions → Enums → Tables → Indexes → RLS Policies → Triggers
-- ============================================================================


-- ============================================================================
-- EXTENSIONS
-- ============================================================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";      -- uuid_generate_v4()
CREATE EXTENSION IF NOT EXISTS "pg_trgm";        -- trigram full-text search on names
CREATE EXTENSION IF NOT EXISTS "btree_gin";      -- GIN indexes on scalar types


-- ============================================================================
-- HELPER: updated_at trigger function
-- ============================================================================
CREATE OR REPLACE FUNCTION trigger_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- ============================================================================
-- GROUP 1: USERS & AUTH
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. users
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.users (
  id                   BIGSERIAL PRIMARY KEY,
  supabase_uid         UUID UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
  email                TEXT UNIQUE NOT NULL,
  full_name            TEXT,
  tier                 TEXT NOT NULL DEFAULT 'free'
                         CHECK (tier IN ('free', 'paid')),
  is_active            BOOLEAN NOT NULL DEFAULT TRUE,
  onboarding_complete  BOOLEAN NOT NULL DEFAULT FALSE,
  phone_number         TEXT,                          -- for Vapi/Twilio call agent
  preferred_language   TEXT NOT NULL DEFAULT 'en'
                         CHECK (preferred_language IN ('en', 'hi', 'hinglish')),
  created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_supabase_uid ON public.users(supabase_uid);
CREATE INDEX IF NOT EXISTS idx_users_email        ON public.users(email);

CREATE TRIGGER set_users_updated_at
  BEFORE UPDATE ON public.users
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- RLS
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

CREATE POLICY "users: own row read"
  ON public.users FOR SELECT
  USING (supabase_uid = auth.uid());

CREATE POLICY "users: own row update"
  ON public.users FOR UPDATE
  USING (supabase_uid = auth.uid());

CREATE POLICY "users: insert own row"
  ON public.users FOR INSERT
  WITH CHECK (supabase_uid = auth.uid());


-- ----------------------------------------------------------------------------
-- 2. risk_profiles
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.risk_profiles (
  id                       BIGSERIAL PRIMARY KEY,
  user_id                  BIGINT UNIQUE NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,

  -- Computed outputs
  risk_score               FLOAT NOT NULL DEFAULT 50,          -- 0–100
  investor_type            TEXT NOT NULL DEFAULT 'beginner'
                             CHECK (investor_type IN ('beginner', 'intermediate', 'experienced')),
  behavioral_bias          TEXT NOT NULL DEFAULT 'balanced'
                             CHECK (behavioral_bias IN ('loss_averse', 'overconfident', 'balanced')),

  -- Raw answers + outputs stored as JSON
  questionnaire_responses  JSONB,                              -- {question_id: answer_index}
  recommended_allocation   JSONB,                              -- {"Equity": 45, "MF": 25, ...}

  -- Extracted metadata (also queryable as columns for fast filtering)
  investment_goal          TEXT,
  time_horizon_years       INT,
  max_acceptable_loss_pct  FLOAT,
  tax_bracket              TEXT,
  age                      INT,
  income_range             TEXT,

  -- Dynamic scoring
  behavioral_adjustment    FLOAT NOT NULL DEFAULT 0.0,         -- added/subtracted from base score
  last_computed            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  next_refresh_due         TIMESTAMPTZ,                        -- 90 days from last_computed

  created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at               TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_risk_profiles_user    ON public.risk_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_risk_profiles_refresh ON public.risk_profiles(next_refresh_due);
CREATE INDEX IF NOT EXISTS idx_risk_profiles_qr      ON public.risk_profiles USING GIN (questionnaire_responses);

CREATE TRIGGER set_risk_profiles_updated_at
  BEFORE UPDATE ON public.risk_profiles
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

ALTER TABLE public.risk_profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "risk_profiles: own read"
  ON public.risk_profiles FOR SELECT
  USING (user_id IN (SELECT id FROM public.users WHERE supabase_uid = auth.uid()));

CREATE POLICY "risk_profiles: own insert"
  ON public.risk_profiles FOR INSERT
  WITH CHECK (user_id IN (SELECT id FROM public.users WHERE supabase_uid = auth.uid()));

CREATE POLICY "risk_profiles: own update"
  ON public.risk_profiles FOR UPDATE
  USING (user_id IN (SELECT id FROM public.users WHERE supabase_uid = auth.uid()));


-- ----------------------------------------------------------------------------
-- 3. behavioral_signals
-- Logged from app actions (panic-sell attempt, frequent check, held through dip)
-- Used by the 90-day risk refresh job.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.behavioral_signals (
  id           BIGSERIAL PRIMARY KEY,
  user_id      BIGINT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  signal_type  TEXT NOT NULL
                 CHECK (signal_type IN (
                   'panic_sell', 'frequent_check', 'held_during_dip',
                   'increased_position_dip', 'withdrew_during_rally',
                   'fomo_buy', 'ignored_alert'
                 )),
  metadata     JSONB,                                           -- {market_drop_pct, portfolio_value, ...}
  timestamp    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_bsig_user      ON public.behavioral_signals(user_id);
CREATE INDEX IF NOT EXISTS idx_bsig_type      ON public.behavioral_signals(signal_type);
CREATE INDEX IF NOT EXISTS idx_bsig_timestamp ON public.behavioral_signals(timestamp DESC);

ALTER TABLE public.behavioral_signals ENABLE ROW LEVEL SECURITY;

CREATE POLICY "behavioral_signals: own read"
  ON public.behavioral_signals FOR SELECT
  USING (user_id IN (SELECT id FROM public.users WHERE supabase_uid = auth.uid()));

CREATE POLICY "behavioral_signals: own insert"
  ON public.behavioral_signals FOR INSERT
  WITH CHECK (user_id IN (SELECT id FROM public.users WHERE supabase_uid = auth.uid()));


-- ============================================================================
-- GROUP 2: PORTFOLIO & HOLDINGS
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 4. portfolios
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.portfolios (
  id              BIGSERIAL PRIMARY KEY,
  user_id         BIGINT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  name            TEXT NOT NULL DEFAULT 'My Portfolio',
  total_invested  FLOAT NOT NULL DEFAULT 0.0,                  -- sum of capital deployed
  current_value   FLOAT NOT NULL DEFAULT 0.0,                  -- refreshed by daily Celery job
  is_paper        BOOLEAN NOT NULL DEFAULT FALSE,               -- paper trading portfolio
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_portfolios_user ON public.portfolios(user_id);

CREATE TRIGGER set_portfolios_updated_at
  BEFORE UPDATE ON public.portfolios
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

ALTER TABLE public.portfolios ENABLE ROW LEVEL SECURITY;

CREATE POLICY "portfolios: own read"
  ON public.portfolios FOR SELECT
  USING (user_id IN (SELECT id FROM public.users WHERE supabase_uid = auth.uid()));

CREATE POLICY "portfolios: own insert"
  ON public.portfolios FOR INSERT
  WITH CHECK (user_id IN (SELECT id FROM public.users WHERE supabase_uid = auth.uid()));

CREATE POLICY "portfolios: own update"
  ON public.portfolios FOR UPDATE
  USING (user_id IN (SELECT id FROM public.users WHERE supabase_uid = auth.uid()));

CREATE POLICY "portfolios: own delete"
  ON public.portfolios FOR DELETE
  USING (user_id IN (SELECT id FROM public.users WHERE supabase_uid = auth.uid()));


-- ----------------------------------------------------------------------------
-- 5. assets  (no RLS — public market data, no user data)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.assets (
  id               BIGSERIAL PRIMARY KEY,
  symbol           TEXT UNIQUE NOT NULL,                        -- RELIANCE.NS, INF090I01239
  name             TEXT NOT NULL,
  asset_class      TEXT NOT NULL
                     CHECK (asset_class IN (
                       'equity', 'mutual_fund', 'etf', 'bond',
                       'gold', 'silver', 'reit', 'fixed_deposit', 'crypto', 'cash'
                     )),
  sector           TEXT,                                        -- IT, BFSI, Pharma, ...
  market_cap_tier  TEXT CHECK (market_cap_tier IN ('large', 'mid', 'small', 'micro')),
  exchange         TEXT NOT NULL DEFAULT 'NSE',                 -- NSE, BSE, MCX, MF
  isin             TEXT,
  is_active        BOOLEAN NOT NULL DEFAULT TRUE,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_assets_symbol     ON public.assets(symbol);
CREATE INDEX IF NOT EXISTS idx_assets_class      ON public.assets(asset_class);
CREATE INDEX IF NOT EXISTS idx_assets_sector     ON public.assets(sector);
CREATE INDEX IF NOT EXISTS idx_assets_name_trgm  ON public.assets USING GIN (name gin_trgm_ops);


-- ----------------------------------------------------------------------------
-- 6. holdings
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.holdings (
  id             BIGSERIAL PRIMARY KEY,
  portfolio_id   BIGINT NOT NULL REFERENCES public.portfolios(id) ON DELETE CASCADE,
  asset_id       BIGINT NOT NULL REFERENCES public.assets(id),
  quantity       FLOAT NOT NULL CHECK (quantity > 0),
  buy_price      FLOAT NOT NULL CHECK (buy_price >= 0),
  buy_date       DATE,
  current_price  FLOAT,                                         -- updated by daily pipeline
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_holdings_portfolio ON public.holdings(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_holdings_asset     ON public.holdings(asset_id);

ALTER TABLE public.holdings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "holdings: portfolio owner read"
  ON public.holdings FOR SELECT
  USING (portfolio_id IN (
    SELECT id FROM public.portfolios
    WHERE user_id IN (SELECT id FROM public.users WHERE supabase_uid = auth.uid())
  ));

CREATE POLICY "holdings: portfolio owner insert"
  ON public.holdings FOR INSERT
  WITH CHECK (portfolio_id IN (
    SELECT id FROM public.portfolios
    WHERE user_id IN (SELECT id FROM public.users WHERE supabase_uid = auth.uid())
  ));

CREATE POLICY "holdings: portfolio owner update"
  ON public.holdings FOR UPDATE
  USING (portfolio_id IN (
    SELECT id FROM public.portfolios
    WHERE user_id IN (SELECT id FROM public.users WHERE supabase_uid = auth.uid())
  ));

CREATE POLICY "holdings: portfolio owner delete"
  ON public.holdings FOR DELETE
  USING (portfolio_id IN (
    SELECT id FROM public.portfolios
    WHERE user_id IN (SELECT id FROM public.users WHERE supabase_uid = auth.uid())
  ));


-- ----------------------------------------------------------------------------
-- 7. target_allocations
-- Desired asset-class split for a portfolio (used for drift detection).
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.target_allocations (
  id             BIGSERIAL PRIMARY KEY,
  portfolio_id   BIGINT NOT NULL REFERENCES public.portfolios(id) ON DELETE CASCADE,
  asset_class    TEXT NOT NULL,                                 -- equity, bond, gold, cash, ...
  target_pct     FLOAT NOT NULL CHECK (target_pct >= 0 AND target_pct <= 100),
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (portfolio_id, asset_class)
);

CREATE INDEX IF NOT EXISTS idx_target_alloc_portfolio ON public.target_allocations(portfolio_id);

CREATE TRIGGER set_target_alloc_updated_at
  BEFORE UPDATE ON public.target_allocations
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

ALTER TABLE public.target_allocations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "target_allocations: portfolio owner"
  ON public.target_allocations FOR ALL
  USING (portfolio_id IN (
    SELECT id FROM public.portfolios
    WHERE user_id IN (SELECT id FROM public.users WHERE supabase_uid = auth.uid())
  ));


-- ----------------------------------------------------------------------------
-- 8. transactions
-- Every buy / sell event — full audit trail + P&L history.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.transactions (
  id                BIGSERIAL PRIMARY KEY,
  portfolio_id      BIGINT NOT NULL REFERENCES public.portfolios(id) ON DELETE CASCADE,
  asset_id          BIGINT NOT NULL REFERENCES public.assets(id),
  transaction_type  TEXT NOT NULL CHECK (transaction_type IN ('buy', 'sell')),
  quantity          FLOAT NOT NULL CHECK (quantity > 0),
  price             FLOAT NOT NULL CHECK (price >= 0),
  total_value       FLOAT NOT NULL,                             -- quantity × price
  is_paper          BOOLEAN NOT NULL DEFAULT FALSE,
  notes             TEXT,
  executed_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_txn_portfolio    ON public.transactions(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_txn_asset        ON public.transactions(asset_id);
CREATE INDEX IF NOT EXISTS idx_txn_executed_at  ON public.transactions(executed_at DESC);

ALTER TABLE public.transactions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "transactions: portfolio owner"
  ON public.transactions FOR ALL
  USING (portfolio_id IN (
    SELECT id FROM public.portfolios
    WHERE user_id IN (SELECT id FROM public.users WHERE supabase_uid = auth.uid())
  ));


-- ----------------------------------------------------------------------------
-- 9. drift_alerts
-- Generated by nightly Celery task. Enable Supabase Realtime on this table.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.drift_alerts (
  id            BIGSERIAL PRIMARY KEY,
  portfolio_id  BIGINT NOT NULL REFERENCES public.portfolios(id) ON DELETE CASCADE,
  asset_class   TEXT NOT NULL,
  actual_pct    FLOAT NOT NULL,
  target_pct    FLOAT NOT NULL,
  drift_pct     FLOAT NOT NULL,                                 -- actual - target
  severity      TEXT NOT NULL CHECK (severity IN ('info', 'warn', 'alert')),
  is_read       BOOLEAN NOT NULL DEFAULT FALSE,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_drift_portfolio  ON public.drift_alerts(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_drift_severity   ON public.drift_alerts(severity);
CREATE INDEX IF NOT EXISTS idx_drift_unread     ON public.drift_alerts(is_read) WHERE is_read = FALSE;

ALTER TABLE public.drift_alerts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "drift_alerts: portfolio owner"
  ON public.drift_alerts FOR ALL
  USING (portfolio_id IN (
    SELECT id FROM public.portfolios
    WHERE user_id IN (SELECT id FROM public.users WHERE supabase_uid = auth.uid())
  ));

-- Enable Realtime for instant push to frontend:
-- ALTER PUBLICATION supabase_realtime ADD TABLE public.drift_alerts;


-- ============================================================================
-- GROUP 3: MARKET DATA
-- Note: prices + features will grow to millions of rows.
-- Partitioned by year for performance.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 10. prices  (OHLCV — partitioned by year)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.prices (
  id            BIGSERIAL,
  asset_id      BIGINT NOT NULL REFERENCES public.assets(id) ON DELETE CASCADE,
  date          DATE NOT NULL,
  open          FLOAT NOT NULL,
  high          FLOAT NOT NULL,
  low           FLOAT NOT NULL,
  close         FLOAT NOT NULL,
  adj_close     FLOAT,
  volume        FLOAT,
  delivery_pct  FLOAT,                                          -- NSE delivery volume %
  PRIMARY KEY (id, date),
  UNIQUE (asset_id, date)
) PARTITION BY RANGE (date);

-- Create yearly partitions (extend as needed)
CREATE TABLE IF NOT EXISTS public.prices_2020 PARTITION OF public.prices
  FOR VALUES FROM ('2020-01-01') TO ('2021-01-01');
CREATE TABLE IF NOT EXISTS public.prices_2021 PARTITION OF public.prices
  FOR VALUES FROM ('2021-01-01') TO ('2022-01-01');
CREATE TABLE IF NOT EXISTS public.prices_2022 PARTITION OF public.prices
  FOR VALUES FROM ('2022-01-01') TO ('2023-01-01');
CREATE TABLE IF NOT EXISTS public.prices_2023 PARTITION OF public.prices
  FOR VALUES FROM ('2023-01-01') TO ('2024-01-01');
CREATE TABLE IF NOT EXISTS public.prices_2024 PARTITION OF public.prices
  FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
CREATE TABLE IF NOT EXISTS public.prices_2025 PARTITION OF public.prices
  FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');
CREATE TABLE IF NOT EXISTS public.prices_2026 PARTITION OF public.prices
  FOR VALUES FROM ('2026-01-01') TO ('2027-01-01');

CREATE INDEX IF NOT EXISTS idx_prices_asset_date ON public.prices(asset_id, date DESC);
CREATE INDEX IF NOT EXISTS idx_prices_date       ON public.prices(date DESC);

-- No RLS needed — prices are public market data


-- ----------------------------------------------------------------------------
-- 11. features  (pre-computed ML features — partitioned by year)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.features (
  id                       BIGSERIAL,
  asset_id                 BIGINT NOT NULL REFERENCES public.assets(id) ON DELETE CASCADE,
  date                     DATE NOT NULL,

  -- Technical indicators
  rsi_14                   FLOAT,
  macd                     FLOAT,
  macd_signal              FLOAT,
  macd_hist                FLOAT,
  bollinger_upper          FLOAT,
  bollinger_lower          FLOAT,
  bollinger_pct            FLOAT,
  atr_14                   FLOAT,
  obv                      FLOAT,
  williams_r               FLOAT,
  stochastic_k             FLOAT,
  stochastic_d             FLOAT,
  adx                      FLOAT,

  -- Return features
  return_1d                FLOAT,
  return_5d                FLOAT,
  return_21d               FLOAT,
  return_63d               FLOAT,
  volatility_21d           FLOAT,

  -- Cross-sectional / market
  beta_nifty50             FLOAT,
  distance_52w_high        FLOAT,
  distance_52w_low         FLOAT,
  relative_strength_nifty  FLOAT,
  sector_momentum_rank     FLOAT,

  -- ML training labels (forward returns)
  fwd_return_1d            FLOAT,
  fwd_return_5d            FLOAT,
  fwd_return_21d           FLOAT,

  PRIMARY KEY (id, date),
  UNIQUE (asset_id, date)
) PARTITION BY RANGE (date);

CREATE TABLE IF NOT EXISTS public.features_2020 PARTITION OF public.features
  FOR VALUES FROM ('2020-01-01') TO ('2021-01-01');
CREATE TABLE IF NOT EXISTS public.features_2021 PARTITION OF public.features
  FOR VALUES FROM ('2021-01-01') TO ('2022-01-01');
CREATE TABLE IF NOT EXISTS public.features_2022 PARTITION OF public.features
  FOR VALUES FROM ('2022-01-01') TO ('2023-01-01');
CREATE TABLE IF NOT EXISTS public.features_2023 PARTITION OF public.features
  FOR VALUES FROM ('2023-01-01') TO ('2024-01-01');
CREATE TABLE IF NOT EXISTS public.features_2024 PARTITION OF public.features
  FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
CREATE TABLE IF NOT EXISTS public.features_2025 PARTITION OF public.features
  FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');
CREATE TABLE IF NOT EXISTS public.features_2026 PARTITION OF public.features
  FOR VALUES FROM ('2026-01-01') TO ('2027-01-01');

CREATE INDEX IF NOT EXISTS idx_features_asset_date ON public.features(asset_id, date DESC);


-- ============================================================================
-- GROUP 4: AI OUTPUTS
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 12. recommendations
-- Enable Supabase Realtime on this table for instant push to frontend.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.recommendations (
  id                    BIGSERIAL PRIMARY KEY,
  user_id               BIGINT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  portfolio_id          BIGINT REFERENCES public.portfolios(id) ON DELETE SET NULL,
  recommendation_type   TEXT NOT NULL
                          CHECK (recommendation_type IN (
                            'rebalance', 'new_investment', 'risk_alert',
                            'drift_alert', 'ml_signal', 'tax_harvesting',
                            'goal_milestone', 'market_alert'
                          )),
  title                 TEXT NOT NULL,
  summary               TEXT NOT NULL,                          -- 1–2 sentences (free tier)
  detailed_explanation  TEXT,                                   -- full explanation (paid tier)
  full_report_json      JSONB,                                  -- PDF report data (paid tier)
  suggested_actions     JSONB,                                  -- [{action, symbol, amount, reason}]
  confidence_score      FLOAT CHECK (confidence_score >= 0 AND confidence_score <= 1),
  disclaimer            TEXT NOT NULL DEFAULT
                          'FinVoice is a decision-support tool. Invest at your own risk. Consult a SEBI-registered advisor for personalised advice.',
  is_read               BOOLEAN NOT NULL DEFAULT FALSE,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rec_user       ON public.recommendations(user_id);
CREATE INDEX IF NOT EXISTS idx_rec_type       ON public.recommendations(recommendation_type);
CREATE INDEX IF NOT EXISTS idx_rec_unread     ON public.recommendations(is_read) WHERE is_read = FALSE;
CREATE INDEX IF NOT EXISTS idx_rec_created    ON public.recommendations(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_rec_actions    ON public.recommendations USING GIN (suggested_actions);

ALTER TABLE public.recommendations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "recommendations: own read"
  ON public.recommendations FOR SELECT
  USING (user_id IN (SELECT id FROM public.users WHERE supabase_uid = auth.uid()));

-- ALTER PUBLICATION supabase_realtime ADD TABLE public.recommendations;


-- ----------------------------------------------------------------------------
-- 13. explanations  (XAI — 1:1 with recommendations)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.explanations (
  id                            BIGSERIAL PRIMARY KEY,
  recommendation_id             BIGINT UNIQUE NOT NULL
                                  REFERENCES public.recommendations(id) ON DELETE CASCADE,

  -- SHAP / feature importance
  shap_values                   JSONB,                          -- {feature_name: shap_value}
  top_features                  JSONB,                          -- [{feature, value, direction}]
  feature_importance_chart_url  TEXT,                           -- Supabase Storage URL

  -- Barra-style factor attribution
  market_beta_contribution      FLOAT,
  sector_tilt_contribution      FLOAT,
  stock_alpha_contribution      FLOAT,
  unexplained_noise             FLOAT,

  -- NLG text (tiered)
  short_explanation             TEXT,                           -- 1 sentence (free)
  medium_explanation            TEXT,                           -- 3–4 factors (paid)
  full_explanation              TEXT,                           -- detailed (paid report)

  -- Market context
  market_regime                 TEXT
                                  CHECK (market_regime IN ('bull', 'bear', 'sideways', 'high_vol')),
  regime_impact_note            TEXT,

  created_at                    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_exp_recommendation ON public.explanations(recommendation_id);
CREATE INDEX IF NOT EXISTS idx_exp_shap           ON public.explanations USING GIN (shap_values);

ALTER TABLE public.explanations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "explanations: own read via recommendation"
  ON public.explanations FOR SELECT
  USING (recommendation_id IN (
    SELECT id FROM public.recommendations
    WHERE user_id IN (SELECT id FROM public.users WHERE supabase_uid = auth.uid())
  ));


-- ============================================================================
-- GROUP 5: CALL AGENT
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 14. call_sessions
-- Every inbound/outbound Vapi call — with transcript and outcome.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.call_sessions (
  id               BIGSERIAL PRIMARY KEY,
  user_id          BIGINT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  vapi_call_id     TEXT UNIQUE,                                 -- Vapi's call identifier
  direction        TEXT NOT NULL DEFAULT 'outbound'
                     CHECK (direction IN ('inbound', 'outbound')),
  trigger_type     TEXT
                     CHECK (trigger_type IN (
                       'market_alert', 'drift_alert', 'scheduled_briefing',
                       'user_initiated', 'behavioral_guardrail',
                       'goal_milestone', 'sip_confirmation', 'tax_alert'
                     )),
  status           TEXT NOT NULL DEFAULT 'initiated'
                     CHECK (status IN ('initiated', 'ringing', 'in_progress', 'completed', 'failed', 'no_answer')),
  transcript       TEXT,                                        -- full call transcript
  summary          TEXT,                                        -- AI-generated summary
  duration_seconds INT CHECK (duration_seconds >= 0),
  sentiment        TEXT CHECK (sentiment IN ('positive', 'neutral', 'negative', 'anxious')),
  actions_taken    JSONB,                                       -- [{action, result}] from call
  initiated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  ended_at         TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_calls_user         ON public.call_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_calls_trigger      ON public.call_sessions(trigger_type);
CREATE INDEX IF NOT EXISTS idx_calls_status       ON public.call_sessions(status);
CREATE INDEX IF NOT EXISTS idx_calls_initiated_at ON public.call_sessions(initiated_at DESC);
CREATE INDEX IF NOT EXISTS idx_calls_vapi_id      ON public.call_sessions(vapi_call_id);

ALTER TABLE public.call_sessions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "call_sessions: own read"
  ON public.call_sessions FOR SELECT
  USING (user_id IN (SELECT id FROM public.users WHERE supabase_uid = auth.uid()));

-- Backend service role can insert (Vapi webhook)
CREATE POLICY "call_sessions: service insert"
  ON public.call_sessions FOR INSERT
  WITH CHECK (TRUE);                                            -- restrict further with service_role key


-- ----------------------------------------------------------------------------
-- 15. call_triggers
-- Scheduled / condition-based trigger config per user.
-- "Call me every Monday at 8am" or "alert me if Nifty drops > 5%"
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.call_triggers (
  id                BIGSERIAL PRIMARY KEY,
  user_id           BIGINT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  trigger_type      TEXT NOT NULL
                      CHECK (trigger_type IN (
                        'market_alert', 'drift_alert', 'scheduled_briefing',
                        'behavioral_guardrail', 'goal_milestone', 'sip_confirmation'
                      )),
  is_enabled        BOOLEAN NOT NULL DEFAULT TRUE,

  -- For scheduled calls
  schedule_cron     TEXT,                                       -- e.g. '0 8 * * MON'
  timezone          TEXT NOT NULL DEFAULT 'Asia/Kolkata',

  -- For condition-based triggers
  condition_json    JSONB,                                      -- {metric: 'nifty_drop_pct', threshold: 5}

  last_triggered_at TIMESTAMPTZ,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_call_triggers_user    ON public.call_triggers(user_id);
CREATE INDEX IF NOT EXISTS idx_call_triggers_enabled ON public.call_triggers(is_enabled) WHERE is_enabled = TRUE;

CREATE TRIGGER set_call_triggers_updated_at
  BEFORE UPDATE ON public.call_triggers
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

ALTER TABLE public.call_triggers ENABLE ROW LEVEL SECURITY;

CREATE POLICY "call_triggers: own"
  ON public.call_triggers FOR ALL
  USING (user_id IN (SELECT id FROM public.users WHERE supabase_uid = auth.uid()));


-- ============================================================================
-- AUTO-CREATE USER ROW ON SUPABASE AUTH SIGNUP
-- This function fires whenever a new user signs up via Supabase Auth.
-- ============================================================================
CREATE OR REPLACE FUNCTION public.handle_new_auth_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.users (supabase_uid, email, full_name)
  VALUES (
    NEW.id,
    NEW.email,
    NEW.raw_user_meta_data->>'full_name'
  )
  ON CONFLICT (supabase_uid) DO NOTHING;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Attach to Supabase Auth
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_auth_user();


-- ============================================================================
-- USEFUL VIEWS
-- ============================================================================

-- Portfolio summary view (used by dashboard)
CREATE OR REPLACE VIEW public.portfolio_summary AS
SELECT
  p.id                                                AS portfolio_id,
  p.user_id,
  p.name,
  p.total_invested,
  p.current_value,
  CASE
    WHEN p.total_invested > 0
    THEN ROUND(((p.current_value - p.total_invested) / p.total_invested * 100)::NUMERIC, 2)
    ELSE 0
  END                                                 AS pnl_pct,
  (p.current_value - p.total_invested)                AS pnl_abs,
  COUNT(DISTINCT h.id)                                AS holdings_count,
  COUNT(DISTINCT da.id) FILTER (WHERE da.is_read = FALSE) AS unread_drift_alerts,
  p.is_paper,
  p.updated_at
FROM public.portfolios p
LEFT JOIN public.holdings h   ON h.portfolio_id = p.id
LEFT JOIN public.drift_alerts da ON da.portfolio_id = p.id
GROUP BY p.id;

-- User notification count view (used by navbar badge)
CREATE OR REPLACE VIEW public.user_notification_counts AS
SELECT
  u.id                                                           AS user_id,
  COUNT(DISTINCT r.id)  FILTER (WHERE r.is_read = FALSE)         AS unread_recommendations,
  COUNT(DISTINCT da.id) FILTER (WHERE da.is_read = FALSE)        AS unread_drift_alerts
FROM public.users u
LEFT JOIN public.recommendations r  ON r.user_id = u.id
LEFT JOIN public.portfolios p       ON p.user_id = u.id
LEFT JOIN public.drift_alerts da    ON da.portfolio_id = p.id
GROUP BY u.id;


-- ============================================================================
-- SEED: Default asset classes for target_allocations lookup
-- ============================================================================
-- (No seed needed — target allocations are generated from risk profile output)


-- ============================================================================
-- DONE
-- ============================================================================
-- Tables created: 15
--   users, risk_profiles, behavioral_signals
--   portfolios, assets, holdings, target_allocations, transactions, drift_alerts
--   prices (partitioned), features (partitioned)
--   recommendations, explanations
--   call_sessions, call_triggers
-- Views: portfolio_summary, user_notification_counts
-- Triggers: updated_at on 6 tables, auto-user-create on auth signup
-- RLS: enabled on all user-data tables
-- ============================================================================
