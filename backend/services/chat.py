"""
FinVoice — AI Chat Service.
Streams GPT responses with full user financial context.
"""

import logging
from typing import AsyncGenerator

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from config import get_settings
from models import (
    User, RiskProfile, Portfolio, Holding, Asset,
    TargetAllocation, DriftAlert,
)

logger = logging.getLogger(__name__)
settings = get_settings()

# ─── OpenAI Client (lazy singleton) ───

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


MODEL = "gpt-4o"  # Will upgrade to gpt-5 when available on account


# ─── Context Gathering ───


async def _gather_user_context(db: AsyncSession, user: User) -> dict:
    """
    Pull everything we know about this user from the DB
    and return it as a structured dict for the system prompt.
    """
    ctx: dict = {
        "full_name": user.full_name or "User",
        "email": user.email,
        "tier": user.tier.value if user.tier else "free",
    }

    # ── Risk Profile ──
    result = await db.execute(
        select(RiskProfile).where(RiskProfile.user_id == user.id)
    )
    risk = result.scalar_one_or_none()
    if risk:
        ctx["risk_score"] = risk.risk_score
        ctx["investor_type"] = risk.investor_type.value if risk.investor_type else "unknown"
        ctx["behavioral_bias"] = risk.behavioral_bias.value if risk.behavioral_bias else "balanced"
        ctx["investment_goal"] = risk.investment_goal or "Not specified"
        ctx["time_horizon_years"] = risk.time_horizon_years
        ctx["income_range"] = risk.income_range or "Not specified"
        ctx["max_acceptable_loss_pct"] = risk.max_acceptable_loss_pct
        ctx["age"] = risk.age
        ctx["tax_bracket"] = risk.tax_bracket or "Not specified"
    else:
        ctx["risk_score"] = None
        ctx["investor_type"] = "unknown"

    # ── Portfolio & Holdings ──
    result = await db.execute(
        select(Portfolio)
        .where(Portfolio.user_id == user.id)
        .options(
            selectinload(Portfolio.holdings).selectinload(Holding.asset),
            selectinload(Portfolio.target_allocations),
            selectinload(Portfolio.drift_alerts),
        )
        .order_by(Portfolio.created_at.desc())
    )
    portfolio = result.scalars().first()

    if portfolio:
        ctx["portfolio_name"] = portfolio.name
        ctx["total_invested"] = portfolio.total_invested or 0
        ctx["current_value"] = portfolio.current_value or portfolio.total_invested or 0

        pnl = (ctx["current_value"] - ctx["total_invested"])
        pnl_pct = (pnl / ctx["total_invested"] * 100) if ctx["total_invested"] > 0 else 0
        ctx["pnl"] = round(pnl, 2)
        ctx["pnl_pct"] = round(pnl_pct, 2)

        # Holdings
        holdings_lines = []
        for h in portfolio.holdings:
            symbol = h.asset.symbol if h.asset else "UNKNOWN"
            name = h.asset.name if h.asset else symbol
            asset_class = h.asset.asset_class.value if h.asset and hasattr(h.asset.asset_class, 'value') else str(h.asset.asset_class) if h.asset else "equity"
            sector = h.asset.sector if h.asset else "N/A"
            value = h.quantity * (h.current_price or h.buy_price)
            holdings_lines.append(
                f"  - {symbol} ({name}): {h.quantity} units @ ₹{h.buy_price:.2f} "
                f"(current: ₹{h.current_price or h.buy_price:.2f}, "
                f"value: ₹{value:,.2f}, class: {asset_class}, sector: {sector or 'N/A'})"
            )
        ctx["holdings_text"] = "\n".join(holdings_lines) if holdings_lines else "  No holdings imported yet."

        # Target Allocation
        alloc_lines = []
        for ta in portfolio.target_allocations:
            alloc_lines.append(f"  - {ta.asset_class}: {ta.target_pct}%")
        ctx["allocation_text"] = "\n".join(alloc_lines) if alloc_lines else "  No target allocation set."

        # Drift Alerts
        drift_lines = []
        for da in portfolio.drift_alerts:
            drift_lines.append(
                f"  - {da.asset_class}: actual {da.actual_pct:.1f}% vs target {da.target_pct:.1f}% "
                f"(drift: {da.drift_pct:+.1f}%, severity: {da.severity.value})"
            )
        ctx["drift_text"] = "\n".join(drift_lines) if drift_lines else "  No drift alerts."
    else:
        ctx["portfolio_name"] = None
        ctx["total_invested"] = 0
        ctx["holdings_text"] = "  No portfolio imported yet."
        ctx["allocation_text"] = "  No target allocation set."
        ctx["drift_text"] = "  No drift alerts."

    return ctx


# ─── System Prompt Builder ───


