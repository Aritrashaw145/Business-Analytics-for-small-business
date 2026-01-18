from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

DATABASE_URL = os.environ.get("DATABASE_URL")

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
    
    product = relationship("Product", back_populates="sales")


class MediaPost(Base):
    __tablename__ = "media_posts"
    
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    post_type = Column(String(20), nullable=False)  # 'reel' or 'story'
    caption = Column(String(500))
    posted_at = Column(Date, nullable=False)
    impressions = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    
    business = relationship("Business", back_populates="media_posts")


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
