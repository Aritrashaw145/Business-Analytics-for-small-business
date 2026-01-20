from sqlalchemy.orm import Session
from models import Product, Sale, MediaPost
from datetime import datetime, timedelta, time
import random


def generate_demo_data(db: Session, business_id: int):
    existing_products = db.query(Product).filter(Product.business_id == business_id).first()
    if existing_products:
        return False
    
    products_data = [
        {"name": "Masala Chai Premium", "cost_price": 150, "selling_price": 299, "category": "Beverages"},
        {"name": "Filter Coffee Powder", "cost_price": 180, "selling_price": 349, "category": "Beverages"},
        {"name": "Multigrain Bread", "cost_price": 35, "selling_price": 75, "category": "Bakery"},
        {"name": "Butter Croissant", "cost_price": 45, "selling_price": 99, "category": "Bakery"},
        {"name": "Samosa (4pk)", "cost_price": 40, "selling_price": 99, "category": "Snacks"},
        {"name": "Pure Honey 500g", "cost_price": 250, "selling_price": 499, "category": "Pantry"},
        {"name": "Peanut Butter", "cost_price": 150, "selling_price": 299, "category": "Pantry"},
        {"name": "Muesli Mix", "cost_price": 180, "selling_price": 399, "category": "Breakfast"},
        {"name": "Fresh Nimbu Pani", "cost_price": 15, "selling_price": 49, "category": "Beverages"},
        {"name": "Protein Bar Pack", "cost_price": 200, "selling_price": 449, "category": "Snacks"},
        {"name": "Mango Lassi", "cost_price": 30, "selling_price": 79, "category": "Beverages"},
        {"name": "Paratha Pack (6)", "cost_price": 60, "selling_price": 149, "category": "Bakery"},
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
    
    media_posts_data = [
        {"type": "reel", "caption": "Our famous Masala Chai recipe revealed!", "days_ago": 85, "hour": 18, "day_target": 4},
        {"type": "story", "caption": "Fresh parathas just out of the tawa", "days_ago": 78, "hour": 10, "day_target": 6},
        {"type": "image", "caption": "Our cozy cafe corner - perfect for weekends", "days_ago": 72, "hour": 14, "day_target": 0},
        {"type": "reel", "caption": "Behind the scenes: Filter coffee preparation", "days_ago": 65, "hour": 19, "day_target": 5},
        {"type": "story", "caption": "Morning rush at our store!", "days_ago": 58, "hour": 9, "day_target": 1},
        {"type": "reel", "caption": "Customer review: Best samosas in town!", "days_ago": 50, "hour": 18, "day_target": 4},
        {"type": "image", "caption": "New honey collection just arrived", "days_ago": 45, "hour": 12, "day_target": 3},
        {"type": "story", "caption": "Flash sale - 20% off all snacks!", "days_ago": 40, "hour": 17, "day_target": 5},
        {"type": "reel", "caption": "How we make fresh Mango Lassi", "days_ago": 35, "hour": 19, "day_target": 5},
        {"type": "story", "caption": "Weekend special menu preview", "days_ago": 28, "hour": 11, "day_target": 6},
        {"type": "reel", "caption": "Our breakfast spread - Muesli & more!", "days_ago": 21, "hour": 18, "day_target": 4},
        {"type": "image", "caption": "Happy customers enjoying chai!", "days_ago": 14, "hour": 15, "day_target": 0},
        {"type": "story", "caption": "Thank you for 5000 followers!", "days_ago": 10, "hour": 20, "day_target": 5},
        {"type": "reel", "caption": "Evening snack time - Samosa party!", "days_ago": 7, "hour": 18, "day_target": 4},
        {"type": "reel", "caption": "New summer drinks menu launch", "days_ago": 3, "hour": 19, "day_target": 5},
    ]
    
    post_dates = set()
    for post_data in media_posts_data:
        post_date = end_date - timedelta(days=post_data["days_ago"])
        post_dates.add(post_date)
        for i in range(1, 4):
            post_dates.add(post_date + timedelta(days=i))
    
    for product in products:
        base_demand = random.uniform(0.5, 2.0)
        
        current_date = start_date
        while current_date <= end_date:
            if random.random() < 0.7:
                day_of_week = current_date.weekday()
                weekend_boost = 1.5 if day_of_week >= 5 else 1.0
                
                post_boost = 1.4 if current_date in post_dates else 1.0
                
                quantity = max(1, int(random.gauss(5 * base_demand * weekend_boost * post_boost, 2)))
                total_amount = quantity * product.selling_price
                
                sale_hour = random.choices(
                    [9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20],
                    weights=[5, 8, 10, 15, 12, 8, 10, 12, 15, 20, 18, 10],
                    k=1
                )[0]
                sale_minute = random.randint(0, 59)
                
                sale = Sale(
                    product_id=product.id,
                    quantity=quantity,
                    total_amount=total_amount,
                    sale_date=current_date,
                    sale_time=time(sale_hour, sale_minute)
                )
                db.add(sale)
            
            current_date += timedelta(days=1)
    
    db.commit()
    
    for post_data in media_posts_data:
        post_date = end_date - timedelta(days=post_data["days_ago"])
        
        post_type = post_data["type"]
        if post_type == "reel":
            base_impressions = random.randint(2000, 8000)
        elif post_type == "image":
            base_impressions = random.randint(500, 2000)
        else:
            base_impressions = random.randint(300, 1500)
        
        engagement_rate = random.uniform(0.05, 0.15)
        
        impressions = base_impressions
        likes = int(impressions * engagement_rate * random.uniform(0.6, 1.0))
        comments = int(impressions * engagement_rate * random.uniform(0.05, 0.15))
        shares = int(impressions * engagement_rate * random.uniform(0.02, 0.08)) if post_type == "reel" else random.randint(0, 5)
        
        post_hour = post_data.get("hour", random.randint(10, 20))
        post_minute = random.randint(0, 59)
        
        media_post = MediaPost(
            business_id=business_id,
            post_type=post_type,
            caption=post_data["caption"],
            posted_at=post_date,
            post_time=time(post_hour, post_minute),
            platform="instagram",
            impressions=impressions,
            likes=likes,
            comments=comments,
            shares=shares
        )
        db.add(media_post)
    
    db.commit()
    return True


def clear_demo_data(db: Session, business_id: int):
    products = db.query(Product).filter(Product.business_id == business_id).all()
    
    for product in products:
        db.query(Sale).filter(Sale.product_id == product.id).delete()
    
    db.query(Product).filter(Product.business_id == business_id).delete()
    db.query(MediaPost).filter(MediaPost.business_id == business_id).delete()
    db.commit()
