"""
FinVoice — Risk Profiler Service
Compact adaptive questionnaire: 12–13 questions per user.
Frontend-driven branching; backend validates by re-simulating the same path.

Produces:
  - Risk score (0-100)
  - Investor type (beginner / intermediate / experienced)
  - Behavioral bias (loss_averse / overconfident / balanced)
  - Recommended asset allocation
"""

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models import RiskProfile, User, BehavioralSignal, InvestorType, BehavioralBiasType


# ══════════════════════════════════════════════════════════════════════════════
# QUESTION BANK  (28 questions total; each user sees 12–13)
# ══════════════════════════════════════════════════════════════════════════════

QUESTIONS = [
    # ── UNIVERSAL Q1–Q5 ───────────────────────────────────────────────────────
    {
        "id": "age_bracket", "section": "foundation",
        "text": "Which age group do you belong to?",
        "type": "radio",
        "options": [
            {"label": "Under 25",  "score": 20},
            {"label": "25–35",     "score": 17},
            {"label": "36–45",     "score": 13},
            {"label": "46–55",     "score": 8},
            {"label": "56+",       "score": 3},
        ],
    },
    {
        "id": "dependents", "section": "foundation",
        "text": "How many people depend on you financially?",
        "type": "radio",
        "options": [
            {"label": "None — just myself", "score": 10},
            {"label": "1–2 people",          "score": 7},
            {"label": "3–4 people",          "score": 4},
            {"label": "5 or more",           "score": 1},
        ],
    },
    {
        "id": "employment", "section": "foundation",
        "text": "What best describes your work situation?",
        "type": "radio",
        "options": [
            {"label": "Government / public sector job",     "score": 10},
            {"label": "Private company — salaried",        "score": 8},
            {"label": "Self-employed / freelancer",        "score": 5},
            {"label": "Business owner",                    "score": 6},
            {"label": "Student / not currently earning",   "score": 3},
            {"label": "Retired",                           "score": 2},
        ],
    },
    {
        "id": "emergency_buffer", "section": "foundation",
        "text": "If you lost your income today, how long could you manage with your savings?",
        "type": "radio",
        "options": [
            {"label": "Less than 1 month", "score": 0},
            {"label": "1–3 months",        "score": 3},
            {"label": "3–6 months",        "score": 6},
            {"label": "6–12 months",       "score": 8},
            {"label": "More than a year",  "score": 10},
        ],
    },
    {
        "id": "investing_experience", "section": "foundation", "tier_splitter": True,
        "text": "Which best describes your investing journey so far?",
        "type": "radio",
        "options": [
            {"label": "Never invested. My money sits in a savings account or FD.",            "score": 2,  "tier": "beginner"},
            {"label": "Done a few SIPs or mutual funds, but I don't follow markets.",         "score": 5,  "tier": "beginner"},
            {"label": "I invest regularly in mutual funds / stocks and understand the basics.","score": 10, "tier": "intermediate"},
            {"label": "I actively manage my portfolio — fundamentals / technicals.",           "score": 15, "tier": "expert"},
            {"label": "I trade options/futures, use leverage, manage complex positions.",      "score": 18, "tier": "expert"},
        ],
    },

    # ── BEGINNER PATH (Q6–Q12) ────────────────────────────────────────────────
    {
        "id": "b_goal", "section": "financial", "tier": "beginner",
        "text": "What is the main reason you want to start investing?",
        "type": "radio",
        "options": [
            {"label": "My savings are losing value to inflation",               "score": 5},
            {"label": "I have a big goal in 2–5 years (wedding, car, home)",   "score": 8},
            {"label": "I want to build wealth slowly over the long term",       "score": 14},
            {"label": "Saving for retirement or my children's future",          "score": 12},
            {"label": "No specific goal — I just want to start somewhere",      "score": 9},
        ],
    },
    {
        "id": "b_time_horizon", "section": "financial", "tier": "beginner",
        "text": "How long can you leave this money invested without needing it back?",
        "type": "radio",
        "options": [
            {"label": "Less than 1 year — I might need it anytime", "score": 2},
            {"label": "1–3 years",                                   "score": 5},
            {"label": "3–5 years",                                   "score": 9},
            {"label": "5–10 years",                                  "score": 13},
            {"label": "10+ years — I'm in no rush at all",           "score": 17},
        ],
    },
    {
        "id": "b_max_loss", "section": "behavioral", "tier": "beginner", "conditional": True,
        "text": "Which situation would actually make you sell your investments?",
        "type": "radio",
        "options": [
            {"label": "Any loss — I can't see my balance go down",                      "score": 1,  "bias": "loss_averse"},
            {"label": "A 10% drop (₹10,000 on every ₹1 lakh invested)",                "score": 4,  "bias": "loss_averse"},
            {"label": "A 20% drop (₹20,000 on every ₹1 lakh invested)",                "score": 8},
            {"label": "A 35%+ drop — even then I'd think twice before selling",         "score": 13, "bias": "balanced"},
            {"label": "I wouldn't sell regardless of how far it falls",                 "score": 17, "bias": "overconfident"},
        ],
    },
    {
        "id": "b_invest_amount", "section": "financial", "tier": "beginner",
        "text": "How much could you invest every month, even in small amounts?",
        "type": "radio",
        "options": [
            {"label": "Under ₹500 / month",         "score": 2},
            {"label": "₹500 – ₹2,000 / month",      "score": 4},
            {"label": "₹2,000 – ₹5,000 / month",    "score": 6},
            {"label": "₹5,000 – ₹15,000 / month",   "score": 8},
            {"label": "More than ₹15,000 / month",  "score": 10},
        ],
    },
    {
        "id": "b_gift_scenario", "section": "behavioral", "tier": "beginner",
        "text": "Someone gifts you ₹1,00,000 today. How would you use it?",
        "type": "radio",
        "options": [
            {"label": "Keep all of it in a bank FD — I can't risk losing even ₹1",          "score": 2,  "bias": "loss_averse"},
            {"label": "Keep ₹80,000 safe; invest ₹20,000 in something that could grow",     "score": 6},
            {"label": "Split equally — half safe, half in growth investments",               "score": 10, "bias": "balanced"},
            {"label": "Invest ₹80,000 or more — ups and downs are fine for me",             "score": 14, "bias": "overconfident"},
        ],
    },
    {
        "id": "b_drop_test", "section": "behavioral", "tier": "beginner",
        "text": "You invest ₹5,000/month. After 6 months (₹30,000 invested) your balance shows ₹25,000. What do you do?",
        "type": "radio",
        "options": [
            {"label": "Stop and withdraw everything immediately",           "score": 1,  "bias": "loss_averse"},
            {"label": "Stop adding money but leave what's already there",   "score": 4,  "bias": "loss_averse"},
            {"label": "Continue as normal — this kind of dip is expected",  "score": 10, "bias": "balanced"},
            {"label": "Invest even more — I'm buying at a discount!",       "score": 15, "bias": "overconfident"},
        ],
    },
    {
        "id": "b_priority", "section": "behavioral", "tier": "beginner",
        "text": "If you could only pick ONE — what matters most about your money?",
        "type": "radio",
        "options": [
            {"label": "Safety — my money should never go down",                      "score": 3,  "bias": "loss_averse"},
            {"label": "Stability — small, steady growth with minimal bumps",         "score": 7},
            {"label": "Growth — I want it to grow, even with some ups and downs",    "score": 13, "bias": "balanced"},
            {"label": "Maximum returns — I'll take big risks for big rewards",       "score": 17, "bias": "overconfident"},
        ],
    },

    # ── INTERMEDIATE PATH (Q6–Q13) ────────────────────────────────────────────
    {
        "id": "i_annual_income", "section": "financial", "tier": "intermediate",
        "text": "What is your approximate annual household income?",
        "type": "radio",
        "options": [
            {"label": "Under ₹6 LPA",    "score": 3},
            {"label": "₹6–12 LPA",       "score": 6},
            {"label": "₹12–25 LPA",      "score": 9},
            {"label": "₹25–50 LPA",      "score": 12},
            {"label": "Above ₹50 LPA",   "score": 15},
        ],
    },
    {
        "id": "i_portfolio_size", "section": "financial", "tier": "intermediate",
        "text": "What is your current total investment value?",
        "sub": "Across all instruments — MFs, stocks, FDs, gold. Exclude your primary home and emergency fund.",
        "type": "radio",
        "options": [
            {"label": "Under ₹1 Lakh",          "score": 3},
            {"label": "₹1–5 Lakh",              "score": 5},
            {"label": "₹5–25 Lakh",             "score": 8},
            {"label": "₹25 Lakh – ₹1 Crore",   "score": 11},
            {"label": "Above ₹1 Crore",         "score": 14},
        ],
    },
    {
        "id": "i_debt", "section": "financial", "tier": "intermediate", "conditional": True,
        "text": "What is your current debt situation?",
        "type": "radio",
        "options": [
            {"label": "Completely debt-free",                   "score": 10},
            {"label": "Only home loan with comfortable EMI",    "score": 8},
            {"label": "Home loan + one other loan",             "score": 5},
            {"label": "Multiple loans or heavy EMI burden",     "score": 2},
        ],
    },
    {
        "id": "i_primary_goal", "section": "financial", "tier": "intermediate",
        "text": "What is your primary investment goal?",
        "type": "radio",
        "options": [
            {"label": "Long-term wealth creation (10+ years)",  "score": 15},
            {"label": "Retirement planning",                    "score": 12},
            {"label": "Child's education or marriage fund",     "score": 10},
            {"label": "Buying a home in 3–7 years",            "score": 7},
            {"label": "Regular income or cash flow",            "score": 4},
            {"label": "Tax saving (ELSS, NPS)",                "score": 6},
        ],
    },
    {
        "id": "i_time_horizon", "section": "financial", "tier": "intermediate",
        "text": "What is your primary investment time horizon?",
        "type": "radio",
        "options": [
            {"label": "Less than 1 year",   "score": 2},
            {"label": "1–3 years",          "score": 5},
            {"label": "3–5 years",          "score": 9},
            {"label": "5–10 years",         "score": 14},
            {"label": "More than 10 years", "score": 18},
        ],
    },
    {
        "id": "i_crash_scenario", "section": "behavioral", "tier": "intermediate",
        "text": "Your portfolio drops 25% in 3 months during a market correction. What do you do?",
        "sub": "Answer honestly — not what sounds 'smart'. Your real reaction matters most.",
        "type": "radio",
        "options": [
            {"label": "Sell everything to stop further losses",                     "score": 2,  "bias": "loss_averse"},
            {"label": "Sell a portion to reduce exposure",                          "score": 5,  "bias": "loss_averse"},
            {"label": "Do nothing — wait for recovery",                             "score": 10, "bias": "balanced"},
            {"label": "Review fundamentals and buy more if thesis holds",           "score": 14, "bias": "balanced"},
            {"label": "Aggressively buy more — crashes are the best entry points",  "score": 17, "bias": "overconfident"},
        ],
    },
    {
        "id": "i_max_loss", "section": "behavioral", "tier": "intermediate",
        "text": "What is the maximum portfolio loss you could tolerate in a single year?",
        "sub": "Think in actual rupees, not abstract percentages.",
        "type": "radio",
        "options": [
            {"label": "0% — I cannot tolerate any loss",                    "score": 1,  "bias": "loss_averse"},
            {"label": "Up to 5%",                                           "score": 4},
            {"label": "Up to 10%",                                          "score": 7},
            {"label": "Up to 20%",                                          "score": 11},
            {"label": "Up to 30%",                                          "score": 15},
            {"label": "More than 30% — fine for long-term gains",           "score": 18, "bias": "overconfident"},
        ],
    },
    {
        "id": "i_past_panic", "section": "behavioral", "tier": "intermediate",
        "text": "Have you ever panic-sold investments during a crash and later regretted it?",
        "sub": "Past behavior under real stress is the strongest predictor of future behavior.",
        "type": "radio",
        "options": [
            {"label": "Yes — and I've done it more than once",          "score": 2,  "bias": "loss_averse"},
            {"label": "Yes — once. I learned from it.",                 "score": 5,  "bias": "loss_averse"},
            {"label": "No — I've stayed the course through dips",       "score": 12, "bias": "balanced"},
            {"label": "I haven't experienced a real market crash yet",  "score": 7},
        ],
    },

    # ── EXPERT PATH (Q6–Q13) ──────────────────────────────────────────────────
    {
        "id": "e_portfolio_size", "section": "financial", "tier": "expert",
        "text": "Total portfolio value (excluding primary residence)?",
        "type": "radio",
        "options": [
            {"label": "Under ₹10 Lakh",          "score": 4},
            {"label": "₹10–50 Lakh",             "score": 7},
            {"label": "₹50 Lakh – ₹2 Crore",    "score": 10},
            {"label": "₹2–10 Crore",             "score": 13},
            {"label": "Above ₹10 Crore",         "score": 16},
        ],
    },
    {
        "id": "e_savings_rate", "section": "financial", "tier": "expert",
        "text": "What percentage of your income do you invest monthly?",
        "type": "radio",
        "options": [
            {"label": "Under 15%",  "score": 4},
            {"label": "15–30%",     "score": 7},
            {"label": "30–50%",     "score": 10},
            {"label": "Above 50%",  "score": 13},
        ],
    },
    {
        "id": "e_primary_goal", "section": "financial", "tier": "expert",
        "text": "Primary investment objective?",
        "type": "radio",
        "options": [
            {"label": "Aggressive wealth creation",              "score": 16},
            {"label": "Retirement corpus building",              "score": 12},
            {"label": "Portfolio income / FIRE",                 "score": 10},
            {"label": "Capital preservation with real returns",  "score": 5},
            {"label": "Multi-goal (diversified objectives)",     "score": 9},
        ],
    },
    {
        "id": "e_time_horizon", "section": "financial", "tier": "expert",
        "text": "Investment time horizon for your primary goal?",
        "type": "radio",
        "options": [
            {"label": "Under 3 years",          "score": 3},
            {"label": "3–5 years",              "score": 7},
            {"label": "5–10 years",             "score": 12},
            {"label": "10–20 years",            "score": 16},
            {"label": "20+ years or perpetual", "score": 18},
        ],
    },
    {
        "id": "e_liquidity_need", "section": "financial", "tier": "expert", "conditional": True,
        "text": "How important is portfolio liquidity to you?",
        "type": "radio",
        "options": [
            {"label": "Critical — need access within weeks",        "score": 2},
            {"label": "Important — within 6 months max",            "score": 5},
            {"label": "Moderate — can lock up for 1–3 years",       "score": 9},
            {"label": "Low — comfortable with 3+ year lock-ins",    "score": 14},
        ],
    },
    {
        "id": "e_drawdown_experience", "section": "behavioral", "tier": "expert",
        "text": "Largest portfolio drawdown you've held through without selling?",
        "sub": "Actual lived experience matters far more than theoretical tolerance.",
        "type": "radio",
        "options": [
            {"label": "Less than 10%",                              "score": 4},
            {"label": "10–20%",                                     "score": 7},
            {"label": "20–35%",                                     "score": 11},
            {"label": "35–50%",                                     "score": 15},
            {"label": "50%+ (held through 2008 or March 2020)",     "score": 18},
        ],
    },
    {
        "id": "e_max_loss", "section": "behavioral", "tier": "expert",
        "text": "Maximum acceptable annual portfolio drawdown?",
        "type": "radio",
        "options": [
            {"label": "Under 10%",                              "score": 4},
            {"label": "10–20%",                                 "score": 8},
            {"label": "20–30%",                                 "score": 12},
            {"label": "30–40%",                                 "score": 16},
            {"label": "40%+ acceptable for outsized returns",  "score": 19},
        ],
    },
    {
        "id": "e_crisis_behavior", "section": "behavioral", "tier": "expert",
        "text": "How did you handle the March 2020 COVID crash (Nifty fell 38%)?",
        "sub": "If you weren't invested then, pick what you think you would have done.",
        "type": "radio",
        "options": [
            {"label": "Panicked and sold most positions",                        "score": 2,  "bias": "loss_averse"},
            {"label": "Switched to defensive — more debt / gold",               "score": 6,  "bias": "loss_averse"},
            {"label": "Held positions, didn't add fresh money",                 "score": 9,  "bias": "balanced"},
            {"label": "Held and continued SIPs as planned",                     "score": 12, "bias": "balanced"},
            {"label": "Aggressively deployed fresh capital into equities",      "score": 16, "bias": "overconfident"},
        ],
    },
]


