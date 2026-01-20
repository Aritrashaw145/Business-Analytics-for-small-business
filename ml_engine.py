import pickle
import os
from datetime import datetime, timedelta, time
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import func

from models import Product, Sale, MediaPost

MODEL_PATH = "post_impact_model.pkl"


def get_sales_features(db: Session, business_id: int) -> pd.DataFrame:
    """Extract and engineer features from sales and posts data"""
    products = db.query(Product).filter(Product.business_id == business_id).all()
    product_ids = [p.id for p in products]
    
    if not product_ids:
        return pd.DataFrame()
    
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=180)
    
    sales = db.query(Sale).filter(
        Sale.product_id.in_(product_ids),
        Sale.sale_date >= start_date
    ).all()
    
    posts = db.query(MediaPost).filter(
        MediaPost.business_id == business_id,
        MediaPost.posted_at >= start_date
    ).all()
    
    if not sales:
        return pd.DataFrame()
    
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
            if post.post_type == "reel":
                daily_data[post_date]["post_type_reel"] = 1
            elif post.post_type == "story":
                daily_data[post_date]["post_type_story"] = 1
            elif post.post_type == "image":
                daily_data[post_date]["post_type_image"] = 1
            
            if post.post_time:
                daily_data[post_date]["post_hour"] = post.post_time.hour
    
    df = pd.DataFrame(list(daily_data.values()))
    df = df.sort_values("date").reset_index(drop=True)
    
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
    
    df = df.dropna()
    
    return df


def calculate_post_impact_by_slot(db: Session, business_id: int) -> Dict[str, Any]:
    """Calculate average sales uplift for different posting slots (day/time/type)"""
    products = db.query(Product).filter(Product.business_id == business_id).all()
    product_ids = [p.id for p in products]
    
    if not product_ids:
        return {"slots": [], "baseline": 0}
    
    posts = db.query(MediaPost).filter(MediaPost.business_id == business_id).all()
    
    if len(posts) < 3:
        return {"slots": [], "baseline": 0, "error": "Need at least 3 posts for analysis"}
    
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=180)
    
    sales = db.query(Sale).filter(
        Sale.product_id.in_(product_ids),
        Sale.sale_date >= start_date
    ).all()
    
    if not sales:
        return {"slots": [], "baseline": 0}
    
    daily_sales = {}
    for sale in sales:
        date_key = sale.sale_date
        if date_key not in daily_sales:
            daily_sales[date_key] = 0
        daily_sales[date_key] += sale.total_amount
    
    baseline_revenues = list(daily_sales.values())
    baseline_daily = np.mean(baseline_revenues) if baseline_revenues else 0
    
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
            if hour < 12:
                hour_bucket = "morning"
            elif hour < 17:
                hour_bucket = "afternoon"
            else:
                hour_bucket = "evening"
        
        slot_impacts.append({
            "day_of_week": post_date.weekday(),
            "day_name": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][post_date.weekday()],
            "time_bucket": hour_bucket,
            "post_type": post.post_type,
            "lift_percent": lift_percent,
            "post_daily": after_daily,
            "baseline_daily": before_daily
        })
    
    return {
        "slots": slot_impacts,
        "baseline": baseline_daily
    }


