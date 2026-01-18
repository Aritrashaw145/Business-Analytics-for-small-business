from sqlalchemy.orm import Session
from models import Product, Sale
from datetime import datetime, timedelta
import random


def generate_demo_data(db: Session, business_id: int):
    existing_products = db.query(Product).filter(Product.business_id == business_id).first()
    if existing_products:
        return False
    
    products_data = [
        {"name": "Organic Coffee Beans", "cost_price": 8.50, "selling_price": 15.99, "category": "Beverages"},
        {"name": "Green Tea Premium", "cost_price": 4.00, "selling_price": 9.99, "category": "Beverages"},
        {"name": "Artisan Bread", "cost_price": 2.50, "selling_price": 6.99, "category": "Bakery"},
        {"name": "Chocolate Croissant", "cost_price": 1.80, "selling_price": 4.50, "category": "Bakery"},
        {"name": "Fresh Muffins (6pk)", "cost_price": 3.00, "selling_price": 8.99, "category": "Bakery"},
        {"name": "Organic Honey", "cost_price": 6.00, "selling_price": 14.99, "category": "Pantry"},
        {"name": "Almond Butter", "cost_price": 5.50, "selling_price": 12.99, "category": "Pantry"},
        {"name": "Granola Mix", "cost_price": 3.50, "selling_price": 9.49, "category": "Breakfast"},
        {"name": "Fresh Juice", "cost_price": 2.00, "selling_price": 5.99, "category": "Beverages"},
        {"name": "Protein Bars (4pk)", "cost_price": 4.00, "selling_price": 10.99, "category": "Snacks"},
        {"name": "Fruit Smoothie", "cost_price": 2.50, "selling_price": 6.49, "category": "Beverages"},
        {"name": "Bagel Pack", "cost_price": 2.00, "selling_price": 5.99, "category": "Bakery"},
    ]
    
    products = []
    for p_data in products_data:
        product = Product(
            business_id=business_id,
            name=p_data["name"],
            cost_price=p_data["cost_price"],
            selling_price=p_data["selling_price"],
            category=p_data["category"]
        )
        db.add(product)
        products.append(product)
    
    db.commit()
    
    for product in products:
        db.refresh(product)
    
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=90)
    
    for product in products:
        base_demand = random.uniform(0.5, 2.0)
        
        current_date = start_date
        while current_date <= end_date:
            if random.random() < 0.7:
                day_of_week = current_date.weekday()
                weekend_boost = 1.5 if day_of_week >= 5 else 1.0
                
                quantity = max(1, int(random.gauss(5 * base_demand * weekend_boost, 2)))
                total_amount = quantity * product.selling_price
                
                sale = Sale(
                    product_id=product.id,
                    quantity=quantity,
                    total_amount=total_amount,
                    sale_date=current_date
                )
                db.add(sale)
            
            current_date += timedelta(days=1)
    
    db.commit()
    return True


def clear_demo_data(db: Session, business_id: int):
    products = db.query(Product).filter(Product.business_id == business_id).all()
    
    for product in products:
        db.query(Sale).filter(Sale.product_id == product.id).delete()
    
    db.query(Product).filter(Product.business_id == business_id).delete()
    db.commit()