# ══════════════════════════════════════════════════════════════════════════════
# PATH SEQUENCES & BRANCH RULES
# ══════════════════════════════════════════════════════════════════════════════

UNIVERSAL_SEQUENCE: list[str] = [
    "age_bracket", "dependents", "employment", "emergency_buffer", "investing_experience",
]

TIER_SEQUENCES: dict[str, list[str]] = {
    "beginner":     ["b_goal", "b_time_horizon", "b_max_loss", "b_invest_amount",
                     "b_gift_scenario", "b_drop_test", "b_priority"],
    "intermediate": ["i_annual_income", "i_portfolio_size", "i_debt", "i_primary_goal",
                     "i_time_horizon", "i_crash_scenario", "i_max_loss", "i_past_panic"],
    "expert":       ["e_portfolio_size", "e_savings_rate", "e_primary_goal", "e_time_horizon",
                     "e_liquidity_need", "e_drawdown_experience", "e_max_loss", "e_crisis_behavior"],
}

# answer_index → forced next question ID (overrides default sequence)
BRANCH_RULES: dict[str, dict[int, str]] = {
    "investing_experience": {0: "b_goal", 1: "b_goal", 2: "i_annual_income",
                             3: "e_portfolio_size", 4: "e_portfolio_size"},
    "b_time_horizon":  {0: "b_invest_amount"},   # < 1 year → skip b_max_loss
    "i_portfolio_size": {0: "i_primary_goal"},   # < ₹1L   → skip i_debt
    "e_time_horizon":  {4: "e_drawdown_experience"},  # perpetual → skip e_liquidity_need
}

