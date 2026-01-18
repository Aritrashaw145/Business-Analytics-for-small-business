from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from models import Product, Sale, Business
from datetime import datetime, timedelta
from typing import List, Dict, Any
import pandas as pd


def get_dashboard_stats(db: Session, business_id: int) -> Dict[str, Any]:
    products = db.query(Product).filter(Product.business_id == business_id).all()
    product_ids = [p.id for p in products]
    
    if not product_ids:
        return {
            "total_revenue": 0,
            "total_profit": 0,
            "total_orders": 0,
            "total_products": 0
        }
    
    sales = db.query(Sale).filter(Sale.product_id.in_(product_ids)).all()
    
    total_revenue = sum(s.total_amount for s in sales)
    total_orders = len(sales)
    
    total_profit = 0
    for sale in sales:
        product = next((p for p in products if p.id == sale.product_id), None)
        if product:
            profit_per_unit = product.selling_price - product.cost_price
            total_profit += profit_per_unit * sale.quantity
    
    return {
        "total_revenue": round(total_revenue, 2),
        "total_profit": round(total_profit, 2),
        "total_orders": total_orders,
        "total_products": len(products)
    }


def get_best_selling_products(db: Session, business_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    products = db.query(Product).filter(Product.business_id == business_id).all()
    product_ids = [p.id for p in products]
    
    if not product_ids:
        return []
    
    result = db.query(
        Sale.product_id,
        func.sum(Sale.quantity).label('total_quantity'),
        func.sum(Sale.total_amount).label('total_revenue')
    ).filter(
        Sale.product_id.in_(product_ids)
    ).group_by(Sale.product_id).order_by(
        func.sum(Sale.quantity).desc()
    ).limit(limit).all()
    
    best_products = []
    for r in result:
        product = next((p for p in products if p.id == r.product_id), None)
        if product:
            best_products.append({
                "name": product.name,
                "category": product.category,
                "quantity_sold": int(r.total_quantity),
                "revenue": round(float(r.total_revenue), 2)
            })
    
    return best_products


def get_most_profitable_products(db: Session, business_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    products = db.query(Product).filter(Product.business_id == business_id).all()
    product_ids = [p.id for p in products]
    
    if not product_ids:
        return []
    
    sales_data = db.query(
        Sale.product_id,
        func.sum(Sale.quantity).label('total_quantity'),
        func.sum(Sale.total_amount).label('total_revenue')
    ).filter(
        Sale.product_id.in_(product_ids)
    ).group_by(Sale.product_id).all()
    
    profitable_products = []
    for s in sales_data:
        product = next((p for p in products if p.id == s.product_id), None)
        if product:
            profit_per_unit = product.selling_price - product.cost_price
            total_profit = profit_per_unit * s.total_quantity
            profitable_products.append({
                "name": product.name,
                "category": product.category,
                "profit": round(total_profit, 2),
                "profit_margin": round((profit_per_unit / product.selling_price) * 100, 1) if product.selling_price > 0 else 0
            })
    
    profitable_products.sort(key=lambda x: x["profit"], reverse=True)
    return profitable_products[:limit]


def get_best_day_of_week(db: Session, business_id: int) -> Dict[str, Any]:
    products = db.query(Product).filter(Product.business_id == business_id).all()
    product_ids = [p.id for p in products]
    
    if not product_ids:
        return {"day": "N/A", "revenue": 0, "daily_breakdown": []}
    
    sales = db.query(Sale).filter(Sale.product_id.in_(product_ids)).all()
    
    if not sales:
        return {"day": "N/A", "revenue": 0, "daily_breakdown": []}
    
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    daily_revenue = {day: 0 for day in day_names}
    
    for sale in sales:
        day_index = sale.sale_date.weekday()
        daily_revenue[day_names[day_index]] += sale.total_amount
    
    best_day = max(daily_revenue, key=daily_revenue.get)
    daily_breakdown = [{"day": day, "revenue": round(rev, 2)} for day, rev in daily_revenue.items()]
    
    return {
        "day": best_day,
        "revenue": round(daily_revenue[best_day], 2),
        "daily_breakdown": daily_breakdown
    }


def get_weekly_trends(db: Session, business_id: int, weeks: int = 8) -> List[Dict[str, Any]]:
    products = db.query(Product).filter(Product.business_id == business_id).all()
    product_ids = [p.id for p in products]
    
    if not product_ids:
        return []
    
    end_date = datetime.now().date()
    start_date = end_date - timedelta(weeks=weeks)
    
    sales = db.query(Sale).filter(
        Sale.product_id.in_(product_ids),
        Sale.sale_date >= start_date
    ).all()
    
    weekly_data = {}
    for sale in sales:
        week_start = sale.sale_date - timedelta(days=sale.sale_date.weekday())
        week_key = week_start.strftime("%Y-%m-%d")
        
        if week_key not in weekly_data:
            weekly_data[week_key] = {"revenue": 0, "orders": 0}
        
        weekly_data[week_key]["revenue"] += sale.total_amount
        weekly_data[week_key]["orders"] += 1
    
    trends = [
        {
            "week": week,
            "revenue": round(data["revenue"], 2),
            "orders": data["orders"]
        }
        for week, data in sorted(weekly_data.items())
    ]
    
    return trends


def get_monthly_trends(db: Session, business_id: int, months: int = 6) -> List[Dict[str, Any]]:
    products = db.query(Product).filter(Product.business_id == business_id).all()
    product_ids = [p.id for p in products]
    
    if not product_ids:
        return []
    
    sales = db.query(Sale).filter(Sale.product_id.in_(product_ids)).all()
    
    monthly_data = {}
    for sale in sales:
        month_key = sale.sale_date.strftime("%Y-%m")
        
        if month_key not in monthly_data:
            monthly_data[month_key] = {"revenue": 0, "orders": 0}
        
        monthly_data[month_key]["revenue"] += sale.total_amount
        monthly_data[month_key]["orders"] += 1
    
    trends = [
        {
            "month": month,
            "revenue": round(data["revenue"], 2),
            "orders": data["orders"]
        }
        for month, data in sorted(monthly_data.items())
    ][-months:]
    
    return trends


def get_low_performing_products(db: Session, business_id: int, days: int = 30, limit: int = 10) -> List[Dict[str, Any]]:
    products = db.query(Product).filter(Product.business_id == business_id).all()
    product_ids = [p.id for p in products]
    
    if not product_ids:
        return []
    
    cutoff_date = datetime.now().date() - timedelta(days=days)
    
    sales_data = db.query(
        Sale.product_id,
        func.sum(Sale.quantity).label('total_quantity'),
        func.sum(Sale.total_amount).label('total_revenue')
    ).filter(
        Sale.product_id.in_(product_ids),
        Sale.sale_date >= cutoff_date
    ).group_by(Sale.product_id).all()
    
    sales_by_product = {s.product_id: {"quantity": s.total_quantity, "revenue": s.total_revenue} for s in sales_data}
    
    low_performers = []
    for product in products:
        sales_info = sales_by_product.get(product.id, {"quantity": 0, "revenue": 0})
        low_performers.append({
            "name": product.name,
            "category": product.category,
            "quantity_sold": int(sales_info["quantity"]) if sales_info["quantity"] else 0,
            "revenue": round(float(sales_info["revenue"]), 2) if sales_info["revenue"] else 0
        })
    
    low_performers.sort(key=lambda x: x["revenue"])
    return low_performers[:limit]


def get_revenue_by_product(db: Session, business_id: int) -> List[Dict[str, Any]]:
    products = db.query(Product).filter(Product.business_id == business_id).all()
    product_ids = [p.id for p in products]
    
    if not product_ids:
        return []
    
    sales_data = db.query(
        Sale.product_id,
        func.sum(Sale.total_amount).label('total_revenue')
    ).filter(
        Sale.product_id.in_(product_ids)
    ).group_by(Sale.product_id).all()
    
    revenue_data = []
    for s in sales_data:
        product = next((p for p in products if p.id == s.product_id), None)
        if product:
            revenue_data.append({
                "name": product.name,
                "revenue": round(float(s.total_revenue), 2)
            })
    
    revenue_data.sort(key=lambda x: x["revenue"], reverse=True)
    return revenue_data
