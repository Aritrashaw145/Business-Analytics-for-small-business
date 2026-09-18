"""
The feedback loop.

1. `log_prediction` records a scenario the app recommended, tied to a
   concrete future calendar date.
2. Once that date plus the evaluation window has actually passed,
   `evaluate_predictions` compares the recommendation to what really
   happened (real `Sale` rows only) and fills in the outcome.
3. `get_prediction_accuracy_summary` aggregates evaluated predictions so
   the UI can show "how good have our recommendations actually been?"

This loop is read-only with respect to the model: it never edits model
weights or feeds its own output back in as a training feature (see
`src/ml/training.py`). It exists purely so a human can see whether the
model is worth trusting, and decide whether to retrain.
"""
from __future__ import annotations

from datetime import datetime, timedelta, date as date_type
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from src.config import settings
from src.db.models import Product, Sale, PredictionLog


def log_prediction(
    db: Session,
    business_id: int,
    day_of_week: int,
    post_type: str,
    predicted_daily_revenue: float,
    predicted_uplift_percent: float,
    confidence: str,
    model_run_id: Optional[int] = None,
    target_date: Optional[date_type] = None,
) -> PredictionLog:
    """Log a recommendation for later evaluation. If `target_date` isn't
    given, uses the next upcoming occurrence of `day_of_week`."""
    if target_date is None:
        today = datetime.now().date()
        days_ahead = (day_of_week - today.weekday()) % 7
        days_ahead = days_ahead or 7  # always a future date, not today
        target_date = today + timedelta(days=days_ahead)

    entry = PredictionLog(
        business_id=business_id,
        model_run_id=model_run_id,
        target_date=target_date,
        day_of_week=day_of_week,
        post_type=post_type,
        predicted_daily_revenue=predicted_daily_revenue,
        predicted_uplift_percent=predicted_uplift_percent,
        confidence=confidence,
        status="pending",
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def evaluate_predictions(db: Session, business_id: int) -> int:
    """Evaluate every pending prediction whose window has closed. Returns
    the number of predictions newly evaluated."""
    window = settings.prediction_evaluation_window_days
    today = datetime.now().date()

    pending = (
        db.query(PredictionLog)
        .filter(PredictionLog.business_id == business_id, PredictionLog.status == "pending")
        .all()
    )

    product_ids = [p.id for p in db.query(Product.id).filter(Product.business_id == business_id).all()]
    evaluated_count = 0

    for entry in pending:
        window_end = entry.target_date + timedelta(days=window - 1)
        if window_end > today:
            continue  # window hasn't closed yet

        before_start = entry.target_date - timedelta(days=7)
        before_end = entry.target_date - timedelta(days=1)

        before_total = (
            sum(
                s.total_amount
                for s in db.query(Sale).filter(
                    Sale.product_id.in_(product_ids),
                    Sale.sale_date >= before_start,
                    Sale.sale_date <= before_end,
                )
            )
            if product_ids
            else 0.0
        )
        after_total = (
            sum(
                s.total_amount
                for s in db.query(Sale).filter(
                    Sale.product_id.in_(product_ids),
                    Sale.sale_date >= entry.target_date,
                    Sale.sale_date <= window_end,
                )
            )
            if product_ids
            else 0.0
        )

        before_daily = before_total / 7 if before_total else 0.0
        after_daily = after_total / window if after_total else 0.0
        actual_uplift_percent = ((after_daily - before_daily) / before_daily * 100) if before_daily > 0 else 0.0

        entry.actual_daily_revenue = round(after_daily, 2)
        entry.actual_uplift_percent = round(actual_uplift_percent, 1)
        entry.absolute_error = round(abs(entry.predicted_daily_revenue - after_daily), 2)
        entry.status = "evaluated"
        entry.evaluated_at = datetime.utcnow()
        evaluated_count += 1

    if evaluated_count:
        db.commit()
    return evaluated_count


def get_prediction_accuracy_summary(db: Session, business_id: int) -> Dict[str, Any]:
    evaluate_predictions(db, business_id)

    evaluated = (
        db.query(PredictionLog)
        .filter(PredictionLog.business_id == business_id, PredictionLog.status == "evaluated")
        .order_by(PredictionLog.evaluated_at.desc())
        .all()
    )
    pending_count = (
        db.query(PredictionLog)
        .filter(PredictionLog.business_id == business_id, PredictionLog.status == "pending")
        .count()
    )

    if not evaluated:
        return {
            "has_data": False,
            "evaluated_count": 0,
            "pending_count": pending_count,
        }

    mae_values = [e.absolute_error for e in evaluated if e.absolute_error is not None]
    within_20pp = sum(
        1
        for e in evaluated
        if e.actual_uplift_percent is not None
        and abs(e.actual_uplift_percent - e.predicted_uplift_percent) <= 20
    )

    return {
        "has_data": True,
        "evaluated_count": len(evaluated),
        "pending_count": pending_count,
        "mean_absolute_error": round(sum(mae_values) / len(mae_values), 2) if mae_values else None,
        "accuracy_within_20pp_percent": round(within_20pp / len(evaluated) * 100, 1),
        "recent": [
            {
                "target_date": e.target_date.strftime("%Y-%m-%d"),
                "post_type": e.post_type,
                "predicted_uplift_percent": e.predicted_uplift_percent,
                "actual_uplift_percent": e.actual_uplift_percent,
                "confidence": e.confidence,
            }
            for e in evaluated[:10]
        ],
    }
