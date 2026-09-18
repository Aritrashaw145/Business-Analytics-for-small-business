"""
CSV import for products, sales, and media posts.

Design goals (Core Rule #4 / Data Management feature rules):
  * Validate columns, types, and dates before writing anything.
  * Never silently drop a bad row - every rejected row is reported back
    with a reason, so the caller can show or export it.
  * A single successful `import_*` call commits once, so a partially bad
    file still saves every row that *did* validate.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import time as time_type
from typing import Any, Dict, List

import pandas as pd
from sqlalchemy.orm import Session

from src.db.models import Product, Sale, MediaPost
from src.core.validation import validate_media_post

REQUIRED_PRODUCT_COLUMNS = {"name", "cost_price", "selling_price"}
REQUIRED_SALE_COLUMNS = {"product_name", "quantity", "sale_date"}
REQUIRED_MEDIA_COLUMNS = {"post_type", "posted_at"}


@dataclass
class RejectedRow:
    row_number: int  # 1-based, matching what a spreadsheet user would see
    reason: str
    raw: Dict[str, Any]


@dataclass
class ImportResult:
    imported_count: int = 0
    rejected: List[RejectedRow] = field(default_factory=list)
    missing_columns: List[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return not self.missing_columns

    def rejected_dataframe(self) -> pd.DataFrame:
        if not self.rejected:
            return pd.DataFrame(columns=["row", "reason"])
        return pd.DataFrame(
            [{"row": r.row_number, "reason": r.reason, **r.raw} for r in self.rejected]
        )


def _check_columns(df: pd.DataFrame, required: set) -> List[str]:
    present = {c.strip().lower() for c in df.columns}
    return sorted(col for col in required if col not in present)


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    return df


def import_products_csv(db: Session, business_id: int, df: pd.DataFrame) -> ImportResult:
    df = _normalize_columns(df)
    result = ImportResult(missing_columns=_check_columns(df, REQUIRED_PRODUCT_COLUMNS))
    if not result.success:
        return result

    from src.core.validation import validate_product

    rows_to_add = []
    for idx, row in df.iterrows():
        row_number = int(idx) + 1
        validation = validate_product(
            row.get("name"), row.get("cost_price"), row.get("selling_price"), row.get("category")
        )
        if not validation.is_valid:
            result.rejected.append(RejectedRow(row_number, "; ".join(validation.errors), row.to_dict()))
            continue
        c = validation.cleaned
        rows_to_add.append(
            Product(
                business_id=business_id,
                name=c["name"],
                cost_price=c["cost_price"],
                selling_price=c["selling_price"],
                category=c["category"],
            )
        )

    for product in rows_to_add:
        db.add(product)
    db.commit()
    result.imported_count = len(rows_to_add)
    return result


def import_sales_csv(db: Session, business_id: int, df: pd.DataFrame) -> ImportResult:
    df = _normalize_columns(df)
    result = ImportResult(missing_columns=_check_columns(df, REQUIRED_SALE_COLUMNS))
    if not result.success:
        return result

    from src.core.validation import validate_sale

    products = db.query(Product).filter(Product.business_id == business_id).all()
    product_map = {p.name.strip().lower(): p for p in products}

    rows_to_add = []
    for idx, row in df.iterrows():
        row_number = int(idx) + 1
        product_name = str(row.get("product_name", "")).strip().lower()
        product = product_map.get(product_name)

        if product is None:
            result.rejected.append(
                RejectedRow(row_number, f"Product '{row.get('product_name')}' not found for this business.", row.to_dict())
            )
            continue

        validation = validate_sale(row.get("quantity"), row.get("sale_date"), product_id=product.id)
        if not validation.is_valid:
            result.rejected.append(RejectedRow(row_number, "; ".join(validation.errors), row.to_dict()))
            continue

        c = validation.cleaned
        rows_to_add.append(
            Sale(
                product_id=product.id,
                quantity=c["quantity"],
                total_amount=round(c["quantity"] * product.selling_price, 2),
                sale_date=c["sale_date"],
            )
        )

    for sale in rows_to_add:
        db.add(sale)
    db.commit()
    result.imported_count = len(rows_to_add)
    return result


def import_media_posts_csv(db: Session, business_id: int, df: pd.DataFrame) -> ImportResult:
    df = _normalize_columns(df)
    result = ImportResult(missing_columns=_check_columns(df, REQUIRED_MEDIA_COLUMNS))
    if not result.success:
        return result

    rows_to_add = []
    for idx, row in df.iterrows():
        row_number = int(idx) + 1
        validation = validate_media_post(
            post_type=row.get("post_type"),
            posted_at=row.get("posted_at"),
            caption=row.get("caption"),
            post_time=row.get("post_time"),
            platform=row.get("platform"),
            impressions=row.get("impressions", 0),
            likes=row.get("likes", 0),
            comments=row.get("comments", 0),
            shares=row.get("shares", 0),
        )
        if not validation.is_valid:
            result.rejected.append(RejectedRow(row_number, "; ".join(validation.errors), row.to_dict()))
            continue

        c = validation.cleaned
        rows_to_add.append(
            MediaPost(
                business_id=business_id,
                post_type=c["post_type"],
                caption=c["caption"],
                posted_at=c["posted_at"],
                post_time=c["post_time"],
                platform=c["platform"],
                impressions=c["impressions"],
                likes=c["likes"],
                comments=c["comments"],
                shares=c["shares"],
            )
        )

    for post in rows_to_add:
        db.add(post)
    db.commit()
    result.imported_count = len(rows_to_add)
    return result
