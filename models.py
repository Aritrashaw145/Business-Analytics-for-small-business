from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Date, Time
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, time
import os

DATABASE_URL = os.environ.get("DATABASE_URL") or "sqlite:///business_analytics.db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Business(Base):
    __tablename__ = "businesses"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    owner_name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    category = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    products = relationship("Product", back_populates="business", cascade="all, delete-orphan")
    media_posts = relationship("MediaPost", back_populates="business", cascade="all, delete-orphan")


class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    name = Column(String(255), nullable=False)
    cost_price = Column(Float, nullable=False)
    selling_price = Column(Float, nullable=False)
    category = Column(String(100))
    
    business = relationship("Business", back_populates="products")
    sales = relationship("Sale", back_populates="product", cascade="all, delete-orphan")


class Sale(Base):
    __tablename__ = "sales"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    total_amount = Column(Float, nullable=False)
    sale_date = Column(Date, nullable=False)
    sale_time = Column(Time, nullable=True)  # Optional: time of sale for granular analysis
    
    product = relationship("Product", back_populates="sales")


class MediaPost(Base):
    __tablename__ = "media_posts"
    
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    post_type = Column(String(20), nullable=False)  # 'reel', 'story', or 'image'
    caption = Column(String(500))
    posted_at = Column(Date, nullable=False)
    post_time = Column(Time, nullable=True)  # Time of posting for ML recommendations
    platform = Column(String(50), default="instagram")  # Platform (instagram, facebook, etc.)
    impressions = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    
    business = relationship("Business", back_populates="media_posts")


def init_db():
    Base.metadata.create_all(bind=engine)
    
    run_migrations()


def run_migrations():
    """Run database migrations to add new columns if they don't exist"""
    from sqlalchemy import text, inspect
    
    inspector = inspect(engine)
    
    with engine.connect() as conn:
        media_post_columns = [col['name'] for col in inspector.get_columns('media_posts')]
        if 'post_time' not in media_post_columns:
            try:
                if 'sqlite' in str(engine.url):
                    conn.execute(text("ALTER TABLE media_posts ADD COLUMN post_time TEXT"))
                else:
                    conn.execute(text("ALTER TABLE media_posts ADD COLUMN IF NOT EXISTS post_time TIME"))
                conn.commit()
            except Exception:
                pass
        
        if 'platform' not in media_post_columns:
            try:
                if 'sqlite' in str(engine.url):
                    conn.execute(text("ALTER TABLE media_posts ADD COLUMN platform TEXT DEFAULT 'instagram'"))
                else:
                    conn.execute(text("ALTER TABLE media_posts ADD COLUMN IF NOT EXISTS platform VARCHAR(50) DEFAULT 'instagram'"))
                conn.commit()
            except Exception:
                pass
        
        sales_columns = [col['name'] for col in inspector.get_columns('sales')]
        if 'sale_time' not in sales_columns:
            try:
                if 'sqlite' in str(engine.url):
                    conn.execute(text("ALTER TABLE sales ADD COLUMN sale_time TEXT"))
                else:
                    conn.execute(text("ALTER TABLE sales ADD COLUMN IF NOT EXISTS sale_time TIME"))
                conn.commit()
            except Exception:
                pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
