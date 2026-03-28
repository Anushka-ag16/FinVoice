"""
Sentiment Analysis Service — FinBERT-based sentiment scoring.

Uses ProsusAI/finbert from HuggingFace for financial sentiment classification.
Scrapes NSE corporate announcements and Google News RSS for headline text.
Score formula: softmax(logits)[:, 0] - softmax(logits)[:, 2]
  where index 0 = positive, index 2 = negative.
(ProsusAI/finbert labels: positive=0, neutral=1, negative=2)
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
import requests
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

logger = logging.getLogger(__name__)

# GPU detection
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
logger.info(f"Using device: {device}")

# In-memory model cache to avoid repeated loads
_MODEL_CACHE: dict[str, Any] = {}


# ══════════════════════════════════════════════════════════════════════════════
# Model Loading
# ══════════════════════════════════════════════════════════════════════════════
def load_finbert() -> tuple[AutoTokenizer, AutoModelForSequenceClassification]:
    """Load ProsusAI/finbert tokenizer and model, caching in memory.

    The model is moved to GPU if available.  Subsequent calls return the
    cached instances to avoid redundant downloads and memory allocation.

    Returns:
        Tuple of ``(tokenizer, model)``.
    """
    if "tokenizer" in _MODEL_CACHE and "model" in _MODEL_CACHE:
        logger.debug("Returning cached FinBERT model")
        return _MODEL_CACHE["tokenizer"], _MODEL_CACHE["model"]

    model_name = "ProsusAI/finbert"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name)
    model = model.to(device)
    model.eval()

    _MODEL_CACHE["tokenizer"] = tokenizer
    _MODEL_CACHE["model"] = model

    logger.info("FinBERT loaded on %s", device)
    return tokenizer, model


# ══════════════════════════════════════════════════════════════════════════════
# Sentiment Scoring
# ══════════════════════════════════════════════════════════════════════════════
def get_sentiment_score(
    texts: list[str],
    batch_size: int = 32,
) -> list[float]:
    """Compute sentiment scores for a list of texts using FinBERT.

    Score = P(positive) - P(negative), yielding a value in [-1, +1].
    Texts are processed in batches for GPU efficiency.

    Args:
        texts: List of text strings (headlines, announcements).
        batch_size: Number of texts per forward pass.

    Returns:
        List of sentiment scores in [-1, +1], one per input text.
    """
    if not texts:
        return []

    tokenizer, model = load_finbert()
    scores: list[float] = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]

        # Filter empty strings
        batch = [t if t and t.strip() else "neutral" for t in batch]

        encodings = tokenizer(
            batch,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt",
        )
        encodings = {k: v.to(device) for k, v in encodings.items()}

        with torch.no_grad():
            outputs = model(**encodings)
            logits = outputs.logits
            probs = torch.nn.functional.softmax(logits, dim=1)

        # ProsusAI/finbert: positive=0, neutral=1, negative=2
        positive_probs = probs[:, 0].cpu().numpy()
        negative_probs = probs[:, 2].cpu().numpy()
        batch_scores = (positive_probs - negative_probs).tolist()
        scores.extend(batch_scores)

    logger.info("Scored %d texts, mean=%.3f", len(scores), np.mean(scores))
    return scores


# ══════════════════════════════════════════════════════════════════════════════
# Data Scraping
# ══════════════════════════════════════════════════════════════════════════════
def scrape_nse_announcements(
    symbol: str,
    session: requests.Session | None = None,
) -> list[str]:
    """Fetch recent corporate announcements from NSE India API.

    Args:
        symbol: NSE stock symbol (e.g. ``RELIANCE``).
        session: Optional ``requests.Session`` with pre-set cookies/headers.

    Returns:
        List of announcement subject strings.
    """
    if session is None:
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
        })

    url = "https://www.nseindia.com/api/corporate-announcements"
    params = {"index": "equities", "symbol": symbol}

    try:
        # NSE requires a prior page visit to set cookies
        session.get("https://www.nseindia.com", timeout=10)
        resp = session.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        announcements: list[str] = []
        for item in data:
            subject = item.get("desc", "") or item.get("subject", "")
            if subject:
                announcements.append(subject.strip())

        logger.info("NSE announcements for %s: %d items", symbol, len(announcements))
        return announcements

    except Exception as exc:
        logger.warning("Failed to scrape NSE announcements for %s: %s", symbol, exc)
        return []


def scrape_google_news(
    symbol: str,
    n: int = 10,
) -> list[str]:
    """Fetch recent headlines from Google News RSS feed.

    Args:
        symbol: Stock symbol (used as search query).
        n: Maximum number of headlines to return.

    Returns:
        List of headline strings.
    """
    import feedparser

    # Strip .NS suffix for search
    clean_symbol = symbol.replace(".NS", "")
    query = f"{clean_symbol} stock India"
    url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"

    try:
        feed = feedparser.parse(url)
        headlines: list[str] = []
        for entry in feed.entries[:n]:
            title = entry.get("title", "")
            if title:
                headlines.append(title.strip())

        logger.info("Google News for %s: %d headlines", symbol, len(headlines))
        return headlines

    except Exception as exc:
        logger.warning("Failed to scrape Google News for %s: %s", symbol, exc)
        return []


# ══════════════════════════════════════════════════════════════════════════════
# Ticker-Level Sentiment
# ══════════════════════════════════════════════════════════════════════════════
def compute_ticker_sentiment(
    ticker: str,
    tokenizer: AutoTokenizer,
    model: AutoModelForSequenceClassification,
) -> pd.DataFrame:
    """Compute daily sentiment score for a ticker by combining announcements
    and news headlines.

    Args:
        ticker: Yahoo Finance ticker (e.g. ``RELIANCE.NS``).
        tokenizer: FinBERT tokenizer (unused directly but ensures model is loaded).
        model: FinBERT model (unused directly but ensures model is loaded).

    Returns:
        DataFrame with columns ``[date, score]``.
    """
    symbol = ticker.replace(".NS", "")

    # Gather texts from multiple sources
    texts = scrape_nse_announcements(symbol)
    texts.extend(scrape_google_news(ticker, n=10))

    if not texts:
        logger.warning("No texts found for %s, returning empty sentiment", ticker)
        return pd.DataFrame(columns=["date", "score"])

    scores = get_sentiment_score(texts)
    avg_score = float(np.mean(scores)) if scores else 0.0

    # We attach today's date — in production this would be per-announcement date
    today = pd.Timestamp.now().normalize()
    result = pd.DataFrame([{"date": today, "score": avg_score}])

    logger.info("Ticker sentiment for %s: %.3f (from %d texts)", ticker, avg_score, len(texts))
    return result


# ══════════════════════════════════════════════════════════════════════════════
# Feature Blending
# ══════════════════════════════════════════════════════════════════════════════
def blend_sentiment_features(
    features_df: pd.DataFrame,
    sentiment_df: pd.DataFrame,
) -> pd.DataFrame:
    """Blend sentiment scores into the feature DataFrame.

    Adds two columns:
      - ``sent_score``: raw sentiment score
      - ``sent_ma5``: 5-day rolling mean of sentiment

    Args:
        features_df: Main feature DataFrame indexed by date.
        sentiment_df: Sentiment DataFrame with ``date`` and ``score`` columns.

    Returns:
        Feature DataFrame with sentiment columns appended.
    """
    df = features_df.copy()

    if sentiment_df.empty:
        df["sent_score"] = 0.0
        df["sent_ma5"] = 0.0
        logger.warning("Empty sentiment DataFrame — filled with zeros")
        return df

    sentiment_df = sentiment_df.set_index("date") if "date" in sentiment_df.columns else sentiment_df
    sentiment_df = sentiment_df.rename(columns={"score": "sent_score"})

    df = df.join(sentiment_df[["sent_score"]], how="left")
    df["sent_score"] = df["sent_score"].ffill().fillna(0.0)
    df["sent_ma5"] = df["sent_score"].rolling(window=5, min_periods=1).mean()

    logger.info(
        "Blended sentiment features: sent_score mean=%.3f, sent_ma5 mean=%.3f",
        df["sent_score"].mean(), df["sent_ma5"].mean(),
    )
    return df


# ──────────────────────────────────────────────────────────────────────────────
# Smoke Test
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logger.info("=== Sentiment Service Smoke Test ===")

    # Test scoring with synthetic texts
    test_texts = [
        "Reliance Industries reports record quarterly profit",
        "Markets crash amid global recession fears",
        "HDFC Bank stock trades flat on low volume",
        "Infosys wins large deal worth $2 billion",
        "SEBI issues warning to several companies for non-compliance",
    ]

    scores = get_sentiment_score(test_texts, batch_size=3)
    logger.info("Scores: %s", scores)
    assert len(scores) == len(test_texts), f"Expected {len(test_texts)} scores, got {len(scores)}"
    assert all(-1.0 <= s <= 1.0 for s in scores), f"Scores out of range: {scores}"

    # Test blending
    dates = pd.date_range("2023-01-01", periods=20, freq="B")
    features = pd.DataFrame({"close": np.random.randn(20) * 100 + 2000}, index=dates)
    sentiment = pd.DataFrame({
        "date": dates[::5],
        "score": [0.3, -0.1, 0.5, 0.2],
    })

    blended = blend_sentiment_features(features, sentiment)
    assert "sent_score" in blended.columns, "Missing sent_score column"
    assert "sent_ma5" in blended.columns, "Missing sent_ma5 column"

    logger.info("=== Smoke Test PASSED ===")