QUESTION_MAP: dict[str, dict] = {q["id"]: q for q in QUESTIONS}

SECTION_LABELS: dict[str, str] = {
    "foundation": "Getting to Know You",
    "financial":  "Your Financial Picture",
    "behavioral": "Your Risk Personality",
}

ALLOCATION_TABLE: list[tuple[int, dict[str, int]]] = [
    (25,  {"Equity / Stocks": 10, "Mutual Funds": 15, "Fixed Deposits / Debt": 45, "Gold / SGBs": 15, "Real Estate / REITs": 15}),
    (40,  {"Equity / Stocks": 20, "Mutual Funds": 25, "Fixed Deposits / Debt": 30, "Gold / SGBs": 15, "Real Estate / REITs": 10}),
    (55,  {"Equity / Stocks": 35, "Mutual Funds": 25, "Fixed Deposits / Debt": 20, "Gold / SGBs": 12, "Real Estate / REITs": 8}),
    (70,  {"Equity / Stocks": 45, "Mutual Funds": 25, "Fixed Deposits / Debt": 12, "Gold / SGBs": 10, "Real Estate / REITs": 8}),
    (85,  {"Equity / Stocks": 55, "Mutual Funds": 25, "Fixed Deposits / Debt": 7,  "Gold / SGBs": 7,  "Real Estate / REITs": 6}),
    (101, {"Equity / Stocks": 65, "Mutual Funds": 22, "Fixed Deposits / Debt": 3,  "Gold / SGBs": 5,  "Real Estate / REITs": 5}),
]


