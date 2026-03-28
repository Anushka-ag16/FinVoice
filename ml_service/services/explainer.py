"""
Model Explainability Service — SHAP, LIME, and Claude API explanations.

Provides:
  - SHAP TreeExplainer for XGBoost (fast, exact tree-based explanations)
  - LIME LimeTabularExplainer for LSTM/TFT (model-agnostic perturbation)
  - Claude API integration for plain-English narrative generation

The Claude prompt produces a 2-3 sentence explanation suitable for a retail
investor who does not understand ML.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Callable

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# SHAP — XGBoost Explanations
# ══════════════════════════════════════════════════════════════════════════════
def build_shap_explainer(xgb_model: Any) -> Any:
    """Build a SHAP TreeExplainer for an XGBoost model.

    TreeExplainer uses the exact Shapley-value computation path for tree
    ensembles, making it much faster than the model-agnostic KernelExplainer.

    Args:
        xgb_model: Trained XGBoost model (``XGBRegressor`` or ``XGBClassifier``).

    Returns:
        ``shap.TreeExplainer`` instance.
    """
    import shap

    explainer = shap.TreeExplainer(xgb_model)
    logger.info("SHAP TreeExplainer built for %s", type(xgb_model).__name__)
    return explainer


def explain_xgb(
    explainer: Any,
    X_row: np.ndarray,
    feature_names: list[str],
) -> dict[str, float]:
    """Explain a single prediction using SHAP values.

    Args:
        explainer: ``shap.TreeExplainer`` instance.
        X_row: Single input row ``(1, n_features)`` or ``(n_features,)``.
        feature_names: Ordered list of feature names.

    Returns:
        Dictionary mapping feature name to its SHAP contribution.
    """
    if X_row.ndim == 1:
        X_row = X_row.reshape(1, -1)

    shap_values = explainer.shap_values(X_row)

    # shap_values may be a list (multiclass) or array
    if isinstance(shap_values, list):
        sv = shap_values[0]
    else:
        sv = shap_values

    sv_flat = sv.flatten()
    assert len(sv_flat) == len(feature_names), (
        f"SHAP values length {len(sv_flat)} != feature_names length {len(feature_names)}"
    )

    explanation = {name: float(val) for name, val in zip(feature_names, sv_flat)}
    logger.debug("SHAP explanation: %s", explanation)
    return explanation


# ══════════════════════════════════════════════════════════════════════════════
# LIME — LSTM / TFT Explanations
# ══════════════════════════════════════════════════════════════════════════════
def build_lime_explainer(
    X_train: np.ndarray,
    feature_names: list[str],
) -> Any:
    """Build a LIME tabular explainer.

    LIME (Local Interpretable Model-agnostic Explanations) approximates the
    model locally with a linear model around each prediction point.  It works
    with any model that has a ``predict`` callable.

    Args:
        X_train: Training data used to compute statistics for perturbation.
        feature_names: Ordered list of feature names.

    Returns:
        ``LimeTabularExplainer`` instance.
    """
    from lime.lime_tabular import LimeTabularExplainer

    explainer = LimeTabularExplainer(
        training_data=X_train,
        feature_names=feature_names,
        mode="regression",
        verbose=False,
    )
    logger.info("LIME explainer built with %d features", len(feature_names))
    return explainer


def explain_lstm(
    lime_explainer: Any,
    predict_fn: Callable[[np.ndarray], np.ndarray],
    X_row: np.ndarray,
) -> dict[str, float]:
    """Explain a single LSTM/TFT prediction using LIME.

    Args:
        lime_explainer: ``LimeTabularExplainer`` instance.
        predict_fn: Callable that accepts ``(n_samples, n_features)`` and
            returns predictions ``(n_samples,)``.
        X_row: Single input row ``(n_features,)``.

    Returns:
        Dictionary mapping feature name to LIME contribution weight.
    """
    explanation = lime_explainer.explain_instance(
        X_row.flatten(),
        predict_fn,
        num_features=len(X_row.flatten()),
        num_samples=500,
    )

    result: dict[str, float] = {}
    for feature_name, weight in explanation.as_list():
        # LIME returns feature descriptions like "0.5 < feature_name <= 1.0"
        # We extract just the contribution weight
        result[feature_name] = float(weight)

    logger.debug("LIME explanation: %d features", len(result))
    return result


# ══════════════════════════════════════════════════════════════════════════════
# Top Factor Extraction
# ══════════════════════════════════════════════════════════════════════════════
def top_factors(
    shap_dict: dict[str, float],
    n: int = 5,
) -> list[tuple[str, float]]:
    """Extract the top-N most influential factors by absolute SHAP value.

    Args:
        shap_dict: Feature → SHAP-value dictionary.
        n: Number of top factors to return.

    Returns:
        List of ``(feature_name, shap_value)`` tuples sorted by ``|value|``
        descending.
    """
    sorted_factors = sorted(shap_dict.items(), key=lambda x: abs(x[1]), reverse=True)
    return sorted_factors[:n]


# ══════════════════════════════════════════════════════════════════════════════
# Claude API — Plain-English Explanation
# ══════════════════════════════════════════════════════════════════════════════
def build_claude_prompt(
    ticker: str,
    prediction: float,
    top_factors_list: list[tuple[str, float]],
    regime_label: str,
) -> str:
    """Build a prompt for Claude to generate a retail-investor-friendly explanation.

    Args:
        ticker: Stock ticker symbol.
        prediction: Predicted 5-day forward return (decimal, e.g. 0.02 = 2%).
        top_factors_list: List of ``(factor_name, contribution)`` from SHAP/LIME.
        regime_label: Current market regime label (e.g. ``"bull"``).

    Returns:
        Formatted prompt string.
    """
    direction = "upward" if prediction > 0 else "downward"
    pct = abs(prediction * 100)

    factors_text = "\n".join(
        f"  - {name}: {'positive' if val > 0 else 'negative'} contribution ({val:+.4f})"
        for name, val in top_factors_list
    )

    prompt = f"""You are a financial analyst explaining a stock prediction to a retail investor
