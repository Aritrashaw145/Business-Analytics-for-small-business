"""
Model persistence.

The fitted scikit-learn model is pickled to disk (one file per business,
never shared across tenants). Everything needed to show "training
status/date/model performance" in the UI is instead stored in the
`ModelRun` table (src.db.models), so the UI never needs to unpickle a
model just to display when it was last trained.
"""
from __future__ import annotations

import json
import os
import pickle
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from src.config import settings
from src.db.models import ModelRun


def _model_dir() -> str:
    os.makedirs(settings.model_dir, exist_ok=True)
    return settings.model_dir


def _model_path(business_id: int) -> str:
    return os.path.join(_model_dir(), f"post_impact_model_{business_id}.pkl")


def save_model_run(
    db: Session,
    business_id: int,
    status: str,
    model_object: Optional[Any] = None,
    features: Optional[list] = None,
    baseline_revenue: Optional[float] = None,
    data_points: int = 0,
    sales_days_count: int = 0,
    posts_count: int = 0,
    mae: Optional[float] = None,
    r2: Optional[float] = None,
    feature_importance: Optional[Dict[str, float]] = None,
    data_quality_warnings: Optional[list] = None,
) -> ModelRun:
    """Persist one training run: the pickle (if a model was actually fit)
    plus a permanent audit row in `model_runs`. Marks this run active and
    every earlier run for the business inactive, so `load_active_model`
    always returns the most recent successfully trained model."""
    model_file_path = None

    if model_object is not None:
        model_file_path = _model_path(business_id)
        payload = {
            "model": model_object,
            "features": features or [],
            "business_id": business_id,
            "trained_at": datetime.utcnow().isoformat(),
            "baseline_revenue": baseline_revenue,
        }
        with open(model_file_path, "wb") as f:
            pickle.dump(payload, f)

    if status == "trained":
        # Only demote earlier runs once a new model has actually been fit
        # successfully - a failed or insufficient-data attempt must never
        # take the last good model out of service.
        db.query(ModelRun).filter(ModelRun.business_id == business_id).update({"is_active": False})

    run = ModelRun(
        business_id=business_id,
        trained_at=datetime.utcnow(),
        status=status,
        data_points=data_points,
        sales_days_count=sales_days_count,
        posts_count=posts_count,
        mae=mae,
        r2=r2,
        feature_importance_json=json.dumps(feature_importance) if feature_importance else None,
        data_quality_notes_json=json.dumps(data_quality_warnings) if data_quality_warnings else None,
        model_file_path=model_file_path,
        is_active=status == "trained",
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def get_latest_model_run(db: Session, business_id: int) -> Optional[ModelRun]:
    return (
        db.query(ModelRun)
        .filter(ModelRun.business_id == business_id)
        .order_by(ModelRun.trained_at.desc())
        .first()
    )


def get_active_model_run(db: Session, business_id: int) -> Optional[ModelRun]:
    return (
        db.query(ModelRun)
        .filter(ModelRun.business_id == business_id, ModelRun.is_active.is_(True))
        .order_by(ModelRun.trained_at.desc())
        .first()
    )


def load_active_model(db: Session, business_id: int) -> Optional[Dict[str, Any]]:
    """Load the pickled model payload for the currently active run, if any."""
    run = get_active_model_run(db, business_id)
    if run is None or not run.model_file_path or not os.path.exists(run.model_file_path):
        return None
    with open(run.model_file_path, "rb") as f:
        return pickle.load(f)


def model_run_summary(run: Optional[ModelRun]) -> Dict[str, Any]:
    if run is None:
        return {"status": "never_trained", "trained_at": None}

    feature_importance = json.loads(run.feature_importance_json) if run.feature_importance_json else {}
    warnings = json.loads(run.data_quality_notes_json) if run.data_quality_notes_json else []

    return {
        "status": run.status,
        "trained_at": run.trained_at.isoformat() if run.trained_at else None,
        "data_points": run.data_points,
        "sales_days_count": run.sales_days_count,
        "posts_count": run.posts_count,
        "mae": run.mae,
        "r2": run.r2,
        "feature_importance": feature_importance,
        "warnings": warnings,
        "is_active": run.is_active,
    }