# ══════════════════════════════════════════════════════════════════════════════
# PATH SIMULATION
# ══════════════════════════════════════════════════════════════════════════════

def detect_tier(answers: dict[str, Any]) -> str:
    exp = answers.get("investing_experience")
    if exp is None:
        return "beginner"
    tier_map = {0: "beginner", 1: "beginner", 2: "intermediate", 3: "expert", 4: "expert"}
    return tier_map.get(int(exp), "beginner")


def simulate_path(answers: dict[str, Any]) -> list[str]:
    """
    Re-simulate the exact ordered list of question IDs this user saw,
    based on their submitted answers. Mirrors the frontend buildPath() logic.
    """
    tier = detect_tier(answers)
    full_sequence = UNIVERSAL_SEQUENCE + TIER_SEQUENCES[tier]

    path: list[str] = []
    i = 0
    while i < len(full_sequence):
        qid = full_sequence[i]
        path.append(qid)

        ans = answers.get(qid)
        if ans is not None and qid in BRANCH_RULES:
            forced_next = BRANCH_RULES[qid].get(int(ans))
            if forced_next is not None:
                try:
                    forced_idx = full_sequence.index(forced_next)
                    if forced_idx > i:
                        i = forced_idx
                        continue
                except ValueError:
                    pass
        i += 1

    return path