def _build_system_prompt(ctx: dict) -> str:
    """Build a detailed system prompt with user financial context."""

    risk_section = ""
    if ctx.get("risk_score") is not None:
        risk_section = f"""
## User Risk Profile
- Risk Score: {ctx['risk_score']}/100
- Investor Type: {ctx['investor_type']}
- Behavioral Bias: {ctx['behavioral_bias']}
- Investment Goal: {ctx['investment_goal']}
- Time Horizon: {ctx.get('time_horizon_years', 'N/A')} years
- Age: {ctx.get('age', 'N/A')}
- Income Range: {ctx['income_range']}
- Tax Bracket: {ctx.get('tax_bracket', 'N/A')}
- Max Acceptable Loss: {ctx.get('max_acceptable_loss_pct', 'N/A')}%
"""
    else:
        risk_section = """
## User Risk Profile
- Risk assessment not yet completed.
"""

    portfolio_section = ""
    if ctx.get("portfolio_name"):
        portfolio_section = f"""
## Current Portfolio — "{ctx['portfolio_name']}"
- Total Invested: ₹{ctx['total_invested']:,.2f}
- Current Value: ₹{ctx['current_value']:,.2f}
- P&L: ₹{ctx['pnl']:,.2f} ({ctx['pnl_pct']:+.2f}%)

### Holdings
{ctx['holdings_text']}

### Target Allocation
{ctx['allocation_text']}

### Active Drift Alerts
{ctx['drift_text']}
"""
    else:
        portfolio_section = """
## Current Portfolio
- No portfolio has been imported yet. Encourage the user to import their portfolio.
"""

    return f"""You are FinVoice AI — a knowledgeable, friendly, and trustworthy financial advisor built specifically for Indian investors. You are embedded inside the FinVoice app.

## Your Capabilities
- Portfolio analysis, rebalancing advice, and drift correction
- Investment strategy for Indian markets: NSE/BSE equities, mutual funds (SIPs), gold (sovereign gold bonds, ETFs), fixed deposits, REITs, bonds
- Risk assessment, management, and behavioral coaching
- Tax-efficient investing: Section 80C, 80D, ELSS, LTCG, STCG, indexation
- SIP planning, goal-based investing, emergency fund guidance
- Market education — explain concepts clearly and simply
- Crash/stress test scenario discussion
- Comparing asset classes and helping with asset allocation

## User Profile
- Name: {ctx['full_name']}
- Account Tier: {ctx['tier']}
{risk_section}
{portfolio_section}

## Communication Guidelines
1. **Adapt to investor type**: If the user is a beginner, avoid jargon and use simple analogies. If experienced, include technical analysis, ratios, and data.
2. **Use Indian context**: Always use ₹ for currency. Use lakhs and crores for large numbers (e.g., ₹1,50,000 or ₹2.5 crore). Reference Indian instruments (Nifty 50, Sensex, ELSS, PPF, NPS, SGBs, etc.).
3. **Be balanced**: Always mention risks alongside opportunities. Never guarantee returns.
4. **Be concise**: Give clear, actionable answers. Use bullet points and structure.
5. **Use hedging language**: Say "historically", "tends to", "based on current data", "potential".
6. **Portfolio-aware**: When the user asks about their portfolio, reference their ACTUAL holdings and data shown above. Don't make up holdings they don't have.
7. **Proactive**: If you notice issues in their portfolio (concentration risk, missing asset classes, drift), mention them naturally.

## Formatting
- Use markdown formatting for readability (bold, bullet points, headers).
- Use tables when comparing options.
- Keep responses focused — aim for 100-300 words unless the user asks for detail.

## Restrictions
- Never provide SEBI-registered investment advice. You are a decision-support tool.
- Never share made-up stock prices, NAVs, or returns. If you don't have data, say so.
- Never execute trades or promise to execute trades.
- End with the disclaimer when giving specific investment recommendations: "📋 *FinVoice is a decision-support tool. Consult a SEBI-registered advisor for personalized advice.*"
"""


# ─── Streaming Chat ───


async def stream_chat_response(
    db: AsyncSession,
    user: User,
    message: str,
    history: list[dict],
) -> AsyncGenerator[str, None]:
    """
    Stream chat tokens from GPT with full user context.

    Args:
        db: Database session
        user: Authenticated user
        message: Current user message
        history: Previous messages [{role: "user"|"assistant", content: str}]

    Yields:
        Token strings as they arrive
    """
    # 1. Gather context
    ctx = await _gather_user_context(db, user)

    # 2. Build messages array
    system_prompt = _build_system_prompt(ctx)
    messages = [{"role": "system", "content": system_prompt}]

    # Add conversation history (cap at last 20 messages to stay within context)
    for msg in history[-20:]:
        role = msg.get("role", "user")
        if role not in ("user", "assistant"):
            role = "user"
        messages.append({"role": role, "content": msg.get("content", "")})

    # Add current message
    messages.append({"role": "user", "content": message})

    # 3. Stream from OpenAI
    client = _get_client()

    try:
        stream = await client.chat.completions.create(
            model=MODEL,
            messages=messages,
            stream=True,
            temperature=0.7,
            max_tokens=1024,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content

    except Exception as e:
        logger.error(f"OpenAI streaming error: {e}")
        yield f"\n\n⚠️ Sorry, I encountered an error. Please try again. ({type(e).__name__})"
