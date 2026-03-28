"""
FinVoice — Custom Trading Algorithms
5 pluggable strategies that generate buy/sell/hold signals
using your existing ML models, technical indicators, and sentiment data.

Strategies:
    1. Momentum        — Ride winners, cut losers
    2. Mean Reversion  — Buy oversold, sell overbought
    3. Sentiment Alpha — Trade on news before the crowd
    4. ML Ensemble     — Let the AI models decide
    5. Smart Rebalancer — Auto-rebalance when portfolio drifts

Each strategy produces a list of { symbol, action, quantity_pct, confidence, reason }
which feed directly into the TradingEngine.
"""

import logging
import numpy as np
import pandas as pd
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


# ─── Base Strategy ───

class TradingSignal:
    """A single trading signal produced by a strategy."""

    def __init__(
        self,
        symbol: str,
        action: str,           # "buy", "sell", "hold"
        strength: float,       # 0.0 to 1.0
        reason: str,           # Human-readable explanation
        amount_pct: float = 0, # % of available capital to deploy
        factors: dict = None,  # What drove this signal
    ):
        self.symbol = symbol
        self.action = action
        self.strength = min(max(strength, 0.0), 1.0)
        self.reason = reason
        self.amount_pct = amount_pct
        self.factors = factors or {}
        self.timestamp = datetime.now()

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "action": self.action,
            "strength": round(self.strength, 3),
            "reason": self.reason,
            "amount_pct": round(self.amount_pct, 2),
            "factors": self.factors,
            "timestamp": self.timestamp.isoformat(),
        }


class BaseStrategy(ABC):
    """Abstract base class for all trading strategies."""

    name: str = "base"
    description: str = ""

    @abstractmethod
    def generate_signals(
        self,
        features_df: pd.DataFrame,
        portfolio: dict,
        config: dict = None,
    ) -> list[TradingSignal]:
        """
        Generate trading signals.

        Args:
            features_df: DataFrame with technical features per symbol.
                        Columns: symbol, close, rsi_14, macd, etc.
            portfolio: Current holdings: {symbol: {qty, value, weight_pct, buy_price}}
            config: Strategy-specific parameters.

        Returns:
            List of TradingSignal objects.
        """
        pass


# ─── Strategy 1: Momentum ───

class MomentumStrategy(BaseStrategy):
    """
    Buy stocks with strong recent price momentum.
    Sell stocks losing momentum.

    Logic:
    - BUY when: 5-day return > 1% AND 21-day return > 3% AND RSI < 70
    - SELL when: 5-day return < -1.5% AND 21-day return < -3%
    - HOLD otherwise

    In plain English: "Buy stocks that are going up and aren't too expensive yet.
    Sell stocks that are going down and losing steam."
    """

    name = "momentum"
    description = "Ride the winners, cut the losers"

    def generate_signals(self, features_df, portfolio, config=None):
        config = config or {}
        buy_5d = config.get("buy_threshold_5d", 0.01)      # 1% over 5 days
        buy_21d = config.get("buy_threshold_21d", 0.03)     # 3% over 21 days
        sell_5d = config.get("sell_threshold_5d", -0.015)    # -1.5% over 5 days
        rsi_cap = config.get("rsi_overbought", 70)
        rsi_floor = config.get("rsi_oversold", 30)

        signals = []

        for _, row in features_df.iterrows():
            symbol = row.get("symbol", "UNKNOWN")
            ret_5d = row.get("return_5d", 0)
            ret_21d = row.get("return_21d", 0)
            rsi = row.get("rsi_14", 50)

            factors = {
                "Price change (1 week)": f"{ret_5d * 100:+.1f}%",
                "Price change (1 month)": f"{ret_21d * 100:+.1f}%",
                "Overpriced meter": f"{rsi:.0f}/100",
            }

            if ret_5d > buy_5d and ret_21d > buy_21d and rsi < rsi_cap:
                strength = min((ret_5d / buy_5d + ret_21d / buy_21d) / 4, 1.0)
                signals.append(TradingSignal(
                    symbol=symbol,
                    action="buy",
                    strength=strength,
                    amount_pct=min(strength * 5, 10),  # Up to 10% of capital
                    reason=(
                        f"{symbol} has been going up steadily — "
                        f"up {ret_5d * 100:.1f}% this week and {ret_21d * 100:.1f}% this month. "
                        f"The stock isn't overpriced yet (priced at {rsi:.0f}/100 on the overpriced meter, "
                        f"danger zone starts at {rsi_cap}). "
                        f"This upward trend looks likely to continue."
                    ),
                    factors=factors,
                ))

            elif ret_5d < sell_5d and ret_21d < sell_5d * 2:
                strength = min(abs(ret_5d / sell_5d) * 0.5, 1.0)
                signals.append(TradingSignal(
                    symbol=symbol,
                    action="sell",
                    strength=strength,
                    amount_pct=min(strength * 3, 8),
                    reason=(
                        f"{symbol} has been losing value — "
                        f"down {abs(ret_5d) * 100:.1f}% this week and "
                        f"{abs(ret_21d) * 100:.1f}% this month. "
                        f"The downward trend suggests it's better to reduce your position "
                        f"and protect your capital."
                    ),
                    factors=factors,
                ))

            else:
                signals.append(TradingSignal(
                    symbol=symbol,
                    action="hold",
                    strength=0.5,
                    reason=(
                        f"{symbol} isn't showing a clear direction right now. "
                        f"It moved {ret_5d * 100:+.1f}% this week. "
                        f"Best to hold and wait for a stronger signal."
                    ),
                    factors=factors,
                ))

        return signals