def get_active_questions(answers: dict[str, Any]) -> list[dict]:
    """Return the ordered question objects the user actually answered."""
    path = simulate_path(answers)
    return [QUESTION_MAP[qid] for qid in path if qid in QUESTION_MAP]


# ══════════════════════════════════════════════════════════════════════════════
# SCORING
# ══════════════════════════════════════════════════════════════════════════════

def compute_score_and_bias(answers: dict[str, Any]) -> dict:
    active = get_active_questions(answers)
    raw_score = 0.0
    max_score = 0.0
    bias_votes: dict[str, int] = {"loss_averse": 0, "overconfident": 0, "balanced": 0}

    goal: str | None = None
    horizon_years: int | None = None
    max_loss_pct: float | None = None

    for q in active:
        qid = q["id"]
        ans = answers.get(qid)
        if ans is None:
            continue

        if q["type"] == "radio":
            idx = int(ans)
            if 0 <= idx < len(q["options"]):
                opt = q["options"][idx]
                raw_score += opt.get("score", 0)
                if opt.get("bias"):
                    bias_votes[opt["bias"]] += 1
            max_score += max(o.get("score", 0) for o in q["options"])

        elif q["type"] == "multi":
            indices = ans if isinstance(ans, list) else [ans]
            for idx in indices:
                idx = int(idx)
                if 0 <= idx < len(q["options"]):
                    opt = q["options"][idx]
                    raw_score += opt.get("score", 0)
                    if opt.get("bias"):
                        bias_votes[opt["bias"]] += 1
            max_score += sum(o.get("score", 0) for o in q["options"])

        # Extract metadata
        if qid in ("b_goal", "i_primary_goal", "e_primary_goal"):
            idx = int(ans)
            if 0 <= idx < len(q["options"]):
                goal = q["options"][idx]["label"]

        if qid in ("b_time_horizon", "i_time_horizon", "e_time_horizon"):
            idx = int(ans)
            horizon_map = {0: 1, 1: 2, 2: 4, 3: 7, 4: 15}
            horizon_years = horizon_map.get(idx, 5)
            if qid == "e_time_horizon":
                horizon_map = {0: 2, 1: 4, 2: 7, 3: 15, 4: 25}
                horizon_years = horizon_map.get(idx, 10)

        if qid in ("b_max_loss", "i_max_loss", "e_max_loss"):
            idx = int(ans)
            if qid == "b_max_loss":
                loss_map = {0: 0, 1: 10, 2: 20, 3: 35, 4: 50}
            elif qid == "i_max_loss":
                loss_map = {0: 0, 1: 5, 2: 10, 3: 20, 4: 30, 5: 40}
            else:
                loss_map = {0: 10, 1: 20, 2: 30, 3: 40, 4: 50}
            max_loss_pct = loss_map.get(idx, 15)

    risk_score = (raw_score / max_score * 100) if max_score > 0 else 50
    risk_score = max(0.0, min(100.0, round(risk_score, 1)))

    if risk_score < 35:
        investor_type = InvestorType.BEGINNER
    elif risk_score < 65:
        investor_type = InvestorType.INTERMEDIATE
    else:
        investor_type = InvestorType.EXPERIENCED

    max_votes = max(bias_votes.values())
    if max_votes == 0:
        bias = BehavioralBiasType.BALANCED
    elif bias_votes["loss_averse"] == max_votes:
        bias = BehavioralBiasType.LOSS_AVERSE
    elif bias_votes["overconfident"] == max_votes:
        bias = BehavioralBiasType.OVERCONFIDENT
    else:
        bias = BehavioralBiasType.BALANCED

    allocation = ALLOCATION_TABLE[-1][1]
    for threshold, alloc in ALLOCATION_TABLE:
        if risk_score < threshold:
            allocation = alloc
            break

    return {
        "risk_score": risk_score,
        "investor_type": investor_type,
        "bias": bias,
        "allocation": allocation,
        "goal": goal,
        "horizon_years": horizon_years,
        "max_loss_pct": max_loss_pct,
    }


