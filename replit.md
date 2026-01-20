# Business Analytics Dashboard

## Overview
A full-stack data analytics application for small businesses, similar to Instagram Insights. Business owners can manage their products and sales data to receive actionable insights including best-selling products, profit analysis, daily performance, sales trends, and ML-powered post recommendations based on sales impact.

## Tech Stack
- **Frontend**: Streamlit (Python)
- **Database**: PostgreSQL (with SQLite fallback for local development)
- **ORM**: SQLAlchemy
- **Charts**: Plotly
- **ML**: scikit-learn (GradientBoostingRegressor for sales prediction)
- **Authentication**: bcrypt password hashing with session-based auth

## Project Structure
```
├── app.py           # Main Streamlit application with all UI screens
├── models.py        # Database models (Business, Product, Sale, MediaPost)
├── auth.py          # Authentication logic (login, signup, password hashing)
├── analytics.py     # Analytics functions (best products, trends, etc.)
├── ml_engine.py     # ML-based post recommendation engine
├── demo_data.py     # Demo data generation utilities
├── .streamlit/      # Streamlit configuration
│   └── config.toml
```

## Database Schema

### Business
- id, name, owner_name, email, password_hash, category, created_at

### Product
- id, business_id (FK), name, cost_price, selling_price, category

### Sale
- id, product_id (FK), quantity, total_amount, sale_date, sale_time (optional)

### MediaPost
- id, business_id (FK), post_type (reel/story/image), caption, posted_at, post_time, platform, impressions, likes, comments, shares

## Features
1. **Authentication**: Secure login/signup with password hashing
2. **Dashboard**: Total revenue, profit, orders, product count with charts
3. **Outcome Section**: Smart recommendations with health score, trends, and actionable insights
4. **Product Analytics**: Best sellers, most profitable, low performers
5. **Best Day Analysis**: Identify highest revenue day of week
6. **Trends**: Weekly and monthly sales trends with line charts
7. **Media Impact Analysis**: Track reels/stories/images and measure their impact on sales
8. **Post Recommendations**: ML-powered recommendations for best day/time/type to post based on SALES uplift (not engagement)
9. **Data Management**: User-friendly wizard for new users, easy product/sales entry, CSV import, demo data

## ML Post Recommendation Engine (ml_engine.py)
The engine predicts sales uplift based on posting patterns:
- **Feature Engineering**: Aggregates sales by day/hour, rolling averages (3-day, 7-day), post type encoding
- **Model**: GradientBoostingRegressor trained on historical sales and posting data
- **Output**: Best day, time, and content type for posting with expected revenue uplift
- **Retrainable**: Model can be retrained via UI button

### Key Functions
- `train_post_impact_model()` - Trains/retrains the ML model
- `get_best_posting_recommendation()` - Returns best day/time/type with expected uplift
- `get_posting_insights()` - Detailed performance by day, time, and content type

## Analytics APIs (Functions)
- `get_dashboard_stats()` - Summary metrics
- `get_best_selling_products()` - By quantity sold
- `get_most_profitable_products()` - By profit = (selling_price - cost_price) * quantity
- `get_best_day_of_week()` - Day with highest revenue
- `get_weekly_trends()` / `get_monthly_trends()` - Time series data
- `get_low_performing_products()` - Lowest revenue in last 30 days
- `get_revenue_by_product()` - For pie chart
- `get_media_impact_stats()` - Total posts, avg engagement, sales lift metrics
- `get_posts_with_impact()` - Individual post performance with sales correlation
- `get_media_type_comparison()` - Reels vs Stories vs Images performance comparison
- `get_revenue_with_posts_timeline()` - Revenue timeline with post markers
- `get_business_recommendations()` - Smart recommendations with health score and action items
- `get_sales_by_day_hour()` - Aggregate sales by day of week and hour
- `get_rolling_revenue_averages()` - 3-day, 7-day, 30-day rolling averages
- `get_post_timing_analysis()` - Analyze posting times and their sales impact

## Running the Application
```bash
streamlit run app.py --server.port 5000
```

## Environment Variables
- `DATABASE_URL` - PostgreSQL connection string (auto-configured)
- `SESSION_SECRET` - For secure sessions