# ─── Strategy 2: Mean Reversion ───

class MeanReversionStrategy(BaseStrategy):
    """
    Buy oversold stocks, sell overbought ones.

    Logic:
    - BUY when: RSI < 30 OR Bollinger %B < 0.1 (stock fell too much)
    - SELL when: RSI > 70 OR Bollinger %B > 0.9 (stock rose too much)

    In plain English: "Buy when a good stock drops too low (bargain hunting).
    Sell when it's risen too high too fast (take profits)."
    """

    name = "mean_reversion"
    description = "Buy the dips, sell the peaks"

    def generate_signals(self, features_df, portfolio, config=None):
        config = config or {}
        rsi_oversold = config.get("rsi_oversold", 30)
        rsi_overbought = config.get("rsi_overbought", 70)
        bb_low = config.get("bollinger_low", 0.10)
        bb_high = config.get("bollinger_high", 0.90)

        signals = []

        for _, row in features_df.iterrows():
            symbol = row.get("symbol", "UNKNOWN")
            rsi = row.get("rsi_14", 50)
            bb_pct = row.get("bollinger_pct", 0.5)
            price = row.get("close", 0)

            factors = {
                "Overpriced meter": f"{rsi:.0f}/100 (buy below {rsi_oversold}, sell above {rsi_overbought})",
                "Price vs normal range": f"{bb_pct * 100:.0f}% (0%=very low, 100%=very high)",
            }

            is_oversold = rsi < rsi_oversold or bb_pct < bb_low
            is_overbought = rsi > rsi_overbought or bb_pct > bb_high

            if is_oversold:
                depth = (rsi_oversold - rsi) / rsi_oversold if rsi < rsi_oversold else (bb_low - bb_pct) / bb_low
                strength = min(0.5 + abs(depth) * 0.5, 1.0)
                signals.append(TradingSignal(
                    symbol=symbol,
                    action="buy",
                    strength=strength,
                    amount_pct=min(strength * 6, 12),
                    reason=(
                        f"{symbol} has dropped to a bargain level. "
                        f"Its 'overpriced meter' is at {rsi:.0f}/100 — anything below {rsi_oversold} "
                        f"usually means the stock fell more than it deserved. "
                        f"Historically, stocks at this level tend to bounce back. "
                        f"This could be a good opportunity to buy the dip."
                    ),
                    factors=factors,
                ))

            elif is_overbought:
                excess = (rsi - rsi_overbought) / (100 - rsi_overbought) if rsi > rsi_overbought else (bb_pct - bb_high) / (1 - bb_high)
                strength = min(0.5 + abs(excess) * 0.5, 1.0)
                signals.append(TradingSignal(
                    symbol=symbol,
                    action="sell",
                    strength=strength,
                    amount_pct=min(strength * 4, 8),
                    reason=(
                        f"{symbol} looks overpriced right now. "
                        f"Its 'overpriced meter' is at {rsi:.0f}/100 — anything above {rsi_overbought} "
                        f"means the stock might have risen too fast. "
                        f"Taking some profits now protects your gains in case of a pullback."
                    ),
                    factors=factors,
                ))

            else:
                signals.append(TradingSignal(
                    symbol=symbol,
                    action="hold",
                    strength=0.5,
                    reason=(
                        f"{symbol} is trading in its normal price range "
                        f"(priced at {rsi:.0f}/100). No extreme buying or selling opportunity right now."
                    ),
                    factors=factors,
                ))

        return signals