# ══════════════════════════════════════════════════════════════════════════════
# SERVICE
# ══════════════════════════════════════════════════════════════════════════════

class RiskProfilerService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def compute_risk_profile(self, user: User, answers: dict[str, Any]) -> RiskProfile:
        result = compute_score_and_bias(answers)

        db_result = await self.db.execute(
            select(RiskProfile).where(RiskProfile.user_id == user.id)
        )
        profile = db_result.scalar_one_or_none()

        profile_data = dict(
            risk_score=result["risk_score"],
            investor_type=result["investor_type"],
            behavioral_bias=result["bias"],
            questionnaire_responses=answers,
            investment_goal=result["goal"],
            time_horizon_years=result["horizon_years"],
            max_acceptable_loss_pct=result["max_loss_pct"],
            last_computed=datetime.utcnow(),
            next_refresh_due=datetime.utcnow() + timedelta(days=90),
        )

        if profile:
            for k, v in profile_data.items():
                setattr(profile, k, v)
        else:
            profile = RiskProfile(user_id=user.id, **profile_data)
            self.db.add(profile)

        await self.db.flush()
        await self.db.refresh(profile)
        return profile

    async def get_profile(self, user_id: int) -> RiskProfile | None:
        result = await self.db.execute(
            select(RiskProfile).where(RiskProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_allocation(self, user_id: int) -> dict[str, int] | None:
        profile = await self.get_profile(user_id)
        if not profile:
            return None
        for threshold, alloc in ALLOCATION_TABLE:
            if profile.risk_score < threshold:
                return alloc
        return ALLOCATION_TABLE[-1][1]

    async def refresh_profile(self, user: User) -> RiskProfile:
        profile = await self.get_profile(user.id)
        if not profile:
            raise ValueError("No risk profile found. Complete the questionnaire first.")

        cutoff = datetime.utcnow() - timedelta(days=90)
        result = await self.db.execute(
            select(BehavioralSignal).where(
                BehavioralSignal.user_id == user.id,
                BehavioralSignal.timestamp >= cutoff,
            )
        )
        signals = result.scalars().all()

        adjustment = 0.0
        for signal in signals:
            if signal.signal_type == "panic_sell":
                adjustment -= 5.0
            elif signal.signal_type == "frequent_check":
                adjustment -= 2.0
            elif signal.signal_type == "held_during_dip":
                adjustment += 3.0
            elif signal.signal_type == "increased_position_dip":
                adjustment += 5.0

        adjustment = max(-20.0, min(20.0, adjustment))
        profile.behavioral_adjustment = adjustment
        new_score = max(0.0, min(100.0, profile.risk_score + adjustment))
        profile.risk_score = new_score
        profile.last_computed = datetime.utcnow()
        profile.next_refresh_due = datetime.utcnow() + timedelta(days=90)

        if new_score < 35:
            profile.investor_type = InvestorType.BEGINNER
        elif new_score < 65:
            profile.investor_type = InvestorType.INTERMEDIATE
        else:
            profile.investor_type = InvestorType.EXPERIENCED

        await self.db.flush()
        return profile
