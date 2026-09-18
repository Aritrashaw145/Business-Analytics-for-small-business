"""
Turns a trained model (or, absent one, the plain slot-average fallback)
into the "best day/time/type to post" recommendation shown in the UI.

Confidence is always derived from the model's own held-out R², or forced
to "low" when there's no trained model - the UI is expected to show that
label prominently rather than presenting every number as equally solid.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from src.db.models import Product, Sale, MediaPost, ModelRun
from src.ml.features import DAY_NAMES, calculate_post_impact_by_slot
from src.ml.storage import get_active_model_run, load_active_model, model_run_summary

POST_TYPES = ("reel", "story", "image")


def predict_revenue_for_scenario(
    model_payload: Dict[str, Any],
    day_of_week: int,
    post_type: str,
    had_post: bool,
    recent_revenue_avg: float,
) -> float:
    model = model_payload["model"]
    features = model_payload["features"]

    row = {
        "day_of_week": day_of_week,
        "is_weekend": 1 if day_of_week >= 5 else 0,
        "revenue_3d_avg": recent_revenue_avg,
        "revenue_7d_avg": recent_revenue_avg,
        "orders_3d_avg": recent_revenue_avg / 100,
        "orders_7d_avg": recent_revenue_avg / 100,
        "had_post": 1 if had_post else 0,
        "had_post_yesterday": 0,
        "had_post_2days": 0,
        "had_post_3days": 0,
        "post_type_reel": 1 if post_type == "reel" else 0,
        "post_type_story": 1 if post_type == "story" else 0,
        "post_type_image": 1 if post_type == "image" else 0,
    }
    for i in range(7):
        row[f"dow_{i}"] = 1 if day_of_week == i else 0

    X = pd.DataFrame([{col: row.get(col, 0) for col in features}])
    return float(model.predict(X)[0])


def _recent_daily_revenue_avg(db: Session, product_ids: list) -> float:
    seven_days_ago = datetime.now().date() - timedelta(days=7)
    recent_sales = db.query(Sale).filter(Sale.product_id.in_(product_ids), Sale.sale_date >= seven_days_ago).all()

    sales_to_use = recent_sales
    if not sales_to_use:
        sales_to_use = db.query(Sale).filter(Sale.product_id.in_(product_ids)).all()
    if not sales_to_use:
        return 1000.0

    daily_revenues: Dict[Any, float] = {}
    for sale in sales_to_use:
        daily_revenues[sale.sale_date] = daily_revenues.get(sale.sale_date, 0.0) + sale.total_amount
    return sum(daily_revenues.values()) / max(len(daily_revenues), 1)


def get_best_posting_recommendation(db: Session, business_id: int) -> Dict[str, Any]:
    """Best day/time/type recommendation, ranked by expected sales uplift -
    never by engagement (Feature Rule)."""
    model_payload = load_active_model(db, business_id)
    active_run = get_active_model_run(db, business_id)

    product_ids = [p.id for p in db.query(Product.id).filter(Product.business_id == business_id).all()]
    if not product_ids:
        return {"error": "No products found", "recommendations": []}

    recent_revenue_avg = _recent_daily_revenue_avg(db, product_ids)
    slot_analysis = calculate_post_impact_by_slot(db, business_id)

    scenarios = []

    if model_payload:
        baseline_revenue = model_payload.get("baseline_revenue") or recent_revenue_avg
        r2 = active_run.r2 if active_run and active_run.r2 is not None else 0.0

        for day_idx, day_name in enumerate(DAY_NAMES):
            for post_type in POST_TYPES:
                predicted_with = predict_revenue_for_scenario(model_payload, day_idx, post_type, True, recent_revenue_avg)
                predicted_without = predict_revenue_for_scenario(model_payload, day_idx, post_type, False, recent_revenue_avg)

                uplift = predicted_with - predicted_without
                baseline = max(predicted_without, baseline_revenue, 1)
                uplift_percent = max(0.0, min((uplift / baseline * 100) if baseline > 0 else 0, 200.0))

                scenarios.append(
                    {
                        "day": day_name,
                        "day_of_week": day_idx,
                        "post_type": post_type,
                        "time_bucket": "evening",
                        "expected_revenue": round(predicted_with, 2),
                        "expected_uplift": round(uplift, 2),
                        "uplift_percent": round(uplift_percent, 1),
                        "confidence": "high" if r2 > 0.5 else "medium",
                    }
                )
    elif slot_analysis.get("slots"):
        day_type_avg: Dict[Any, Dict[str, Any]] = {}
        for slot in slot_analysis["slots"]:
            key = (slot["day_of_week"], slot["post_type"])
            bucket = day_type_avg.setdefault(key, {"lifts": [], "day_name": slot["day_name"]})
            bucket["lifts"].append(slot["lift_percent"])

        for (day_idx, post_type), data in day_type_avg.items():
            avg_lift = float(np.mean(data["lifts"]))
            scenarios.append(
                {
                    "day": data["day_name"],
                    "day_of_week": day_idx,
                    "post_type": post_type,
                    "time_bucket": "evening",
                    "expected_revenue": round(slot_analysis["baseline"] * (1 + avg_lift / 100), 2),
                    "expected_uplift": round(slot_analysis["baseline"] * avg_lift / 100, 2),
                    "uplift_percent": round(avg_lift, 1),
                    "confidence": "low",
                }
            )

    if not scenarios:
        return {
            "error": "Insufficient data for recommendations",
            "recommendations": [],
            "message": "Add more posts and sales data to get personalized recommendations",
        }

    scenarios.sort(key=lambda x: x["uplift_percent"], reverse=True)
    best = scenarios[0]

    best_day = max(
        [(d, sum(s["uplift_percent"] for s in scenarios if s["day"] == d)) for d in DAY_NAMES],
        key=lambda x: x[1],
    )[0]
    best_type = max(
        [(t, sum(s["uplift_percent"] for s in scenarios if s["post_type"] == t)) for t in POST_TYPES],
        key=lambda x: x[1],
    )[0]

    return {
        "best_overall": {
            "day": best["day"],
            "day_of_week": best["day_of_week"],
            "time": "Evening (6-9 PM)",
            "post_type": best["post_type"],
            "expected_uplift_percent": best["uplift_percent"],
            "expected_revenue": best["expected_revenue"],
            "confidence": best["confidence"],
        },
        "best_day": best_day,
        "best_post_type": best_type,
        "best_time": "Evening",
        "top_5_scenarios": scenarios[:5],
        "model_available": model_payload is not None,
        "data_based": len(slot_analysis.get("slots", [])) > 0,
        "message": f"Posting a {best['post_type']} on {best['day']} evening could increase your sales by ~{best['uplift_percent']:.0f}%",
    }


def get_posting_insights(db: Session, business_id: int) -> Dict[str, Any]:
    slot_analysis = calculate_post_impact_by_slot(db, business_id)
    if not slot_analysis.get("slots"):
        return {"has_data": False, "message": "Add media posts and sales to see posting insights"}

    slots = slot_analysis["slots"]

    def group_avg(key: str):
        groups: Dict[str, list] = {}
        for s in slots:
            groups.setdefault(s[key], []).append(s["lift_percent"])
        return {k: float(np.mean(v)) for k, v in groups.items()}, {k: len(v) for k, v in groups.items()}

    day_avg, day_counts = group_avg("day_name")
    type_avg, type_counts = group_avg("post_type")
    time_avg, time_counts = group_avg("time_bucket")

    return {
        "has_data": True,
        "total_posts_analyzed": len(slots),
        "baseline_daily_revenue": round(slot_analysis["baseline"], 2),
        "day_performance": [
            {"day": d, "avg_lift": round(l, 1), "post_count": day_counts[d]}
            for d, l in sorted(day_avg.items(), key=lambda x: -x[1])
        ],
        "type_performance": [
            {"type": t, "avg_lift": round(l, 1), "post_count": type_counts[t]}
            for t, l in sorted(type_avg.items(), key=lambda x: -x[1])
        ],
        "time_performance": [
            {"time": t, "avg_lift": round(l, 1), "post_count": time_counts[t]}
            for t, l in sorted(time_avg.items(), key=lambda x: -x[1])
        ],
    }


def get_model_status(db: Session, business_id: int) -> Dict[str, Any]:
    """Training status/date/performance for the UI - always DB-backed, so
    it works even before any model has ever been trained."""
    from src.ml.storage import get_latest_model_run

    latest_run = get_latest_model_run(db, business_id)
    active_run = get_active_model_run(db, business_id)

    summary = model_run_summary(active_run or latest_run)

    product_ids = [p.id for p in db.query(Product.id).filter(Product.business_id == business_id).all()]
    total_sales_days = (
        len({s.sale_date for s in db.query(Sale.sale_date).filter(Sale.product_id.in_(product_ids)).all()})
        if product_ids
        else 0
    )
    total_posts = db.query(MediaPost).filter(MediaPost.business_id == business_id).count()

    new_sales_days_since_training = 0
    new_posts_since_training = 0
    if active_run:
        new_sales_days_since_training = max(0, total_sales_days - (active_run.sales_days_count or 0))
        new_posts_since_training = max(0, total_posts - (active_run.posts_count or 0))

    should_retrain = active_run is None or new_sales_days_since_training >= 7 or new_posts_since_training >= 3

    summary["current_sales_days"] = total_sales_days
    summary["current_posts_count"] = total_posts
    summary["new_sales_days_since_training"] = new_sales_days_since_training
    summary["new_posts_since_training"] = new_posts_since_training
    summary["should_retrain"] = should_retrain
    return summary
