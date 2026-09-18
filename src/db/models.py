"""
SQLAlchemy ORM models.

Tables
------
Business        - a signed-up business account (tenant)
Product         - a product belonging to a business
Sale            - a recorded sale of a product
MediaPost       - a tracked social media post belonging to a business
ModelRun        - metadata for a single ML training run (audit trail)
PredictionLog   - a logged prediction used later for the feedback loop

All business-owned tables carry `business_id` so every query can (and must)
be scoped to the authenticated tenant. See `src.core.analytics` and
`src.ml` for the query helpers that enforce this scoping.
"""
from __future__ import annotations

from datetime import datetime, date as date_type

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Date,
    Time,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Business(Base):
    __tablename__ = "businesses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    owner_name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    category = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)

    products = relationship("Product", back_populates="business", cascade="all, delete-orphan")
    media_posts = relationship("MediaPost", back_populates="business", cascade="all, delete-orphan")
    model_runs = relationship("ModelRun", back_populates="business", cascade="all, delete-orphan")
    prediction_logs = relationship("PredictionLog", back_populates="business", cascade="all, delete-orphan")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    cost_price = Column(Float, nullable=False)
    selling_price = Column(Float, nullable=False)
    category = Column(String(100))

    business = relationship("Business", back_populates="products")
    sales = relationship("Sale", back_populates="product", cascade="all, delete-orphan")


class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    total_amount = Column(Float, nullable=False)
    sale_date = Column(Date, nullable=False, index=True)
    sale_time = Column(Time, nullable=True)

    product = relationship("Product", back_populates="sales")


class MediaPost(Base):
    __tablename__ = "media_posts"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False, index=True)
    post_type = Column(String(20), nullable=False)  # 'reel', 'story', or 'image'
    caption = Column(String(500))
    posted_at = Column(Date, nullable=False, index=True)
    post_time = Column(Time, nullable=True)
    platform = Column(String(50), default="instagram")
    impressions = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)

    business = relationship("Business", back_populates="media_posts")


class ModelRun(Base):
    """
    Audit record for one ML training run. Persisted independently of the
    pickled model file so training status/date/performance can be shown in
    the UI without unpickling scikit-learn objects, and so past runs are
    never silently overwritten.
    """
    __tablename__ = "model_runs"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False, index=True)
    trained_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(String(20), nullable=False)  # 'trained' | 'insufficient_data' | 'failed'
    data_points = Column(Integer, default=0)
    sales_days_count = Column(Integer, default=0)
    posts_count = Column(Integer, default=0)
    mae = Column(Float, nullable=True)
    r2 = Column(Float, nullable=True)
    feature_importance_json = Column(Text, nullable=True)
    data_quality_notes_json = Column(Text, nullable=True)
    model_file_path = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=False)  # the model currently used for predictions

    business = relationship("Business", back_populates="model_runs")


class PredictionLog(Base):
    """
    A prediction the app made (e.g. "post a reel on Friday evening"),
    logged so its outcome can later be compared against real sales.
    This is the feedback loop's raw material: it is read for accuracy
    reporting only and is never used as a training feature, so a bad
    prediction cannot bias future training runs.
    """
    __tablename__ = "prediction_logs"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    model_run_id = Column(Integer, ForeignKey("model_runs.id"), nullable=True)

    target_date = Column(Date, nullable=False)  # the date the scenario is about
    day_of_week = Column(Integer, nullable=False)
    post_type = Column(String(20), nullable=False)
    predicted_daily_revenue = Column(Float, nullable=False)
    predicted_uplift_percent = Column(Float, nullable=False)
    confidence = Column(String(10), nullable=False)  # 'low' | 'medium' | 'high'

    status = Column(String(20), default="pending", nullable=False)  # pending|evaluated
    actual_daily_revenue = Column(Float, nullable=True)
    actual_uplift_percent = Column(Float, nullable=True)
    absolute_error = Column(Float, nullable=True)
    evaluated_at = Column(DateTime, nullable=True)

    business = relationship("Business", back_populates="prediction_logs")
