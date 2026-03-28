"""
Model Registry Module — MLflow Model Versioning & Promotion.

Provides a thin, type-safe wrapper around the MLflow tracking client for
registering models, promoting versions to production, loading production
artifacts, listing versions, and comparing experiment runs.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import mlflow
import mlflow.pyfunc
import numpy as np
import pandas as pd
from mlflow.tracking import MlflowClient

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Client Initialisation
# ──────────────────────────────────────────────────────────────────────────────
def get_mlflow_client() -> MlflowClient:
    """Create and return an MLflow tracking client.

    The tracking URI is read from the ``MLFLOW_TRACKING_URI`` environment
    variable.  Falls back to ``sqlite:///mlflow.db`` for local development.

    Returns:
        Configured ``MlflowClient``.
    """
    tracking_uri = os.environ.get("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db")
    mlflow.set_tracking_uri(tracking_uri)
    client = MlflowClient(tracking_uri=tracking_uri)
    logger.info("MLflow client initialised (tracking_uri=%s)", tracking_uri)
    return client


# ──────────────────────────────────────────────────────────────────────────────
# Registration
# ──────────────────────────────────────────────────────────────────────────────
def register_model(
    run_id: str,
    model_name: str,
    artifact_path: str = "model",
) -> Any:
    """Register a logged model artifact as a versioned model.

    Args:
        run_id: MLflow run ID containing the logged model artifact.
        model_name: Registered model name (e.g. ``xgboost_predictor``).
        artifact_path: Relative path to the model artifact within the run.

    Returns:
        ``ModelVersion`` object with version number and metadata.
    """
    model_uri = f"runs:/{run_id}/{artifact_path}"
    mv = mlflow.register_model(model_uri, model_name)
    logger.info(
        "Registered model '%s' version %s from run %s",
        model_name, mv.version, run_id,
    )
    return mv


# ──────────────────────────────────────────────────────────────────────────────
# Promotion
# ──────────────────────────────────────────────────────────────────────────────
def promote_to_production(model_name: str, version: int | str) -> None:
    """Promote a model version to the 'Production' stage.

    Any existing production version is transitioned to 'Archived'.

    Args:
        model_name: Registered model name.
        version: Version number to promote.

    Raises:
        mlflow.exceptions.MlflowException: If model/version does not exist.
    """
    client = get_mlflow_client()

    # Archive current production version(s)
    try:
        for mv in client.get_latest_versions(model_name, stages=["Production"]):
            client.transition_model_version_stage(
                name=model_name,
                version=mv.version,
                stage="Archived",
            )
            logger.info(
                "Archived previous production version %s of '%s'",
                mv.version, model_name,
            )
    except Exception:
        pass  # No existing production version

    client.transition_model_version_stage(
        name=model_name,
        version=str(version),
        stage="Production",
    )
    logger.info("Promoted '%s' version %s to Production", model_name, version)


# ──────────────────────────────────────────────────────────────────────────────
# Loading
# ──────────────────────────────────────────────────────────────────────────────
def get_production_model(model_name: str) -> Any:
    """Load the current production version of a registered model.

    Args:
        model_name: Registered model name.

    Returns:
        Loaded ``mlflow.pyfunc.PyFuncModel`` ready for prediction.

    Raises:
        ValueError: If no production version exists.
    """
    client = get_mlflow_client()
    versions = client.get_latest_versions(model_name, stages=["Production"])

    if not versions:
        raise ValueError(
            f"No production version found for model '{model_name}'. "
            f"Register and promote a version first."
        )

    latest = versions[0]
    model_uri = f"models:/{model_name}/Production"
    model = mlflow.pyfunc.load_model(model_uri)
    logger.info(
        "Loaded production model '%s' version %s",
        model_name, latest.version,
    )
    return model


# ──────────────────────────────────────────────────────────────────────────────
# Listing
# ──────────────────────────────────────────────────────────────────────────────
def list_model_versions(model_name: str) -> list[Any]:
    """List all versions of a registered model.

    Args:
        model_name: Registered model name.

    Returns:
        List of ``ModelVersion`` objects sorted by version number.
    """
    client = get_mlflow_client()

    try:
        from mlflow.entities.model_registry import ModelVersion
        versions = client.search_model_versions(f"name='{model_name}'")
    except Exception:
        versions = []

    versions_sorted = sorted(versions, key=lambda mv: int(mv.version))
    logger.info("Found %d versions of '%s'", len(versions_sorted), model_name)
    return versions_sorted


# ──────────────────────────────────────────────────────────────────────────────
# Feature Importance Logging
# ──────────────────────────────────────────────────────────────────────────────
def log_feature_importance(
    model: Any,
    feature_names: list[str],
    run_id: str,
) -> None:
    """Log feature importances from a tree-based model to an MLflow run.

    Supports XGBoost, CatBoost, and scikit-learn models with a
    ``feature_importances_`` attribute.

    Args:
        model: Trained model with ``feature_importances_`` attribute.
        feature_names: Ordered list of feature names.
        run_id: MLflow run ID to log the artifact under.

    Raises:
        AttributeError: If the model lacks ``feature_importances_``.
    """
    importance = getattr(model, "feature_importances_", None)
    if importance is None:
        raise AttributeError(
            f"Model {type(model).__name__} does not have feature_importances_"
        )

    importance_df = pd.DataFrame({
        "feature": feature_names,
        "importance": importance,
    }).sort_values("importance", ascending=False)

    # Save as CSV artifact
    artifact_dir = Path("models") / "feature_importance"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    csv_path = artifact_dir / f"feature_importance_{run_id[:8]}.csv"
    tmp_path = csv_path.with_suffix(".tmp")
    importance_df.to_csv(tmp_path, index=False)
    tmp_path.replace(csv_path)

    client = get_mlflow_client()
    client.log_artifact(run_id, str(csv_path))
    logger.info("Feature importance logged for run %s (%d features)", run_id[:8], len(feature_names))


# ──────────────────────────────────────────────────────────────────────────────
# Run Comparison
# ──────────────────────────────────────────────────────────────────────────────
def compare_runs(
    run_ids: list[str],
    metric: str = "ic_mean",
) -> pd.DataFrame:
    """Compare multiple MLflow runs on a specific metric.

    Args:
        run_ids: List of MLflow run IDs to compare.
        metric: Metric name to extract and compare.

    Returns:
        DataFrame with columns ``[run_id, run_name, <metric>]`` sorted by
        the metric in descending order.
    """
    client = get_mlflow_client()
    rows: list[dict[str, Any]] = []

    for rid in run_ids:
        try:
            run = client.get_run(rid)
            metric_value = run.data.metrics.get(metric, float("nan"))
            run_name = run.data.tags.get("mlflow.runName", "unnamed")
            rows.append({
                "run_id": rid,
                "run_name": run_name,
                metric: metric_value,
            })
        except Exception as exc:
            logger.warning("Could not fetch run %s: %s", rid, exc)
            rows.append({"run_id": rid, "run_name": "error", metric: float("nan")})

    df = pd.DataFrame(rows).sort_values(metric, ascending=False)
    logger.info("Compared %d runs on metric '%s'", len(df), metric)
    return df


# ──────────────────────────────────────────────────────────────────────────────
# Smoke Test
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logger.info("=== Model Registry Smoke Test ===")

    # Test client creation
    client = get_mlflow_client()
    logger.info("Client created: %s", type(client))

    # Test compare_runs with empty list
    result = compare_runs([], metric="ic_mean")
    assert len(result) == 0, f"Expected empty DataFrame, got {len(result)} rows"

    # Test list_model_versions with non-existent model
    versions = list_model_versions("non_existent_model_test")
    assert len(versions) == 0, f"Expected 0 versions, got {len(versions)}"

    logger.info("=== Smoke Test PASSED ===")
