"""
FinVoice — Explainer Service (XAI Layer)
SHAP, LIME, Factor Attribution, and NLG explanations.
"""

from typing import Optional
import numpy as np


class ExplainerService:
    """
    Generates explanations for ML model predictions.
    Three tiers: Short (free), Medium (paid), Full (paid report).
    """

    def __init__(self):
        self._shap_explainer = None
        self._lime_explainer = None

    def explain_xgboost_prediction(
        self,
        model,
        features: np.ndarray,
        feature_names: list[str],
        top_n: int = 5,
    ) -> dict:
        """
        SHAP-based explanation for XGBoost predictions.
        Returns feature importances and natural language explanation.
        """
        try:
            import shap

            if self._shap_explainer is None:
                self._shap_explainer = shap.TreeExplainer(model)

            shap_values = self._shap_explainer.shap_values(features)

            if len(shap_values.shape) > 1:
                sv = shap_values[0]
            else:
                sv = shap_values

            # Top N influential features
            abs_shap = np.abs(sv)
            top_indices = abs_shap.argsort()[-top_n:][::-1]

            top_features = []
            for idx in top_indices:
                top_features.append({
                    "feature": feature_names[idx],
                    "shap_value": round(float(sv[idx]), 4),
                    "impact": "positive" if sv[idx] > 0 else "negative",
                    "magnitude": round(float(abs_shap[idx]), 4),
                })

            # Generate explanations
            short = self._generate_short_explanation(top_features)
            medium = self._generate_medium_explanation(top_features)
            full = self._generate_full_explanation(top_features, sv, feature_names)

            return {
                "shap_values": {fn: round(float(v), 4) for fn, v in zip(feature_names, sv)},
                "top_features": top_features,
                "short_explanation": short,
                "medium_explanation": medium,
                "full_explanation": full,
            }

        except Exception as e:
            return {
                "shap_values": {},
                "top_features": [],
                "short_explanation": f"Explanation unavailable: {str(e)}",
                "medium_explanation": None,
                "full_explanation": None,
            }

    def compute_factor_attribution(
        self,
        portfolio_return: float,
        market_return: float,
        sector_returns: dict[str, float],
        portfolio_sector_weights: dict[str, float],
    ) -> dict:
        """
        Barra-style factor attribution.
        Decomposes portfolio return into: market beta, sector tilt, stock alpha, noise.
        """
        # Market beta contribution
        portfolio_beta = 1.0  # Placeholder — compute from regression
        market_contribution = portfolio_beta * market_return

        # Sector tilt contribution
        benchmark_sector_weight = 1.0 / max(len(sector_returns), 1)
        sector_contribution = 0.0
        for sector, weight in portfolio_sector_weights.items():
            excess_weight = weight - benchmark_sector_weight
            sector_ret = sector_returns.get(sector, 0)
            sector_contribution += excess_weight * sector_ret

        # Stock alpha = total - market - sector
        stock_alpha = portfolio_return - market_contribution - sector_contribution

        # Unexplained (noise)
        unexplained = 0.0  # In practice, this is the residual

        return {
            "market_beta_contribution": round(market_contribution, 4),
            "sector_tilt_contribution": round(sector_contribution, 4),
            "stock_alpha_contribution": round(stock_alpha, 4),
            "unexplained_noise": round(unexplained, 4),
        }

    def _generate_short_explanation(self, top_features: list[dict]) -> str:
        """One-sentence explanation (free tier)."""
        if not top_features:
            return "No significant factors identified."

        top = top_features[0]
        direction = "increased" if top["impact"] == "positive" else "decreased"
        feature_name = top["feature"].replace("_", " ").title()
        return f"Allocation {direction} primarily due to {feature_name}."

    def _generate_medium_explanation(self, top_features: list[dict]) -> str:
        """3-4 factor explanation (paid tier)."""
        if not top_features:
            return "No significant factors identified."

        parts = []
        for f in top_features[:4]:
            feature_name = f["feature"].replace("_", " ").title()
            direction = "positively" if f["impact"] == "positive" else "negatively"
            parts.append(f"{feature_name} ({direction} impacting)")

        return (
            f"This recommendation is driven by {len(parts)} key factors: "
            + ", ".join(parts[:-1])
            + (f", and {parts[-1]}" if len(parts) > 1 else parts[0])
            + "."
        )

    def _generate_full_explanation(
        self, top_features: list[dict], all_shap: np.ndarray, feature_names: list[str]
    ) -> str:
        """Detailed explanation with full breakdown (paid report)."""
        lines = ["## Prediction Explanation\n"]
        lines.append("### Top Contributing Factors\n")

        for i, f in enumerate(top_features, 1):
            feature_name = f["feature"].replace("_", " ").title()
            impact = "↑" if f["impact"] == "positive" else "↓"
            lines.append(
                f"{i}. **{feature_name}** {impact} (SHAP: {f['shap_value']:+.4f})"
            )

        lines.append("\n### Interpretation\n")
        positive_count = sum(1 for f in top_features if f["impact"] == "positive")
        negative_count = len(top_features) - positive_count

        if positive_count > negative_count:
            lines.append(
                "The model sees predominantly bullish signals from the analyzed features. "
                "The allocation recommendation leans toward growth assets."
            )
        else:
            lines.append(
                "The model detects cautionary signals from several features. "
                "The allocation recommendation favors defensive positioning."
            )

        return "\n".join(lines)