def train_post_impact_model(db: Session, business_id: int) -> Dict[str, Any]:
    """Train a tree-based model to predict sales based on posting patterns"""
    try:
        from sklearn.ensemble import GradientBoostingRegressor
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import mean_absolute_error, r2_score
    except ImportError:
        return {"success": False, "error": "scikit-learn not installed"}
    
    df = get_sales_features(db, business_id)
    
    if df.empty or len(df) < 30:
        return {"success": False, "error": "Insufficient data. Need at least 30 days of sales."}
    
    feature_cols = [
        "day_of_week", "is_weekend",
        "revenue_3d_avg", "revenue_7d_avg",
        "orders_3d_avg", "orders_7d_avg",
        "had_post", "had_post_yesterday", "had_post_2days", "had_post_3days",
        "post_type_reel", "post_type_story", "post_type_image",
        "dow_0", "dow_1", "dow_2", "dow_3", "dow_4", "dow_5", "dow_6"
    ]
    
    available_cols = [col for col in feature_cols if col in df.columns]
    
    X = df[available_cols]
    y = df["revenue"]
    
    if len(X) < 30:
        return {"success": False, "error": "Not enough data for training"}
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    model = GradientBoostingRegressor(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        random_state=42
    )
    model.fit(X_train, y_train)
    
    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    
    feature_importance = dict(zip(available_cols, model.feature_importances_))
    
    model_data = {
        "model": model,
        "features": available_cols,
        "business_id": business_id,
        "trained_at": datetime.now().isoformat(),
        "metrics": {"mae": mae, "r2": r2},
        "feature_importance": feature_importance,
        "baseline_revenue": float(df["revenue"].mean())
    }
    
    model_file = f"post_impact_model_{business_id}.pkl"
    with open(model_file, 'wb') as f:
        pickle.dump(model_data, f)
    
    return {
        "success": True,
        "mae": round(mae, 2),
        "r2": round(r2, 3),
        "data_points": len(df),
        "feature_importance": {k: round(v, 4) for k, v in sorted(feature_importance.items(), key=lambda x: -x[1])[:5]}
    }


def load_model(business_id: int) -> Optional[Dict[str, Any]]:
    """Load the trained model for a business"""
    model_file = f"post_impact_model_{business_id}.pkl"
    if os.path.exists(model_file):
        with open(model_file, 'rb') as f:
            return pickle.load(f)
    return None


def predict_revenue_for_scenario(
    model_data: Dict[str, Any],
    day_of_week: int,
    post_type: str,
    had_post: bool,
    recent_revenue_avg: float
) -> float:
    """Predict expected revenue for a specific posting scenario"""
    model = model_data["model"]
    features = model_data["features"]
    
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


def get_best_posting_recommendation(db: Session, business_id: int) -> Dict[str, Any]:
    """Get the best day/time/type recommendation for posting based on expected sales uplift"""
    
    model_data = load_model(business_id)
    
    products = db.query(Product).filter(Product.business_id == business_id).all()
    product_ids = [p.id for p in products]
    
    if not product_ids:
        return {"error": "No products found", "recommendations": []}
    
    seven_days_ago = datetime.now().date() - timedelta(days=7)
    recent_sales = db.query(func.avg(Sale.total_amount)).filter(
        Sale.product_id.in_(product_ids),
        Sale.sale_date >= seven_days_ago
    ).scalar() or 0
    
    recent_revenue_avg = float(recent_sales) * 5
    
    slot_analysis = calculate_post_impact_by_slot(db, business_id)
    
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    post_types = ["reel", "story", "image"]
    time_buckets = ["morning", "afternoon", "evening"]
    
    scenarios = []
    
    if model_data:
        baseline_revenue = model_data.get("baseline_revenue", recent_revenue_avg)
        
        for day_idx, day_name in enumerate(day_names):
            for post_type in post_types:
                predicted_with_post = predict_revenue_for_scenario(
                    model_data, day_idx, post_type, True, recent_revenue_avg
                )
                predicted_without_post = predict_revenue_for_scenario(
                    model_data, day_idx, post_type, False, recent_revenue_avg
                )
                
                uplift = predicted_with_post - predicted_without_post
                uplift_percent = (uplift / predicted_without_post * 100) if predicted_without_post > 0 else 0
                
                scenarios.append({
                    "day": day_name,
                    "day_of_week": day_idx,
                    "post_type": post_type,
                    "time_bucket": "evening",
                    "expected_revenue": round(predicted_with_post, 2),
                    "expected_uplift": round(uplift, 2),
                    "uplift_percent": round(uplift_percent, 1),
                    "confidence": "high" if model_data["metrics"]["r2"] > 0.5 else "medium"
                })
    else:
        if slot_analysis.get("slots"):
            slots = slot_analysis["slots"]
            
            day_type_avg = {}
            for slot in slots:
                key = (slot["day_of_week"], slot["post_type"])
                if key not in day_type_avg:
                    day_type_avg[key] = {"lifts": [], "day_name": slot["day_name"]}
                day_type_avg[key]["lifts"].append(slot["lift_percent"])
            
            for (day_idx, post_type), data in day_type_avg.items():
                avg_lift = np.mean(data["lifts"])
                scenarios.append({
                    "day": data["day_name"],
                    "day_of_week": day_idx,
                    "post_type": post_type,
                    "time_bucket": "evening",
                    "expected_revenue": round(slot_analysis["baseline"] * (1 + avg_lift/100), 2),
                    "expected_uplift": round(slot_analysis["baseline"] * avg_lift/100, 2),
                    "uplift_percent": round(avg_lift, 1),
                    "confidence": "low"
                })
    
    if not scenarios:
        return {
            "error": "Insufficient data for recommendations",
            "recommendations": [],
            "message": "Add more posts and sales data to get personalized recommendations"
        }
    
    scenarios.sort(key=lambda x: x["uplift_percent"], reverse=True)
    
    best = scenarios[0]
    
    best_day = max(
        [(d, sum(s["uplift_percent"] for s in scenarios if s["day"] == d))
         for d in day_names],
        key=lambda x: x[1]
    )[0]
    
    best_type = max(
        [(t, sum(s["uplift_percent"] for s in scenarios if s["post_type"] == t))
         for t in post_types],
        key=lambda x: x[1]
    )[0]
    
    return {
        "best_overall": {
            "day": best["day"],
            "time": "Evening (6-9 PM)",
            "post_type": best["post_type"],
            "expected_uplift_percent": best["uplift_percent"],
            "expected_revenue": best["expected_revenue"],
            "confidence": best["confidence"]
        },
        "best_day": best_day,
        "best_post_type": best_type,
        "best_time": "Evening",
        "top_5_scenarios": scenarios[:5],
        "model_available": model_data is not None,
        "data_based": len(slot_analysis.get("slots", [])) > 0,
        "message": f"Posting a {best['post_type']} on {best['day']} evening could increase your sales by ~{best['uplift_percent']:.0f}%"
    }


