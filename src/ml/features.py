"""
Feature engineering for the post-impact model.

Everything here reads only real `Sale` and `MediaPost` rows from the
database - never predictions or synthetic data - so the model can only
ever learn from ground truth (see PROJECT_GUIDE.md, "How the ML system
stays controlled").
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from src.db.models import Product, Sale, MediaPost

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

FEATURE_COLUMNS = [
    "day_of_week", "is_weekend",
    "revenue_3d_avg", "revenue_7d_avg",
    "orders_3d_avg", "orders_7d_avg",
    "had_post", "had_post_yesterday", "had_post_2days", "had_post_3days",
    "post_type_reel", "post_type_story", "post_type_image",
    "dow_0", "dow_1", "dow_2", "dow_3", "dow_4", "dow_5", "dow_6",
]


def get_sales_features(db: Session, business_id: int) -> pd.DataFrame:
    """Build one row per calendar day with revenue, posting activity, and
    rolling-average features. Returns an empty DataFrame if there isn't
    enough real data to build any complete feature row."""
    product_ids = [p.id for p in db.query(Product.id).filter(Product.business_id == business_id).all()]
    if not product_ids:
        return pd.DataFrame()

    sales = db.query(Sale).filter(Sale.product_id.in_(product_ids)).all()
    posts = db.query(MediaPost).filter(MediaPost.business_id == business_id).all()
    if not sales:
        return pd.DataFrame()

    valid_dates = [s.sale_date for s in sales if s.sale_date]
    valid_dates.extend([p.posted_at for p in posts if p.posted_at])
    if not valid_dates:
        return pd.DataFrame()

    start_date = min(valid_dates)
    end_date = max(valid_dates + [datetime.now().date()])

    daily_data = {}
    current = start_date
    while current <= end_date:
        daily_data[current] = {
            "date": current,
            "day_of_week": current.weekday(),
            "revenue": 0.0,
            "orders": 0,
            "had_post": 0,
            "post_type_reel": 0,
            "post_type_story": 0,
            "post_type_image": 0,
            "post_hour": -1,
        }
        current += timedelta(days=1)

    for sale in sales:
        if sale.sale_date in daily_data:
            daily_data[sale.sale_date]["revenue"] += sale.total_amount
            daily_data[sale.sale_date]["orders"] += 1

    for post in posts:
        post_date = post.posted_at
        if post_date in daily_data:
            daily_data[post_date]["had_post"] = 1
            key = f"post_type_{post.post_type}"
            if key in daily_data[post_date]:
                daily_data[post_date][key] = 1
            if post.post_time:
                daily_data[post_date]["post_hour"] = post.post_time.hour

    df = pd.DataFrame(list(daily_data.values())).sort_values("date").reset_index(drop=True)

    df["revenue_3d_avg"] = df["revenue"].rolling(window=3, min_periods=1).mean().shift(1)
    df["revenue_7d_avg"] = df["revenue"].rolling(window=7, min_periods=1).mean().shift(1)
    df["orders_3d_avg"] = df["orders"].rolling(window=3, min_periods=1).mean().shift(1)
    df["orders_7d_avg"] = df["orders"].rolling(window=7, min_periods=1).mean().shift(1)

    df["had_post_yesterday"] = df["had_post"].shift(1).fillna(0)
    df["had_post_2days"] = df["had_post"].shift(2).fillna(0)
    df["had_post_3days"] = df["had_post"].shift(3).fillna(0)

    df["is_weekend"] = df["day_of_week"].apply(lambda x: 1 if x >= 5 else 0)
    for i in range(7):
        df[f"dow_{i}"] = (df["day_of_week"] == i).astype(int)

    return df.dropna()


def calculate_post_impact_by_slot(db: Session, business_id: int) -> Dict[str, Any]:
    """Average sales uplift per (day, time-of-day, post type) slot - the
    non-ML fallback used when there isn't yet a trained model."""
    product_ids = [p.id for p in db.query(Product.id).filter(Product.business_id == business_id).all()]
    if not product_ids:
        return {"slots": [], "baseline": 0}

    posts = db.query(MediaPost).filter(MediaPost.business_id == business_id).all()
    if len(posts) < 3:
        return {"slots": [], "baseline": 0, "error": "Need at least 3 posts for analysis"}

    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=180)
    sales = db.query(Sale).filter(Sale.product_id.in_(product_ids), Sale.sale_date >= start_date).all()
    if not sales:
        return {"slots": [], "baseline": 0}

    daily_sales: Dict[Any, float] = {}
    for sale in sales:
        daily_sales[sale.sale_date] = daily_sales.get(sale.sale_date, 0.0) + sale.total_amount

    baseline_revenues = list(daily_sales.values())
    baseline_daily = float(np.mean(baseline_revenues)) if baseline_revenues else 0.0

    slot_impacts = []
    for post in posts:
        post_date = post.posted_at

        before_start = post_date - timedelta(days=7)
        before_sales = sum(daily_sales.get(before_start + timedelta(days=i), 0) for i in range(7))
        before_daily = before_sales / 7 if before_sales else baseline_daily

        after_sales = sum(daily_sales.get(post_date + timedelta(days=i), 0) for i in range(3))
        after_daily = after_sales / 3 if after_sales else 0

        lift_percent = ((after_daily - before_daily) / before_daily * 100) if before_daily > 0 else 0

        hour_bucket = "morning"
        if post.post_time:
            hour = post.post_time.hour
            if hour >= 17:
                hour_bucket = "evening"
            elif hour >= 12:
                hour_bucket = "afternoon"

        slot_impacts.append(
            {
                "day_of_week": post_date.weekday(),
                "day_name": DAY_NAMES[post_date.weekday()],
                "time_bucket": hour_bucket,
                "post_type": post.post_type,
                "lift_percent": lift_percent,
                "post_daily": after_daily,
                "baseline_daily": before_daily,
            }
        )

    return {"slots": slot_impacts, "baseline": baseline_daily}