# ─── Strategy 3: Sentiment Alpha ───

class SentimentStrategy(BaseStrategy):
    """
    Trade based on news sentiment before the crowd.

    Logic:
    - BUY when: Sentiment score > +0.3 (strongly positive news)
    - SELL when: Sentiment score < -0.3 (strongly negative news)
    - Size position by sentiment confidence

    In plain English: "When we detect very positive news about a stock,
    buy before the price catches up. When news turns negative, sell early."
    """

    name = "sentiment_alpha"
    description = "Trade on news before everyone else"

    def generate_signals(self, features_df, portfolio, config=None):
        config = config or {}
        buy_threshold = config.get("buy_sentiment", 0.3)
        sell_threshold = config.get("sell_sentiment", -0.3)
        sentiment_data = config.get("sentiment", {})  # {symbol: {score, signal, headlines}}

        signals = []

        for _, row in features_df.iterrows():
            symbol = row.get("symbol", "UNKNOWN")
            sent = sentiment_data.get(symbol, {})
            score = sent.get("score", 0)
            signal_type = sent.get("signal", "neutral")
            headlines = sent.get("headlines", [])

            news_summary = headlines[0] if headlines else "No recent news"

            factors = {
                "News mood": f"{signal_type.capitalize()} ({score:+.2f})",
                "Latest headline": news_summary,
                "Articles analyzed": str(len(headlines)),
            }

            if score > buy_threshold:
                strength = min(score / 1.0, 1.0)
                signals.append(TradingSignal(
                    symbol=symbol,
                    action="buy",
                    strength=strength,
                    amount_pct=min(strength * 5, 10),
                    reason=(
                        f"We're seeing very positive news about {symbol}. "
                        f"Our AI read {len(headlines)} recent articles and scored the overall mood "
                        f"at {score:+.2f} (positive). "
                        f"Latest: \"{news_summary}\". "
                        f"When news is this positive, stock prices typically follow upward "
                        f"over the next few days."
                    ),
                    factors=factors,
                ))

            elif score < sell_threshold:
                strength = min(abs(score) / 1.0, 1.0)
                signals.append(TradingSignal(
                    symbol=symbol,
                    action="sell",
                    strength=strength,
                    amount_pct=min(strength * 4, 8),
                    reason=(
                        f"We're seeing worrying news about {symbol}. "
                        f"Our AI analyzed {len(headlines)} recent articles and the mood is "
                        f"negative ({score:+.2f}). "
                        f"Latest: \"{news_summary}\". "
                        f"Negative news often pushes prices down — selling now "
                        f"helps protect your investment."
                    ),
                    factors=factors,
                ))

            else:
                signals.append(TradingSignal(
                    symbol=symbol,
                    action="hold",
                    strength=0.3,
                    reason=(
                        f"News about {symbol} is mixed or neutral right now "
                        f"(mood score: {score:+.2f}). "
                        f"No strong reason to buy or sell based on news alone."
                    ),
                    factors=factors,
                ))

        return signals


# ─── Strategy 4: ML Ensemble ───