def get_posting_insights(db: Session, business_id: int) -> Dict[str, Any]:
    """Get detailed posting insights and patterns"""
    
    slot_analysis = calculate_post_impact_by_slot(db, business_id)
    
    if not slot_analysis.get("slots"):
        return {
            "has_data": False,
            "message": "Add media posts and sales to see posting insights"
        }
    
    slots = slot_analysis["slots"]
    
    day_performance = {}
    type_performance = {}
    time_performance = {}
    
    for slot in slots:
        day = slot["day_name"]
        ptype = slot["post_type"]
        time_b = slot.get("time_bucket", "unknown")
        lift = slot["lift_percent"]
        
        if day not in day_performance:
            day_performance[day] = []
        day_performance[day].append(lift)
        
        if ptype not in type_performance:
            type_performance[ptype] = []
        type_performance[ptype].append(lift)
        
        if time_b not in time_performance:
            time_performance[time_b] = []
        time_performance[time_b].append(lift)
    
    day_avg = {d: np.mean(lifts) for d, lifts in day_performance.items()}
    type_avg = {t: np.mean(lifts) for t, lifts in type_performance.items()}
    time_avg = {t: np.mean(lifts) for t, lifts in time_performance.items()}
    
    return {
        "has_data": True,
        "total_posts_analyzed": len(slots),
        "baseline_daily_revenue": round(slot_analysis["baseline"], 2),
        "day_performance": [
            {"day": d, "avg_lift": round(l, 1), "post_count": len(day_performance[d])}
            for d, l in sorted(day_avg.items(), key=lambda x: -x[1])
        ],
        "type_performance": [
            {"type": t, "avg_lift": round(l, 1), "post_count": len(type_performance[t])}
            for t, l in sorted(type_avg.items(), key=lambda x: -x[1])
        ],
        "time_performance": [
            {"time": t, "avg_lift": round(l, 1), "post_count": len(time_performance[t])}
            for t, l in sorted(time_avg.items(), key=lambda x: -x[1])
        ]
    }
