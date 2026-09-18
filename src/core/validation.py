"""
Validation for every place user-entered data enters the system: the manual
entry forms and the three CSV importers (Core Rule #4).

Every validator returns a `ValidationResult` with `is_valid`, a list of
human-readable `errors`, and (on success) a `cleaned` dict of normalized
values ready to hand to the ORM. Nothing here touches the database - it is
pure functions over plain Python values, which keeps it trivial to unit
test and reusable from both the Streamlit forms and the CSV importer.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time as time_type
from typing import Any, Dict, List, Optional

VALID_POST_TYPES = ("reel", "story", "image")
VALID_CATEGORIES = ("Beverages", "Bakery", "Pantry", "Breakfast", "Snacks", "Other")


@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    cleaned: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def ok(cleaned: Dict[str, Any]) -> "ValidationResult":
        return ValidationResult(is_valid=True, errors=[], cleaned=cleaned)

    @staticmethod
    def fail(*errors: str) -> "ValidationResult":
        return ValidationResult(is_valid=False, errors=list(errors), cleaned={})


def _to_float(value: Any) -> Optional[float]:
    try:
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> Optional[int]:
    f = _to_float(value)
    if f is None:
        return None
    return int(round(f))


def _to_date(value: Any) -> Optional[date]:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(value.strip(), fmt).date()
            except ValueError:
                continue
        try:
            import pandas as pd

            parsed = pd.to_datetime(value, errors="raise")
            return parsed.date()
        except Exception:
            return None
    return None


def _to_time(value: Any) -> Optional[time_type]:
    if isinstance(value, time_type):
        return value
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    parts = text.split(":")
    try:
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
        second = int(parts[2]) if len(parts) > 2 else 0
        return time_type(hour, minute, second)
    except (ValueError, IndexError):
        return None


# --------------------------------------------------------------------------
# Manual entry validation
# --------------------------------------------------------------------------

def validate_product(
    name: Any, cost_price: Any, selling_price: Any, category: Any = None
) -> ValidationResult:
    errors = []

    clean_name = str(name).strip() if name is not None else ""
    if not clean_name:
        errors.append("Product name is required.")
    elif len(clean_name) > 255:
        errors.append("Product name must be 255 characters or fewer.")

    cost = _to_float(cost_price)
    if cost is None:
        errors.append("Cost price must be a number.")
    elif cost < 0:
        errors.append("Cost price cannot be negative.")

    price = _to_float(selling_price)
    if price is None:
        errors.append("Selling price must be a number.")
    elif price <= 0:
        errors.append("Selling price must be greater than zero.")

    if cost is not None and price is not None and cost > price:
        errors.append("Cost price is higher than selling price - double check these numbers.")

    if errors:
        return ValidationResult.fail(*errors)

    clean_category = str(category).strip() if category else "Other"
    return ValidationResult.ok(
        {
            "name": clean_name,
            "cost_price": round(cost, 2),
            "selling_price": round(price, 2),
            "category": clean_category or "Other",
        }
    )


def validate_sale(quantity: Any, sale_date: Any, product_id: Optional[int] = None) -> ValidationResult:
    errors = []

    qty = _to_int(quantity)
    if qty is None:
        errors.append("Quantity must be a whole number.")
    elif qty <= 0:
        errors.append("Quantity must be at least 1.")

    parsed_date = _to_date(sale_date)
    if parsed_date is None:
        errors.append("Sale date is missing or not a recognizable date.")
    elif parsed_date > date.today():
        errors.append("Sale date cannot be in the future.")

    if product_id is None:
        errors.append("A product must be selected for this sale.")

    if errors:
        return ValidationResult.fail(*errors)

    return ValidationResult.ok(
        {"quantity": qty, "sale_date": parsed_date, "product_id": product_id}
    )


def validate_media_post(
    post_type: Any,
    posted_at: Any,
    caption: Any = None,
    post_time: Any = None,
    platform: Any = None,
    impressions: Any = 0,
    likes: Any = 0,
    comments: Any = 0,
    shares: Any = 0,
) -> ValidationResult:
    errors = []

    clean_type = str(post_type).strip().lower() if post_type else ""
    if clean_type not in VALID_POST_TYPES:
        errors.append(f"Post type must be one of {', '.join(VALID_POST_TYPES)}.")

    parsed_date = _to_date(posted_at)
    if parsed_date is None:
        errors.append("Post date is missing or not a recognizable date.")
    elif parsed_date > date.today():
        errors.append("Post date cannot be in the future.")

    parsed_time = _to_time(post_time)

    metrics = {}
    for label, value in (
        ("impressions", impressions),
        ("likes", likes),
        ("comments", comments),
        ("shares", shares),
    ):
        parsed = _to_int(value) if value not in (None, "") else 0
        if parsed is None or parsed < 0:
            errors.append(f"{label.capitalize()} must be a non-negative whole number.")
            parsed = 0
        metrics[label] = parsed

    if errors:
        return ValidationResult.fail(*errors)

    clean_caption = str(caption)[:500] if caption else ""
    clean_platform = str(platform).strip() if platform else "instagram"

    return ValidationResult.ok(
        {
            "post_type": clean_type,
            "posted_at": parsed_date,
            "caption": clean_caption,
            "post_time": parsed_time,
            "platform": clean_platform or "instagram",
            **metrics,
        }
    )


def validate_signup(
    business_name: Any, owner_name: Any, email: Any, password: Any, confirm_password: Any
) -> ValidationResult:
    errors = []

    if not business_name or not str(business_name).strip():
        errors.append("Business name is required.")
    if not owner_name or not str(owner_name).strip():
        errors.append("Owner name is required.")

    clean_email = str(email).strip().lower() if email else ""
    if not clean_email or "@" not in clean_email or "." not in clean_email.split("@")[-1]:
        errors.append("Enter a valid email address.")

    if not password or len(str(password)) < 6:
        errors.append("Password must be at least 6 characters.")
    elif password != confirm_password:
        errors.append("Passwords do not match.")

    if errors:
        return ValidationResult.fail(*errors)

    return ValidationResult.ok(
        {
            "business_name": str(business_name).strip(),
            "owner_name": str(owner_name).strip(),
            "email": clean_email,
            "password": str(password),
        }
    )
