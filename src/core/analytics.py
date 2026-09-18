"""
Dashboard and business analytics.

Every function here takes `business_id` and scopes its query to that
business's own products/sales/posts (Core Rule #1 - tenant isolation).
Profit is always `(selling_price - cost_price) * quantity` (Feature Rule).
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import func

from src.db.models import Product, Sale, MediaPost

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _business_product_ids(db: Session, business_id: int) -> List[int]:
    return [p.id for p in db.query(Product.id).filter(Product.business_id == business_id).all()]


def get_dashboard_stats(db: Session, business_id: int) -> Dict[str, Any]:
    products = db.query(Product).filter(Product.business_id == business_id).all()
    product_ids = [p.id for p in products]

    if not product_ids:
        return {"total_revenue": 0, "total_profit": 0, "total_orders": 0, "total_products": 0}

    sales = db.query(Sale).filter(Sale.product_id.in_(product_ids)).all()

    total_revenue = sum(s.total_amount for s in sales)
    total_orders = len(sales)

    products_by_id = {p.id: p for p in products}
    total_profit = 0.0
    for sale in sales:
        product = products_by_id.get(sale.product_id)
        if product:
            total_profit += (product.selling_price - product.cost_price) * sale.quantity

    return {
        "total_revenue": round(total_revenue, 2),
        "total_profit": round(total_profit, 2),
        "total_orders": total_orders,
        "total_products": len(products),
    }


def get_best_selling_products(db: Session, business_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    products = db.query(Product).filter(Product.business_id == business_id).all()
    product_ids = [p.id for p in products]
    if not product_ids:
        return []

    result = (
        db.query(
            Sale.product_id,
            func.sum(Sale.quantity).label("total_quantity"),
            func.sum(Sale.total_amount).label("total_revenue"),
        )
        .filter(Sale.product_id.in_(product_ids))
        .group_by(Sale.product_id)
        .order_by(func.sum(Sale.quantity).desc())
        .limit(limit)
        .all()
    )

    products_by_id = {p.id: p for p in products}
    best_products = []
    for r in result:
        product = products_by_id.get(r.product_id)
        if product:
            best_products.append(
                {
                    "name": product.name,
                    "category": product.category,
                    "quantity_sold": int(r.total_quantity),
                    "revenue": round(float(r.total_revenue), 2),
                }
            )
    return best_products


def get_most_profitable_products(db: Session, business_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    products = db.query(Product).filter(Product.business_id == business_id).all()
    product_ids = [p.id for p in products]
    if not product_ids:
        return []

    sales_data = (
        db.query(
            Sale.product_id,
            func.sum(Sale.quantity).label("total_quantity"),
        )
        .filter(Sale.product_id.in_(product_ids))
        .group_by(Sale.product_id)
        .all()
    )

    profitable_products = []
    for s in sales_data:
        product = next((p for p in products if p.id == s.product_id), None)
        if product:
            profit_per_unit = product.selling_price - product.cost_price
            total_profit = profit_per_unit * s.total_quantity
            profitable_products.append(
                {
                    "name": product.name,
                    "category": product.category,
                    "profit": round(total_profit, 2),
                    "profit_margin": round((profit_per_unit / product.selling_price) * 100, 1)
                    if product.selling_price > 0
                    else 0,
                }
            )

    profitable_products.sort(key=lambda x: x["profit"], reverse=True)
    return profitable_products[:limit]


def get_best_day_of_week(db: Session, business_id: int) -> Dict[str, Any]:
    product_ids = _business_product_ids(db, business_id)
    if not product_ids:
        return {"day": "N/A", "revenue": 0, "daily_breakdown": []}

    sales = db.query(Sale).filter(Sale.product_id.in_(product_ids)).all()
    if not sales:
        return {"day": "N/A", "revenue": 0, "daily_breakdown": []}

    daily_revenue = {day: 0.0 for day in DAY_NAMES}
    for sale in sales:
        daily_revenue[DAY_NAMES[sale.sale_date.weekday()]] += sale.total_amount

    best_day = max(daily_revenue, key=daily_revenue.get)
    daily_breakdown = [{"day": day, "revenue": round(rev, 2)} for day, rev in daily_revenue.items()]

    return {
        "day": best_day,
        "revenue": round(daily_revenue[best_day], 2),
        "daily_breakdown": daily_breakdown,
    }


def get_weekly_trends(db: Session, business_id: int, weeks: int = 8) -> List[Dict[str, Any]]:
    product_ids = _business_product_ids(db, business_id)
    if not product_ids:
        return []

    sales = db.query(Sale).filter(Sale.product_id.in_(product_ids)).all()
    if not sales:
        return []

    weekly_data: Dict[str, Dict[str, float]] = {}
    for sale in sales:
        week_start = sale.sale_date - timedelta(days=sale.sale_date.weekday())
        week_key = week_start.strftime("%Y-%m-%d")
        bucket = weekly_data.setdefault(week_key, {"revenue": 0.0, "orders": 0})
        bucket["revenue"] += sale.total_amount
        bucket["orders"] += 1

    trends = [
        {"week": week, "revenue": round(data["revenue"], 2), "orders": data["orders"]}
        for week, data in sorted(weekly_data.items())
    ]
    return trends[-weeks:]


def get_monthly_trends(db: Session, business_id: int, months: int = 6) -> List[Dict[str, Any]]:
    product_ids = _business_product_ids(db, business_id)
    if not product_ids:
        return []

    sales = db.query(Sale).filter(Sale.product_id.in_(product_ids)).all()

    monthly_data: Dict[str, Dict[str, float]] = {}
    for sale in sales:
        month_key = sale.sale_date.strftime("%Y-%m")
        bucket = monthly_data.setdefault(month_key, {"revenue": 0.0, "orders": 0})
        bucket["revenue"] += sale.total_amount
        bucket["orders"] += 1

    trends = [
        {"month": month, "revenue": round(data["revenue"], 2), "orders": data["orders"]}
        for month, data in sorted(monthly_data.items())
    ]
    return trends[-months:]


def get_low_performing_products(db: Session, business_id: int, days: int = 30, limit: int = 10) -> List[Dict[str, Any]]:
    products = db.query(Product).filter(Product.business_id == business_id).all()
    product_ids = [p.id for p in products]
    if not product_ids:
        return []

    cutoff_date = datetime.now().date() - timedelta(days=days)

    sales_data = (
        db.query(
            Sale.product_id,
            func.sum(Sale.quantity).label("total_quantity"),
            func.sum(Sale.total_amount).label("total_revenue"),
        )
        .filter(Sale.product_id.in_(product_ids), Sale.sale_date >= cutoff_date)
        .group_by(Sale.product_id)
        .all()
    )

    sales_by_product = {s.product_id: {"quantity": s.total_quantity, "revenue": s.total_revenue} for s in sales_data}

    low_performers = []
    for product in products:
        info = sales_by_product.get(product.id, {"quantity": 0, "revenue": 0})
        low_performers.append(
            {
                "name": product.name,
                "category": product.category,
                "quantity_sold": int(info["quantity"]) if info["quantity"] else 0,
                "revenue": round(float(info["revenue"]), 2) if info["revenue"] else 0,
            }
        )

    low_performers.sort(key=lambda x: x["revenue"])
    return low_performers[:limit]


def get_revenue_by_product(db: Session, business_id: int) -> List[Dict[str, Any]]:
    products = db.query(Product).filter(Product.business_id == business_id).all()
    product_ids = [p.id for p in products]
    if not product_ids:
        return []

    sales_data = (
        db.query(Sale.product_id, func.sum(Sale.total_amount).label("total_revenue"))
        .filter(Sale.product_id.in_(product_ids))
        .group_by(Sale.product_id)
        .all()
    )

    products_by_id = {p.id: p for p in products}
    revenue_data = []
    for s in sales_data:
        product = products_by_id.get(s.product_id)
        if product:
            revenue_data.append({"name": product.name, "revenue": round(float(s.total_revenue), 2)})

    revenue_data.sort(key=lambda x: x["revenue"], reverse=True)
    return revenue_data


def get_media_posts(db: Session, business_id: int) -> List[Dict[str, Any]]:
    posts = (
        db.query(MediaPost)
        .filter(MediaPost.business_id == business_id)
        .order_by(MediaPost.posted_at.desc())
        .all()
    )
    return [
        {
            "id": p.id,
            "post_type": p.post_type,
            "caption": p.caption,
            "posted_at": p.posted_at.strftime("%Y-%m-%d"),
            "impressions": p.impressions,
            "likes": p.likes,
            "comments": p.comments,
            "shares": p.shares,
            "engagement": p.likes + p.comments + p.shares,
        }
        for p in posts
    ]


def calculate_post_impact(db: Session, post: MediaPost, product_ids: List[int]) -> Dict[str, Any]:
    """
    Compares average daily revenue in the 7 days before a post to the 3
    days after it. This is the core "sales uplift" measurement used
    throughout the media-impact and recommendation features.
    """
    post_date = post.posted_at

    before_start = post_date - timedelta(days=7)
    before_end = post_date - timedelta(days=1)
    after_start = post_date
    after_end = post_date + timedelta(days=3)

    before_sales = (
        db.query(func.sum(Sale.total_amount))
        .filter(Sale.product_id.in_(product_ids), Sale.sale_date >= before_start, Sale.sale_date <= before_end)
        .scalar()
        or 0
    )
    after_sales = (
        db.query(func.sum(Sale.total_amount))
        .filter(Sale.product_id.in_(product_ids), Sale.sale_date >= after_start, Sale.sale_date <= after_end)
        .scalar()
        or 0
    )

    before_days = (before_end - before_start).days + 1
    after_days = (after_end - after_start).days + 1

    baseline_daily = before_sales / before_days if before_days > 0 else 0
    post_daily = after_sales / after_days if after_days > 0 else 0

    lift_percent = ((post_daily - baseline_daily) / baseline_daily * 100) if baseline_daily > 0 else 0
    incremental_revenue = (post_daily - baseline_daily) * after_days if baseline_daily > 0 else 0

    return {
        "baseline_daily": round(baseline_daily, 2),
        "post_daily": round(post_daily, 2),
        "lift_percent": round(lift_percent, 1),
        "incremental_revenue": round(max(0, incremental_revenue), 2),
    }


def get_media_impact_stats(db: Session, business_id: int) -> Dict[str, Any]:
    posts = db.query(MediaPost).filter(MediaPost.business_id == business_id).all()
    if not posts:
        return {
            "total_posts": 0,
            "total_reels": 0,
            "total_stories": 0,
            "avg_engagement": 0,
            "avg_lift": 0,
            "total_incremental_revenue": 0,
        }

    product_ids = _business_product_ids(db, business_id)

    total_reels = sum(1 for p in posts if p.post_type == "reel")
    total_stories = sum(1 for p in posts if p.post_type == "story")
    total_engagement = sum(p.likes + p.comments + p.shares for p in posts)
    avg_engagement = total_engagement / len(posts)

    total_lift = 0.0
    total_incremental = 0.0
    for post in posts:
        impact = calculate_post_impact(db, post, product_ids)
        total_lift += impact["lift_percent"]
        total_incremental += impact["incremental_revenue"]

    return {
        "total_posts": len(posts),
        "total_reels": total_reels,
        "total_stories": total_stories,
        "avg_engagement": round(avg_engagement, 1),
        "avg_lift": round(total_lift / len(posts), 1),
        "total_incremental_revenue": round(total_incremental, 2),
    }


def get_posts_with_impact(db: Session, business_id: int) -> List[Dict[str, Any]]:
    posts = (
        db.query(MediaPost)
        .filter(MediaPost.business_id == business_id)
        .order_by(MediaPost.posted_at.desc())
        .all()
    )
    if not posts:
        return []

    product_ids = _business_product_ids(db, business_id)

    result = []
    for post in posts:
        impact = calculate_post_impact(db, post, product_ids)
        result.append(
            {
                "id": post.id,
                "post_type": post.post_type,
                "caption": post.caption or "",
                "posted_at": post.posted_at.strftime("%Y-%m-%d"),
                "impressions": post.impressions,
                "likes": post.likes,
                "comments": post.comments,
                "shares": post.shares,
                "engagement": post.likes + post.comments + post.shares,
                **impact,
            }
        )
    return result


def get_media_type_comparison(db: Session, business_id: int) -> Dict[str, Any]:
    posts = db.query(MediaPost).filter(MediaPost.business_id == business_id).all()
    empty = {"count": 0, "avg_lift": 0, "avg_engagement": 0}
    if not posts:
        return {"reels": empty, "stories": empty}

    product_ids = _business_product_ids(db, business_id)

    def calc_avg(post_list):
        if not post_list:
            return dict(empty)
        total_lift = 0.0
        total_engagement = 0
        for post in post_list:
            impact = calculate_post_impact(db, post, product_ids)
            total_lift += impact["lift_percent"]
            total_engagement += post.likes + post.comments + post.shares
        return {
            "count": len(post_list),
            "avg_lift": round(total_lift / len(post_list), 1),
            "avg_engagement": round(total_engagement / len(post_list), 1),
        }

    return {
        "reels": calc_avg([p for p in posts if p.post_type == "reel"]),
        "stories": calc_avg([p for p in posts if p.post_type == "story"]),
    }


def get_revenue_with_posts_timeline(db: Session, business_id: int, days: int = 30) -> Dict[str, Any]:
    product_ids = _business_product_ids(db, business_id)

    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)

    sales = db.query(Sale).filter(Sale.product_id.in_(product_ids), Sale.sale_date >= start_date).all()
    posts = db.query(MediaPost).filter(MediaPost.business_id == business_id, MediaPost.posted_at >= start_date).all()

    daily_revenue = {}
    current = start_date
    while current <= end_date:
        daily_revenue[current.strftime("%Y-%m-%d")] = 0.0
        current += timedelta(days=1)

    for sale in sales:
        date_key = sale.sale_date.strftime("%Y-%m-%d")
        if date_key in daily_revenue:
            daily_revenue[date_key] += sale.total_amount

    revenue_data = [{"date": d, "revenue": round(r, 2)} for d, r in sorted(daily_revenue.items())]
    post_markers = [
        {"date": p.posted_at.strftime("%Y-%m-%d"), "type": p.post_type, "caption": p.caption or ""} for p in posts
    ]

    return {"revenue_data": revenue_data, "post_markers": post_markers}


def get_sales_by_day_hour(db: Session, business_id: int) -> Dict[str, Any]:
    """Aggregate sales by day of week and hour - used as ML feature-engineering input."""
    product_ids = _business_product_ids(db, business_id)
    if not product_ids:
        return {"by_day": [], "by_hour": []}

    sales = db.query(Sale).filter(Sale.product_id.in_(product_ids)).all()

    by_day = {day: {"revenue": 0.0, "count": 0} for day in DAY_NAMES}
    by_hour = {h: {"revenue": 0.0, "count": 0} for h in range(24)}

    for sale in sales:
        day_idx = sale.sale_date.weekday()
        by_day[DAY_NAMES[day_idx]]["revenue"] += sale.total_amount
        by_day[DAY_NAMES[day_idx]]["count"] += 1

        if sale.sale_time:
            hour = sale.sale_time.hour
            by_hour[hour]["revenue"] += sale.total_amount
            by_hour[hour]["count"] += 1

    return {
        "by_day": [{"day": d, "revenue": round(v["revenue"], 2), "orders": v["count"]} for d, v in by_day.items()],
        "by_hour": [
            {"hour": h, "revenue": round(v["revenue"], 2), "orders": v["count"]}
            for h, v in by_hour.items()
            if v["count"] > 0
        ],
    }


def get_rolling_revenue_averages(db: Session, business_id: int) -> Dict[str, Any]:
    product_ids = _business_product_ids(db, business_id)
    if not product_ids:
        return {"avg_3d": 0, "avg_7d": 0, "avg_30d": 0}

    today = datetime.now().date()

    def window_avg(days: int) -> float:
        total = (
            db.query(func.sum(Sale.total_amount))
            .filter(Sale.product_id.in_(product_ids), Sale.sale_date >= today - timedelta(days=days))
            .scalar()
            or 0
        )
        return round(total / days, 2) if total else 0

    return {"avg_3d": window_avg(3), "avg_7d": window_avg(7), "avg_30d": window_avg(30)}


def get_post_timing_analysis(db: Session, business_id: int) -> Dict[str, Any]:
    posts = db.query(MediaPost).filter(MediaPost.business_id == business_id).all()
    if not posts:
        return {"analysis": [], "best_time": None, "best_day": None}

    product_ids = _business_product_ids(db, business_id)

    analysis = []
    for post in posts:
        impact = calculate_post_impact(db, post, product_ids)

        time_bucket = "evening"
        if post.post_time:
            hour = post.post_time.hour
            if 6 <= hour < 12:
                time_bucket = "morning"
            elif 12 <= hour < 17:
                time_bucket = "afternoon"

        analysis.append(
            {
                "day": DAY_NAMES[post.posted_at.weekday()],
                "time_bucket": time_bucket,
                "post_type": post.post_type,
                "lift_percent": impact["lift_percent"],
            }
        )

    def group_avg(key: str):
        groups: Dict[str, List[float]] = {}
        for a in analysis:
            groups.setdefault(a[key], []).append(a["lift_percent"])
        return groups

    day_lifts = group_avg("day")
    time_lifts = group_avg("time_bucket")

    best_day = max(day_lifts.items(), key=lambda x: sum(x[1]) / len(x[1]))[0] if day_lifts else None
    best_time = max(time_lifts.items(), key=lambda x: sum(x[1]) / len(x[1]))[0] if time_lifts else None

    return {
        "analysis": analysis,
        "best_day": best_day,
        "best_time": best_time,
        "day_summary": {d: round(sum(l) / len(l), 1) for d, l in day_lifts.items()},
        "time_summary": {t: round(sum(l) / len(l), 1) for t, l in time_lifts.items()},
    }


def get_business_recommendations(db: Session, business_id: int) -> Dict[str, Any]:
    """Generate actionable business recommendations based on all available data."""
    product_ids = _business_product_ids(db, business_id)

    if not product_ids:
        return {
            "status": "new_business",
            "primary_action": "Add your products and start recording sales",
            "recommendations": [
                {
                    "type": "setup",
                    "priority": "high",
                    "title": "Add Your Products",
                    "description": "Start by adding your products with cost and selling prices to track profitability.",
                    "icon": "📦",
                },
                {
                    "type": "setup",
                    "priority": "high",
                    "title": "Record Your Sales",
                    "description": "Once products are added, record daily sales to get insights.",
                    "icon": "💰",
                },
                {
                    "type": "growth",
                    "priority": "medium",
                    "title": "Create Social Media Content",
                    "description": "Post reels and stories to attract more customers.",
                    "icon": "📱",
                },
            ],
            "health_score": 0,
            "focus_area": "Getting Started",
        }

    stats = get_dashboard_stats(db, business_id)
    thirty_days_ago = datetime.now().date() - timedelta(days=30)
    seven_days_ago = datetime.now().date() - timedelta(days=7)

    recent_sales = db.query(Sale).filter(Sale.product_id.in_(product_ids), Sale.sale_date >= thirty_days_ago).all()
    very_recent_sales = [s for s in recent_sales if s.sale_date >= seven_days_ago]
    older_sales = [s for s in recent_sales if s.sale_date < seven_days_ago]

    recent_revenue = sum(s.total_amount for s in very_recent_sales)
    older_revenue = sum(s.total_amount for s in older_sales)

    older_daily_avg = older_revenue / 23 if older_sales else 0
    recent_daily_avg = recent_revenue / 7 if very_recent_sales else 0

    growth_trend = (
        "growing"
        if recent_daily_avg > older_daily_avg * 1.1
        else ("declining" if recent_daily_avg < older_daily_avg * 0.9 else "stable")
    )

    media_posts = db.query(MediaPost).filter(MediaPost.business_id == business_id).all()
    recent_posts = [p for p in media_posts if p.posted_at >= seven_days_ago]

    recommendations = []
    focus_area = "Business Growth"
    health_score = 50

    if growth_trend == "declining":
        health_score -= 20
        focus_area = "Revenue Recovery"
        recommendations.append(
            {
                "type": "urgent",
                "priority": "high",
                "title": "Launch a Promotion",
                "description": "Sales are declining. Consider running a limited-time discount or special offer to boost revenue.",
                "icon": "🎯",
            }
        )
    elif growth_trend == "growing":
        health_score += 20
        recommendations.append(
            {
                "type": "growth",
                "priority": "medium",
                "title": "Scale What's Working",
                "description": "Your sales are growing! Identify your best-selling products and stock up.",
                "icon": "📈",
            }
        )

    low_performers = get_low_performing_products(db, business_id, 5)
    if low_performers and low_performers[0]["revenue"] == 0:
        recommendations.append(
            {
                "type": "action",
                "priority": "high",
                "title": "Review Underperforming Products",
                "description": f"'{low_performers[0]['name']}' has no recent sales. Consider discounting or discontinuing.",
                "icon": "⚠️",
            }
        )

    if not media_posts:
        recommendations.append(
            {
                "type": "growth",
                "priority": "high",
                "title": "Start Posting on Social Media",
                "description": "You have no media posts tracked. Reels and stories can significantly boost sales.",
                "icon": "📱",
            }
        )
    elif len(recent_posts) == 0:
        recommendations.append(
            {
                "type": "action",
                "priority": "high",
                "title": "Post a New Reel or Story",
                "description": "No posts in the last 7 days. Regular content keeps customers engaged.",
                "icon": "🎬",
            }
        )
    else:
        health_score += 10

    if media_posts:
        reels = [p for p in media_posts if p.post_type == "reel"]
        stories = [p for p in media_posts if p.post_type == "story"]

        if len(reels) < len(stories) * 0.5:
            recommendations.append(
                {
                    "type": "growth",
                    "priority": "medium",
                    "title": "Create More Reels",
                    "description": "Reels typically get more reach than stories. Try posting more reels.",
                    "icon": "🎥",
                }
            )
        elif len(stories) < len(reels) * 0.5:
            recommendations.append(
                {
                    "type": "growth",
                    "priority": "medium",
                    "title": "Post More Stories",
                    "description": "Stories keep your audience engaged daily. Try posting more frequently.",
                    "icon": "📸",
                }
            )

    best_day = get_best_day_of_week(db, business_id)
    if best_day["day"] != "N/A":
        recommendations.append(
            {
                "type": "insight",
                "priority": "low",
                "title": f"Focus on {best_day['day']}s",
                "description": f"Your best day is {best_day['day']} with ₹{best_day['revenue']:,.0f} revenue. Plan special offers for this day.",
                "icon": "📅",
            }
        )

    profitable = get_most_profitable_products(db, business_id, 1)
    if profitable:
        top_product = profitable[0]
        recommendations.append(
            {
                "type": "insight",
                "priority": "medium",
                "title": f"Promote '{top_product['name']}'",
                "description": f"Your most profitable product with {top_product['profit_margin']:.0f}% margin. Feature it prominently.",
                "icon": "⭐",
            }
        )
        health_score += 10

    if stats["total_products"] < 5:
        recommendations.append(
            {
                "type": "growth",
                "priority": "medium",
                "title": "Expand Your Product Line",
                "description": "You only have a few products. Adding more variety can attract different customers.",
                "icon": "🛍️",
            }
        )
    else:
        health_score += 10

    health_score = min(100, max(0, health_score))
    recommendations.sort(key=lambda x: {"high": 0, "medium": 1, "low": 2}.get(x["priority"], 3))
    primary_action = recommendations[0]["description"] if recommendations else "Keep up the great work!"

    return {
        "status": "active",
        "primary_action": primary_action,
        "recommendations": recommendations[:6],
        "health_score": health_score,
        "focus_area": focus_area,
        "growth_trend": growth_trend,
        "recent_daily_avg": round(recent_daily_avg, 2),
        "posts_this_week": len(recent_posts),
    }
