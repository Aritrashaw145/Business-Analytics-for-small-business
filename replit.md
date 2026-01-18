# Business Analytics Dashboard

## Overview
A full-stack data analytics application for small businesses, similar to Instagram Insights. Business owners can manage their products and sales data to receive actionable insights including best-selling products, profit analysis, daily performance, and sales trends.

## Tech Stack
- **Frontend**: Streamlit (Python)
- **Database**: PostgreSQL
- **ORM**: SQLAlchemy
- **Charts**: Plotly
- **Authentication**: bcrypt password hashing with session-based auth

## Project Structure
```
├── app.py           # Main Streamlit application with all UI screens
├── models.py        # Database models (Business, Product, Sale)
├── auth.py          # Authentication logic (login, signup, password hashing)
├── analytics.py     # Analytics functions (best products, trends, etc.)
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
- id, product_id (FK), quantity, total_amount, sale_date

### MediaPost
- id, business_id (FK), post_type (reel/story), caption, posted_at, impressions, likes, comments, shares

## Features
1. **Authentication**: Secure login/signup with password hashing
2. **Dashboard**: Total revenue, profit, orders, product count with charts
3. **Product Analytics**: Best sellers, most profitable, low performers
4. **Best Day Analysis**: Identify highest revenue day of week
5. **Trends**: Weekly and monthly sales trends with line charts
6. **Media Impact Analysis**: Track reels/stories and measure their impact on sales
7. **Data Management**: Add products, record sales, manage media posts, CSV import, demo data

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
- `get_media_type_comparison()` - Reels vs Stories performance comparison
- `get_revenue_with_posts_timeline()` - Revenue timeline with post markers

## Running the Application
```bash
streamlit run app.py --server.port 5000
```

## Environment Variables
- `DATABASE_URL` - PostgreSQL connection string (auto-configured)
- `SESSION_SECRET` - For secure sessions
