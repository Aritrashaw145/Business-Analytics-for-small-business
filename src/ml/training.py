"""
Training pipeline for the post-impact model.

`train_post_impact_model` is the only place a model is ever fit. It is
only ever invoked by an explicit user action (the "Train Model" button in
the UI, or a script) - nothing in this codebase retrains automatically or
adjusts model weights based on its own predictions. That is what keeps
the "improves only through evaluated historical outcomes, not uncontrolled
self-modification" requirement true: training reads real `Sale` and
`MediaPost` rows (via `get_sales_features`), evaluates on a held-out
split, and records everything in an immutable `ModelRun` audit row.
"""
from __future__ import annotations

from typing import Any, Dict

from sqlalchemy.orm import Session

from src.db.models import MediaPost
from src.ml.data_quality import assess_data_quality
from src.ml.features import FEATURE_COLUMNS, get_sales_features
from src.ml.storage import save_model_run


def train_post_impact_model(db: Session, business_id: int) -> Dict[str, Any]:
    """Fit a GradientBoostingRegressor on this business's real sales/post
    history and persist it. Returns a result dict the UI can render
    directly; on failure, `success` is False and `error` explains why -
    no exception escapes a bad-data situation."""
    try:
        from sklearn.ensemble import GradientBoostingRegressor
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import mean_absolute_error, r2_score
    except ImportError:
        return {"success": False, "error": "scikit-learn is not installed."}

    df = get_sales_features(db, business_id)
    posts_count = db.query(MediaPost).filter(MediaPost.business_id == business_id).count()

    quality = assess_data_quality(df, posts_count)

    if not quality.can_train:
        save_model_run(
            db,
            business_id,
            status="insufficient_data",
            sales_days_count=quality.sales_days_count,
            posts_count=quality.posts_count,
            data_quality_warnings=quality.warnings,
        )
        return {
            "success": False,
            "error": "Insufficient data to train a reliable model.",
            "warnings": quality.warnings,
            "sales_days_count": quality.sales_days_count,
            "posts_count": quality.posts_count,
        }

    available_cols = [c for c in FEATURE_COLUMNS if c in df.columns]
    X = df[available_cols]
    y = df["revenue"]

    test_size = 0.2 if len(X) >= 15 else max(1, int(len(X) * 0.2)) / len(X)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=42)

    model = GradientBoostingRegressor(n_estimators=100, max_depth=4, learning_rate=0.1, random_state=42)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    mae = float(mean_absolute_error(y_test, y_pred))
    r2 = float(r2_score(y_test, y_pred)) if len(y_test) > 1 else 0.0

    feature_importance = dict(zip(available_cols, [float(v) for v in model.feature_importances_]))
    baseline_revenue = float(df["revenue"].mean())

    run = save_model_run(
        db,
        business_id,
        status="trained",
        model_object=model,
        features=available_cols,
        baseline_revenue=baseline_revenue,
        data_points=len(df),
        sales_days_count=quality.sales_days_count,
        posts_count=quality.posts_count,
        mae=mae,
        r2=r2,
        feature_importance=feature_importance,
        data_quality_warnings=quality.warnings,
    )

    top_features = dict(sorted(feature_importance.items(), key=lambda kv: -kv[1])[:5])

    return {
        "success": True,
        "model_run_id": run.id,
        "trained_at": run.trained_at.isoformat(),
        "mae": round(mae, 2),
        "r2": round(r2, 3),
        "data_points": len(df),
        "feature_importance": {k: round(v, 4) for k, v in top_features.items()},
        "warnings": quality.warnings,
    }