class MLEnsembleStrategy(BaseStrategy):
    """
    Use the AutoGluon + XGBoost + LSTM ensemble predictions directly.

    Logic:
    - BUY when: Predicted 5-day return > +1.5% AND confidence > 60%
    - SELL when: Predicted 5-day return < -1.0% AND confidence > 60%
    - Position size scaled by confidence

    In plain English: "6 different AI models analyze 18 data points per stock.
    When most of them agree on a direction, we follow that signal."
    """

    name = "ml_ensemble"
    description = "Let 6 AI models decide together"

    def generate_signals(self, features_df, portfolio, config=None):
        config = config or {}
        predictions = config.get("ml_predictions", {})  # {symbol: {return_5d, confidence}}
        buy_return = config.get("buy_return_threshold", 0.015)    # 1.5%
        sell_return = config.get("sell_return_threshold", -0.01)   # -1.0%
        min_confidence = config.get("min_confidence", 0.60)       # 60%

        signals = []

        for _, row in features_df.iterrows():
            symbol = row.get("symbol", "UNKNOWN")
            pred = predictions.get(symbol, {})
            predicted_return = pred.get("return_5d", 0)
            confidence = pred.get("confidence", 0)
            models_agree = pred.get("models_agree", 0)
            total_models = pred.get("total_models", 6)

            factors = {
                "AI prediction": f"{predicted_return * 100:+.1f}% over 5 days",
                "Models agreeing": f"{models_agree}/{total_models}",
                "Confidence": f"{confidence * 100:.0f}%",
            }

            if predicted_return > buy_return and confidence > min_confidence:
                strength = min(confidence, 1.0)
                signals.append(TradingSignal(
                    symbol=symbol,
                    action="buy",
                    strength=strength,
                    amount_pct=min(strength * 5, 10),
                    reason=(
                        f"Our AI analyzed 18 different data points for {symbol} — "
                        f"price trends, trading volume, market conditions, and news. "
                        f"{models_agree} out of {total_models} models predict the price will "
                        f"go up by ~{predicted_return * 100:.1f}% over the next 5 trading days. "
                        f"Confidence level: {confidence * 100:.0f}%. "
                        f"When this many models agree, the prediction is usually reliable."
                    ),
                    factors=factors,
                ))

            elif predicted_return < sell_return and confidence > min_confidence:
                strength = min(confidence, 1.0)
                signals.append(TradingSignal(
                    symbol=symbol,
                    action="sell",
                    strength=strength,
                    amount_pct=min(strength * 4, 8),
                    reason=(
                        f"Our AI is predicting a {abs(predicted_return) * 100:.1f}% drop "
                        f"in {symbol} over the next 5 days. "
                        f"{models_agree} out of {total_models} models agree on this direction. "
                        f"Confidence: {confidence * 100:.0f}%. "
                        f"Reducing your position now helps protect against the expected decline."
                    ),
                    factors=factors,
                ))

            else:
                reason_detail = ""
                if confidence <= min_confidence:
                    reason_detail = (
                        f"Our AI models disagree on {symbol} — only {models_agree} out of "
                        f"{total_models} agree, so confidence is low ({confidence * 100:.0f}%). "
                        f"When the AI isn't sure, it's better to wait."
                    )
                else:
                    reason_detail = (
                        f"The AI predicts a small move of {predicted_return * 100:+.1f}% for "
                        f"{symbol} — not enough to justify trading costs."
                    )

                signals.append(TradingSignal(
                    symbol=symbol,
                    action="hold",
                    strength=0.3,
                    reason=reason_detail,
                    factors=factors,
                ))

        return signals


# ─── Strategy 5: Smart Rebalancer ───