who does not understand machine learning or quantitative finance.

Stock: {ticker}
Predicted 5-day return: {prediction:+.2%} ({direction} movement expected)
Current market regime: {regime_label}

Top factors driving this prediction:
{factors_text}

Write a 2-3 sentence plain English explanation of why the model predicts this
{direction} movement for {ticker}. Do NOT mention machine learning, SHAP values,
or technical jargon. Speak as if explaining to a friend who invests casually.
Focus on what matters: the direction, the confidence level, and the key drivers
in everyday language."""

    return prompt


def call_claude_api(prompt: str, api_key: str | None = None) -> str:
    """Call Anthropic's Claude API to generate a plain-English explanation.

    Args:
        prompt: The formatted explanation prompt.
        api_key: Anthropic API key.  If ``None``, reads from
            ``ANTHROPIC_API_KEY`` environment variable.

    Returns:
        Claude's response text.

    Raises:
        ValueError: If no API key is provided or found.
        anthropic.APIError: On API communication failures.
    """
    if api_key is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    if not api_key or api_key == "your_key_here":
        logger.warning("No valid ANTHROPIC_API_KEY found — returning placeholder explanation")
        return (
            "Our analysis suggests this stock may move based on recent market "
            "conditions and company-specific factors. Please consult a financial "
            "advisor for personalised guidance."
        )

    import anthropic

    client = anthropic.Anthropic(api_key=api_key)

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text
    logger.info("Claude API response received (%d chars)", len(response_text))
    return response_text


# ──────────────────────────────────────────────────────────────────────────────
# Smoke Test
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logger.info("=== Explainer Service Smoke Test ===")

    # Test top_factors
    mock_shap = {
        "rsi": 0.05,
        "macd": -0.12,
        "volatility": 0.08,
        "india_vix": -0.03,
        "boll_pct": 0.01,
        "volume": -0.15,
        "close": 0.02,
    }
    top5 = top_factors(mock_shap, n=5)
    logger.info("Top 5 factors: %s", top5)
    assert len(top5) == 5, f"Expected 5 factors, got {len(top5)}"
    assert abs(top5[0][1]) >= abs(top5[1][1]), "Factors not sorted by absolute value"

    # Test prompt building
    prompt = build_claude_prompt(
        ticker="RELIANCE.NS",
        prediction=0.023,
        top_factors_list=top5,
        regime_label="bull",
    )
    logger.info("Prompt length: %d chars", len(prompt))
    assert "RELIANCE.NS" in prompt
    assert "bull" in prompt

    # Test Claude API (with placeholder — no real key needed)
    response = call_claude_api(prompt)
    logger.info("Response: %s", response[:100])
    assert len(response) > 0, "Empty Claude response"

    # Test LIME explainer build (without actual model)
    X_mock = np.random.randn(100, 7).astype(np.float32)
    feature_names = list(mock_shap.keys())
    lime_exp = build_lime_explainer(X_mock, feature_names)
    logger.info("LIME explainer created: %s", type(lime_exp))

    logger.info("=== Smoke Test PASSED ===")
