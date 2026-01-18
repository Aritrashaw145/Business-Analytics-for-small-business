from sqlalchemy.orm import Session
from models import Product, Sale, MediaPost
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
    
    media_posts_data = [
        {"type": "reel", "caption": "Check out our new coffee brewing technique!", "days_ago": 85},
        {"type": "story", "caption": "Fresh croissants just out of the oven", "days_ago": 78},
        {"type": "reel", "caption": "Behind the scenes: How we source our organic beans", "days_ago": 70},
        {"type": "story", "caption": "Morning rush hour vibes", "days_ago": 63},
        {"type": "reel", "caption": "Customer testimonial: Best coffee in town!", "days_ago": 55},
        {"type": "story", "caption": "New almond butter flavor dropping tomorrow", "days_ago": 48},
        {"type": "reel", "caption": "Recipe: Perfect breakfast with our granola", "days_ago": 40},
        {"type": "story", "caption": "Flash sale - 20% off all bakery items", "days_ago": 35},
        {"type": "reel", "caption": "Meet our barista team", "days_ago": 28},
        {"type": "story", "caption": "Weekend special menu preview", "days_ago": 21},
        {"type": "reel", "caption": "How we make our fresh juice daily", "days_ago": 14},
        {"type": "story", "caption": "Thank you for 1000 followers!", "days_ago": 7},
        {"type": "reel", "caption": "New smoothie flavors for summer", "days_ago": 3},
    ]
    
    for post_data in media_posts_data:
        post_date = end_date - timedelta(days=post_data["days_ago"])
        
        is_reel = post_data["type"] == "reel"
        base_impressions = random.randint(800, 5000) if is_reel else random.randint(200, 1500)
        engagement_rate = random.uniform(0.05, 0.15)
        
        impressions = base_impressions
        likes = int(impressions * engagement_rate * random.uniform(0.6, 1.0))
        comments = int(impressions * engagement_rate * random.uniform(0.05, 0.15))
        shares = int(impressions * engagement_rate * random.uniform(0.02, 0.08)) if is_reel else 0
        
        media_post = MediaPost(
            business_id=business_id,
            post_type=post_data["type"],
            caption=post_data["caption"],
            posted_at=post_date,
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