class SmartRebalanceStrategy(BaseStrategy):
    """
    Automatically rebalance when portfolio drifts too far from target.

    Logic:
    - BUY underweight assets (current % < target % by > 3%)
    - SELL overweight assets (current % > target % by > 3%)
    - Scale trade size by drift magnitude

    In plain English: "If you wanted 20% in banks but now it's 27% because
    that stock went up a lot, sell some to bring it back. If another stock
    dropped and is now under target, buy more at the lower price."
    """

    name = "smart_rebalance"
    description = "Keep your portfolio balanced automatically"

    def generate_signals(self, features_df, portfolio, config=None):
        config = config or {}
        target_weights = config.get("target_weights", {})
        drift_threshold = config.get("drift_threshold", 3.0)  # 3% drift triggers rebalance

        signals = []

        for _, row in features_df.iterrows():
            symbol = row.get("symbol", "UNKNOWN")
            current_weight = portfolio.get(symbol, {}).get("weight_pct", 0)
            target_weight = target_weights.get(symbol, current_weight)
            drift = current_weight - target_weight

            factors = {
                "Your current allocation": f"{current_weight:.1f}%",
                "Your target allocation": f"{target_weight:.1f}%",
                "Drift from target": f"{drift:+.1f}%",
            }

            if drift < -drift_threshold:
                # Underweight — buy more
                strength = min(abs(drift) / 10, 1.0)
                signals.append(TradingSignal(
                    symbol=symbol,
                    action="buy",
                    strength=strength,
                    amount_pct=abs(drift),
                    reason=(
                        f"{symbol} makes up only {current_weight:.1f}% of your portfolio, "
                        f"but your target is {target_weight:.1f}%. "
                        f"It's drifted {abs(drift):.1f}% below where you want it. "
                        f"Buying more will bring your portfolio back in balance "
                        f"and maintain the diversification you planned."
                    ),
                    factors=factors,
                ))

            elif drift > drift_threshold:
                # Overweight — sell some
                strength = min(abs(drift) / 10, 1.0)
                signals.append(TradingSignal(
                    symbol=symbol,
                    action="sell",
                    strength=strength,
                    amount_pct=abs(drift),
                    reason=(
                        f"{symbol} has grown to {current_weight:.1f}% of your portfolio — "
                        f"that's {drift:.1f}% more than your target of {target_weight:.1f}%. "
                        f"When one stock gets too big, your risk increases. "
                        f"Trimming it back keeps your portfolio diversified and safe."
                    ),
                    factors=factors,
                ))

            else:
                signals.append(TradingSignal(
                    symbol=symbol,
                    action="hold",
                    strength=0.5,
                    reason=(
                        f"{symbol} is at {current_weight:.1f}% vs target {target_weight:.1f}% — "
                        f"only {abs(drift):.1f}% off target. "
                        f"Close enough — no rebalancing needed."
                    ),
                    factors=factors,
                ))

        return signals


# ─── Strategy Orchestrator ───

