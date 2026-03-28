"""
FinVoice — FinBERT Sentiment Pipeline
Scores financial news/tweets for market sentiment and feeds scores as ML features.
Uses the pre-trained ProsusAI/finbert model from HuggingFace.
"""

import logging
import numpy as np
from typing import Optional

logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """
    Financial sentiment analysis using FinBERT.
    Processes news headlines, tweets, and analyst reports to generate
    sentiment scores that feed into the ML prediction pipeline.

    Outputs:
        - sentiment_score: float [-1, 1] (negative to positive)
        - sentiment_label: str (positive, negative, neutral)
        - confidence: float [0, 1]
    """

    MODEL_NAME = "ProsusAI/finbert"

    def __init__(self):
        self._pipeline = None
        self._loaded = False

    def _load_model(self):
        """Lazy-load FinBERT pipeline (heavy, ~500MB download first time)."""
        if self._loaded:
            return

        try:
            from transformers import pipeline as hf_pipeline

            self._pipeline = hf_pipeline(
                "sentiment-analysis",
                model=self.MODEL_NAME,
                tokenizer=self.MODEL_NAME,
                truncation=True,
                max_length=512,
            )
            self._loaded = True
            logger.info("FinBERT sentiment model loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load FinBERT: {e}")
            self._pipeline = None
            raise

    def analyze_text(self, text: str) -> dict:
        """
        Analyze a single text for financial sentiment.

        Args:
            text: News headline, tweet, or report excerpt.

        Returns:
            {
                "text": str,
                "sentiment_label": "positive" | "negative" | "neutral",
                "sentiment_score": float [-1, 1],
                "confidence": float [0, 1]
            }
        """
        self._load_model()

        if not text or not text.strip():
            return {
                "text": text,
                "sentiment_label": "neutral",
                "sentiment_score": 0.0,
                "confidence": 0.0,
            }

        result = self._pipeline(text)[0]
        label = result["label"].lower()
        confidence = result["score"]

        # Convert to numeric score
        if label == "positive":
            score = confidence
        elif label == "negative":
            score = -confidence
        else:
            score = 0.0

        return {
            "text": text[:200],
            "sentiment_label": label,
            "sentiment_score": round(score, 4),
            "confidence": round(confidence, 4),
        }

    def analyze_batch(self, texts: list[str]) -> list[dict]:
        """Analyze a batch of texts. Returns list of sentiment results."""
        self._load_model()

        if not texts:
            return []

        # Filter empty texts
        valid_texts = [(i, t) for i, t in enumerate(texts) if t and t.strip()]

        if not valid_texts:
            return [
                {"text": t, "sentiment_label": "neutral", "sentiment_score": 0.0, "confidence": 0.0}
                for t in texts
            ]

        # Batch inference
        batch_texts = [t for _, t in valid_texts]
        results = self._pipeline(batch_texts, batch_size=16)

        # Map results back
        output = [None] * len(texts)
        for (orig_idx, text), result in zip(valid_texts, results):
            label = result["label"].lower()
            confidence = result["score"]

            if label == "positive":
                score = confidence
            elif label == "negative":
                score = -confidence
            else:
                score = 0.0

            output[orig_idx] = {
                "text": text[:200],
                "sentiment_label": label,
                "sentiment_score": round(score, 4),
                "confidence": round(confidence, 4),
            }

        # Fill in any skipped empty texts
        for i, item in enumerate(output):
            if item is None:
                output[i] = {
                    "text": texts[i] if i < len(texts) else "",
                    "sentiment_label": "neutral",
                    "sentiment_score": 0.0,
                    "confidence": 0.0,
                }

        return output

    def score_for_symbol(self, headlines: list[str]) -> dict:
        """
        Aggregate sentiment for a specific stock from multiple headlines.

        Returns:
            {
                "avg_sentiment": float [-1, 1],
                "sentiment_std": float,
                "positive_ratio": float [0, 1],
                "negative_ratio": float [0, 1],
                "neutral_ratio": float [0, 1],
                "num_articles": int,
                "signal": "bullish" | "bearish" | "neutral"
            }
        """
        if not headlines:
            return {
                "avg_sentiment": 0.0,
                "sentiment_std": 0.0,
                "positive_ratio": 0.0,
                "negative_ratio": 0.0,
                "neutral_ratio": 1.0,
                "num_articles": 0,
                "signal": "neutral",
            }

        results = self.analyze_batch(headlines)
        scores = [r["sentiment_score"] for r in results]
        labels = [r["sentiment_label"] for r in results]

        avg_sentiment = float(np.mean(scores))
        sentiment_std = float(np.std(scores)) if len(scores) > 1 else 0.0

        n = len(labels)
        positive_ratio = labels.count("positive") / n
        negative_ratio = labels.count("negative") / n
        neutral_ratio = labels.count("neutral") / n

        # Determine overall signal
        if avg_sentiment > 0.2:
            signal = "bullish"
        elif avg_sentiment < -0.2:
            signal = "bearish"
        else:
            signal = "neutral"

        return {
            "avg_sentiment": round(avg_sentiment, 4),
            "sentiment_std": round(sentiment_std, 4),
            "positive_ratio": round(positive_ratio, 4),
            "negative_ratio": round(negative_ratio, 4),
            "neutral_ratio": round(neutral_ratio, 4),
            "num_articles": n,
            "signal": signal,
        }

    def generate_feature_vector(self, headlines_by_symbol: dict) -> dict:
        """
        Generate sentiment features for the ML pipeline.

        Args:
            headlines_by_symbol: {"RELIANCE": ["headline1", ...], "TCS": [...]}

        Returns:
            {"RELIANCE": {"sent_avg": 0.3, "sent_std": 0.1, "sent_pos_ratio": 0.6, ...}}
        """
        features = {}

        for symbol, headlines in headlines_by_symbol.items():
            agg = self.score_for_symbol(headlines)
            features[symbol] = {
                "sent_avg": agg["avg_sentiment"],
                "sent_std": agg["sentiment_std"],
                "sent_pos_ratio": agg["positive_ratio"],
                "sent_neg_ratio": agg["negative_ratio"],
                "sent_signal": 1 if agg["signal"] == "bullish" else (-1 if agg["signal"] == "bearish" else 0),
                "sent_num_articles": agg["num_articles"],
            }

        return features


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    analyzer = SentimentAnalyzer()

    test_headlines = [
        "Reliance Industries reports record quarterly profits",
        "TCS sees massive client attrition amid global slowdown",
        "Nifty 50 ends flat ahead of RBI policy decision",
        "HDFC Bank beats Street estimates, NPAs improve",
    ]

    for headline in test_headlines:
        result = analyzer.analyze_text(headline)
        print(f"{result['sentiment_label']:>8} ({result['sentiment_score']:+.2f}) | {headline}")
