"""
Data-quality gate the training pipeline runs before fitting anything.

This is what stops the model from being trained - or a prediction from
being presented as reliable - when the business simply doesn't have
enough real history yet (Feature Rule: "Do not present a recommendation
as reliable when historical data is insufficient").
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import pandas as pd

from src.config import settings


@dataclass
class DataQualityReport:
    can_train: bool
    sales_days_count: int
    posts_count: int
    revenue_variance: float
    warnings: List[str] = field(default_factory=list)


def assess_data_quality(df: pd.DataFrame, posts_count: int) -> DataQualityReport:
    warnings: List[str] = []
    sales_days_count = len(df)

    if df.empty:
        return DataQualityReport(
            can_train=False,
            sales_days_count=0,
            posts_count=posts_count,
            revenue_variance=0.0,
            warnings=["No sales data available yet."],
        )

    revenue_variance = float(df["revenue"].var()) if len(df) > 1 else 0.0

    can_train = True
    if sales_days_count < settings.min_training_days:
        can_train = False
        warnings.append(
            f"Only {sales_days_count} days of usable sales history "
            f"(need at least {settings.min_training_days})."
        )
    elif sales_days_count < settings.min_training_days * 3:
        warnings.append(
            f"Only {sales_days_count} days of history - predictions will improve "
            "as more sales are recorded."
        )

    if posts_count < settings.min_training_posts:
        can_train = False
        warnings.append(
            f"Only {posts_count} tracked posts (need at least {settings.min_training_posts}) "
            "to learn a posting-impact pattern."
        )

    if revenue_variance == 0 and sales_days_count > 1:
        can_train = False
        warnings.append("Revenue is identical every day - there's no pattern for the model to learn yet.")

    return DataQualityReport(
        can_train=can_train,
        sales_days_count=sales_days_count,
        posts_count=posts_count,
        revenue_variance=revenue_variance,
        warnings=warnings,
    )