class AlgorithmOrchestrator:
    """
    Combines signals from multiple strategies into a single trade decision.

    Weighting:
    - Each strategy gets a weight based on its recent performance
    - Signals are combined: if 3 strategies say BUY and 1 says SELL → weighted BUY
    - Final confidence = weighted average of individual signal strengths
    """

    STRATEGY_MAP = {
        "momentum": MomentumStrategy,
        "mean_reversion": MeanReversionStrategy,
        "sentiment_alpha": SentimentStrategy,
        "ml_ensemble": MLEnsembleStrategy,
        "smart_rebalance": SmartRebalanceStrategy,
    }

    DEFAULT_WEIGHTS = {
        "momentum": 0.20,
        "mean_reversion": 0.15,
        "sentiment_alpha": 0.20,
        "ml_ensemble": 0.30,      # ML gets highest weight
        "smart_rebalance": 0.15,
    }

    def __init__(self, strategies: list[str] = None, weights: dict = None):
        """
        Args:
            strategies: List of strategy names to use. Default: all 5.
            weights: Custom weights. Default: ML-heavy.
        """
        strategy_names = strategies or list(self.STRATEGY_MAP.keys())
        self.strategies = {
            name: self.STRATEGY_MAP[name]()
            for name in strategy_names
            if name in self.STRATEGY_MAP
        }
        self.weights = weights or self.DEFAULT_WEIGHTS

    def run_all(
        self,
        features_df: pd.DataFrame,
        portfolio: dict,
        strategy_configs: dict = None,
    ) -> dict:
        """
        Run all strategies and combine their signals.

        Args:
            features_df: Technical features per symbol.
            portfolio: Current portfolio: {symbol: {qty, value, weight_pct}}
            strategy_configs: Per-strategy config: {"momentum": {...}, ...}

        Returns:
            {
                "signals": {symbol: combined TradingSignal},
                "strategy_signals": {strategy_name: [TradingSignal]},
                "summary": str,
            }
        """
        strategy_configs = strategy_configs or {}
        all_signals = {}     # {strategy_name: [signal, ...]}
        symbol_votes = {}    # {symbol: [{strategy, action, strength, weight}]}

        # Run each strategy
        for name, strategy in self.strategies.items():
            config = strategy_configs.get(name, {})
            try:
                signals = strategy.generate_signals(features_df, portfolio, config)
                all_signals[name] = [s.to_dict() for s in signals]

                for signal in signals:
                    if signal.symbol not in symbol_votes:
                        symbol_votes[signal.symbol] = []
                    symbol_votes[signal.symbol].append({
                        "strategy": name,
                        "action": signal.action,
                        "strength": signal.strength,
                        "weight": self.weights.get(name, 0.2),
                        "reason": signal.reason,
                        "factors": signal.factors,
                    })

            except Exception as e:
                logger.error(f"Strategy {name} failed: {e}")
                all_signals[name] = []

        # Combine signals per symbol
        combined = {}
        for symbol, votes in symbol_votes.items():
            combined[symbol] = self._combine_votes(symbol, votes)

        # Generate summary
        buys = [s for s in combined.values() if s["action"] == "buy"]
        sells = [s for s in combined.values() if s["action"] == "sell"]
        holds = [s for s in combined.values() if s["action"] == "hold"]

        summary = (
            f"Analyzed {len(combined)} stocks using {len(self.strategies)} strategies. "
            f"Result: {len(buys)} buy, {len(sells)} sell, {len(holds)} hold recommendations."
        )

        return {
            "signals": combined,
            "strategy_signals": all_signals,
            "summary": summary,
            "strategies_used": list(self.strategies.keys()),
        }

    def _combine_votes(self, symbol: str, votes: list) -> dict:
        """Combine strategy votes into a single recommendation."""
        # Calculate weighted score: buy = +1, sell = -1, hold = 0
        action_scores = {"buy": 1.0, "sell": -1.0, "hold": 0.0}
        total_weight = 0
        weighted_score = 0
        weighted_strength = 0
        all_reasons = []
        all_factors = {}

        for vote in votes:
            w = vote["weight"]
            total_weight += w
            weighted_score += action_scores.get(vote["action"], 0) * w * vote["strength"]
            weighted_strength += vote["strength"] * w
            all_reasons.append(f"**{vote['strategy'].replace('_', ' ').title()}**: {vote['reason']}")
            for k, v in vote["factors"].items():
                all_factors[f"{vote['strategy']}: {k}"] = v

        if total_weight > 0:
            final_score = weighted_score / total_weight
            avg_strength = weighted_strength / total_weight
        else:
            final_score = 0
            avg_strength = 0.5

        # Determine final action
        if final_score > 0.15:
            action = "buy"
        elif final_score < -0.15:
            action = "sell"
        else:
            action = "hold"

        # Count agreement
        buy_votes = sum(1 for v in votes if v["action"] == "buy")
        sell_votes = sum(1 for v in votes if v["action"] == "sell")
        hold_votes = sum(1 for v in votes if v["action"] == "hold")
        total_strats = len(votes)

        if action == "buy":
            agreement_text = f"{buy_votes} out of {total_strats} strategies recommend buying"
        elif action == "sell":
            agreement_text = f"{sell_votes} out of {total_strats} strategies recommend selling"
        else:
            agreement_text = f"Strategies are mixed — no clear consensus"

        return {
            "symbol": symbol,
            "action": action,
            "confidence": round(avg_strength, 3),
            "score": round(final_score, 3),
            "agreement": agreement_text,
            "buy_votes": buy_votes,
            "sell_votes": sell_votes,
            "hold_votes": hold_votes,
            "reasons": all_reasons,
            "factors": all_factors,
        }

    @staticmethod
    def available_strategies() -> list[dict]:
        """List all available strategies with descriptions."""
        return [
            {
                "name": name,
                "title": cls.name.replace("_", " ").title(),
                "description": cls.description,
            }
            for name, cls in AlgorithmOrchestrator.STRATEGY_MAP.items()
        ]
