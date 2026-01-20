import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
import io
import csv

from models import init_db, SessionLocal, Product, Sale, MediaPost
from auth import create_business, authenticate_business, get_business_by_email
from analytics import (
    get_dashboard_stats,
    get_best_selling_products,
    get_most_profitable_products,
    get_best_day_of_week,
    get_weekly_trends,
    get_monthly_trends,
    get_low_performing_products,
    get_revenue_by_product,
    get_media_impact_stats,
    get_posts_with_impact,
    get_media_type_comparison,
    get_revenue_with_posts_timeline,
    get_business_recommendations,
    get_post_timing_analysis
)
from demo_data import generate_demo_data, clear_demo_data
from ml_engine import (
    get_best_posting_recommendation,
    get_posting_insights,
    train_post_impact_model
)

init_db()

DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "demo123"

def ensure_demo_account():
    """Create demo account with demo data if it doesn't exist"""
    db = SessionLocal()
    try:
        existing = get_business_by_email(db, DEMO_EMAIL)
        if not existing:
            business = create_business(
                db,
                name="Demo Business",
                owner_name="Demo User",
                email=DEMO_EMAIL,
                password=DEMO_PASSWORD,
                category="Food & Beverage"
            )
            if business:
                generate_demo_data(db, business.id)
    finally:
        db.close()

ensure_demo_account()

st.set_page_config(
    page_title="Business Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
    }
    .metric-label {
        font-size: 0.9rem;
        opacity: 0.9;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 20px;
    }
</style>
""", unsafe_allow_html=True)

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "business_id" not in st.session_state:
    st.session_state.business_id = None
if "business_name" not in st.session_state:
    st.session_state.business_name = None


def show_auth_page():
    st.title("Business Analytics Dashboard")
    st.markdown("Track your sales, identify trends, and grow your business with actionable insights.")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        tab1, tab2 = st.tabs(["Login", "Register"])
        
        with tab1:
            st.subheader("Welcome Back")
            st.caption(f"Demo: {DEMO_EMAIL} / {DEMO_PASSWORD}")
            with st.form("login_form"):
                email = st.text_input("Email", placeholder=DEMO_EMAIL, key="login_email")
                password = st.text_input("Password", type="password", placeholder=DEMO_PASSWORD, key="login_password")
                submit = st.form_submit_button("Login", use_container_width=True)
                
                if submit:
                    if email and password:
                        db = SessionLocal()
                        try:
                            business = authenticate_business(db, email, password)
                            if business:
                                st.session_state.authenticated = True
                                st.session_state.business_id = business.id
                                st.session_state.business_name = business.name
                                st.rerun()
                            else:
                                st.error("Invalid email or password")
                        finally:
                            db.close()
                    else:
                        st.warning("Please fill in all fields")
        
        with tab2:
            st.subheader("Create Your Account")
            with st.form("register_form"):
                business_name = st.text_input("Business Name", key="reg_business")
                owner_name = st.text_input("Owner Name", key="reg_owner")
                category = st.selectbox("Business Category", 
                    ["Retail", "Food & Beverage", "Services", "E-commerce", "Other"],
                    key="reg_category")
                email = st.text_input("Email", key="reg_email")
                password = st.text_input("Password", type="password", key="reg_password")
                confirm_password = st.text_input("Confirm Password", type="password", key="reg_confirm")
                submit = st.form_submit_button("Create Account", use_container_width=True)
                
                if submit:
                    if all([business_name, owner_name, email, password, confirm_password]):
                        if password != confirm_password:
                            st.error("Passwords do not match")
                        elif len(password) < 6:
                            st.error("Password must be at least 6 characters")
                        else:
                            db = SessionLocal()
                            try:
                                existing = get_business_by_email(db, email)
                                if existing:
                                    st.error("An account with this email already exists")
                                else:
                                    business = create_business(db, business_name, owner_name, email, password, category)
                                    st.session_state.authenticated = True
                                    st.session_state.business_id = business.id
                                    st.session_state.business_name = business.name
                                    st.success("Account created successfully!")
                                    st.rerun()
                            finally:
                                db.close()
                    else:
                        st.warning("Please fill in all fields")


def show_dashboard():
    db = SessionLocal()
    try:
        stats = get_dashboard_stats(db, st.session_state.business_id)
        
        st.title(f"Dashboard - {st.session_state.business_name}")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="Total Revenue",
                value=f"₹{stats['total_revenue']:,.2f}",
                delta=None
            )
        
        with col2:
            st.metric(
                label="Total Profit",
                value=f"₹{stats['total_profit']:,.2f}",
                delta=None
            )
        
        with col3:
            st.metric(
                label="Total Orders",
                value=f"{stats['total_orders']:,}",
                delta=None
            )
        
        with col4:
            st.metric(
                label="Products",
                value=f"{stats['total_products']}",
                delta=None
            )
        
        recommendations = get_business_recommendations(db, st.session_state.business_id)
        
        health_color = "#10b981" if recommendations["health_score"] >= 70 else (
            "#f59e0b" if recommendations["health_score"] >= 40 else "#ef4444"
        )
        trend_icon = "📈" if recommendations.get("growth_trend") == "growing" else (
            "📉" if recommendations.get("growth_trend") == "declining" else "➡️"
        )
        
        st.markdown("")
        
        if "show_outcome" not in st.session_state:
            st.session_state.show_outcome = False
        
        outcome_btn = st.button("🎯 VIEW YOUR ACTION ITEMS - Click to see what to do next!", 
                                use_container_width=True, type="primary", key="outcome_btn")
        
        if outcome_btn:
            st.session_state.show_outcome = not st.session_state.show_outcome
        
        if st.session_state.show_outcome:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        padding: 20px; border-radius: 12px; color: white; text-align: center; margin: 16px 0;">
                <div style="font-size: 1.2rem; margin-bottom: 8px;">Business Health Score</div>
                <div style="font-size: 3rem; font-weight: bold;">{recommendations["health_score"]}/100</div>
                <div style="font-size: 1rem; opacity: 0.9; margin-top: 8px;">
                    {trend_icon} Sales {recommendations.get("growth_trend", "stable").capitalize()} | Focus: {recommendations["focus_area"]}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("### What You Should Do Next")
            
            for rec in recommendations["recommendations"]:
                if rec["priority"] == "high":
                    priority_color = "#ef4444"
                    bg_color = "#fef2f2"
                    border_color = "#fecaca"
                    priority_label = "HIGH PRIORITY"
                elif rec["priority"] == "medium":
                    priority_color = "#f59e0b"
                    bg_color = "#fffbeb"
                    border_color = "#fde68a"
                    priority_label = "MEDIUM"
                else:
                    priority_color = "#10b981"
                    bg_color = "#ecfdf5"
                    border_color = "#a7f3d0"
                    priority_label = "LOW"
                
                st.markdown(f"""
                <div style="background: {bg_color}; padding: 16px; border-radius: 10px; margin-bottom: 12px; 
                            border: 2px solid {border_color}; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <span style="font-size: 1.5rem;">{rec["icon"]}</span>
                        <div style="flex: 1;">
                            <div style="font-weight: 600; font-size: 1.1rem; color: #1f2937;">{rec["title"]}</div>
                            <div style="color: #4b5563; font-size: 0.95rem; margin-top: 4px;">{rec["description"]}</div>
                        </div>
                        <span style="background: {priority_color}; color: white; padding: 4px 12px; 
                                     border-radius: 20px; font-size: 0.75rem; font-weight: 600;">{priority_label}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        st.divider()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Top Selling Products")
            best_products = get_best_selling_products(db, st.session_state.business_id, 5)
            if best_products:
                df = pd.DataFrame(best_products)
                fig = px.bar(
                    df,
                    x="name",
                    y="quantity_sold",
                    color="category",
                    title="Units Sold by Product"
                )
                fig.update_layout(xaxis_title="", yaxis_title="Quantity Sold")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No sales data yet. Add products and sales to see insights.")
        
        with col2:
            st.subheader("Revenue by Product")
            revenue_data = get_revenue_by_product(db, st.session_state.business_id)
            if revenue_data:
                df = pd.DataFrame(revenue_data)
                fig = px.pie(
                    df,
                    values="revenue",
                    names="name",
                    title="Revenue Distribution"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No revenue data available yet.")
        
        st.subheader("Weekly Sales Trends")
        weekly_trends = get_weekly_trends(db, st.session_state.business_id, 8)
        if weekly_trends:
            df = pd.DataFrame(weekly_trends)
            fig = px.line(
                df,
                x="week",
                y="revenue",
                markers=True,
                title="Revenue Over Time"
            )
            fig.update_layout(xaxis_title="Week Starting", yaxis_title="Revenue (₹)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Not enough data for trends yet.")
        
    finally:
        db.close()


def show_products_analytics():
    db = SessionLocal()
    try:
        st.title("Product Analytics")
        
        tab1, tab2, tab3 = st.tabs(["Best Sellers", "Most Profitable", "Low Performers"])
        
        with tab1:
            st.subheader("Best Selling Products")
            st.markdown("Products ranked by total quantity sold")
            
            best_products = get_best_selling_products(db, st.session_state.business_id, 10)
            if best_products:
                df = pd.DataFrame(best_products)
                
                fig = px.bar(
                    df,
                    x="quantity_sold",
                    y="name",
                    orientation='h',
                    color="revenue",
                    color_continuous_scale="Viridis",
                    title="Top 10 Best Selling Products"
                )
                fig.update_layout(yaxis={'categoryorder': 'total ascending'})
                st.plotly_chart(fig, use_container_width=True)
                
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("No sales data available yet.")
        
        with tab2:
            st.subheader("Most Profitable Products")
            st.markdown("Products ranked by total profit generated")
            
            profitable = get_most_profitable_products(db, st.session_state.business_id, 10)
            if profitable:
                df = pd.DataFrame(profitable)
                
                fig = px.bar(
                    df,
                    x="profit",
                    y="name",
                    orientation='h',
                    color="profit_margin",
                    color_continuous_scale="RdYlGn",
                    title="Top 10 Most Profitable Products"
                )
                fig.update_layout(yaxis={'categoryorder': 'total ascending'})
                st.plotly_chart(fig, use_container_width=True)
                
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("No profit data available yet.")
        
        with tab3:
            st.subheader("Low Performing Products")
            st.markdown("Products with lowest revenue in the last 30 days")
            
            low_performers = get_low_performing_products(db, st.session_state.business_id, 10)
            if low_performers:
                df = pd.DataFrame(low_performers)
                
                fig = px.bar(
                    df,
                    x="revenue",
                    y="name",
                    orientation='h',
                    color="quantity_sold",
                    color_continuous_scale="Reds_r",
                    title="Low Performing Products (Last 30 Days)"
                )
                fig.update_layout(yaxis={'categoryorder': 'total descending'})
                st.plotly_chart(fig, use_container_width=True)
                
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("No product data available yet.")
                
    finally:
        db.close()


def show_best_day():
    db = SessionLocal()
    try:
        st.title("Best Day Analysis")
        
        best_day_data = get_best_day_of_week(db, st.session_state.business_id)
        
        if best_day_data["day"] != "N/A":
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.markdown("### Your Best Day")
                st.markdown(f"## {best_day_data['day']}")
                st.metric("Revenue on Best Day", f"₹{best_day_data['revenue']:,.2f}")
                st.markdown("---")
                st.info("This is the day when your business generates the most revenue. Consider scheduling promotions or increasing staff on this day.")
            
            with col2:
                df = pd.DataFrame(best_day_data["daily_breakdown"])
                
                colors = ['#667eea' if day != best_day_data['day'] else '#ff6b6b' for day in df['day']]
                
                fig = go.Figure(data=[
                    go.Bar(
                        x=df['day'],
                        y=df['revenue'],
                        marker_color=colors
                    )
                ])
                fig.update_layout(
                    title="Revenue by Day of Week",
                    xaxis_title="Day",
                    yaxis_title="Revenue (₹)"
                )
                st.plotly_chart(fig, use_container_width=True)
            
            st.subheader("Daily Revenue Breakdown")
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No sales data available yet. Add sales to see which day performs best.")
            
    finally:
        db.close()


def show_trends():
    db = SessionLocal()
    try:
        st.title("Sales Trends")
        
        tab1, tab2 = st.tabs(["Weekly Trends", "Monthly Trends"])
        
        with tab1:
            st.subheader("Weekly Sales Trends")
            weekly = get_weekly_trends(db, st.session_state.business_id, 12)
            
            if weekly:
                df = pd.DataFrame(weekly)
                
                fig = px.line(
                    df,
                    x="week",
                    y="revenue",
                    markers=True,
                    title="Weekly Revenue"
                )
                fig.update_traces(line_color='#667eea', marker_size=10)
                fig.update_layout(xaxis_title="Week Starting", yaxis_title="Revenue (₹)")
                st.plotly_chart(fig, use_container_width=True)
                
                fig2 = px.bar(
                    df,
                    x="week",
                    y="orders",
                    title="Weekly Orders Count"
                )
                fig2.update_traces(marker_color='#764ba2')
                st.plotly_chart(fig2, use_container_width=True)
                
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("Not enough data for weekly trends yet.")
        
        with tab2:
            st.subheader("Monthly Sales Trends")
            monthly = get_monthly_trends(db, st.session_state.business_id, 12)
            
            if monthly:
                df = pd.DataFrame(monthly)
                
                fig = px.area(
                    df,
                    x="month",
                    y="revenue",
                    title="Monthly Revenue"
                )
                fig.update_traces(fill='tozeroy', line_color='#667eea')
                fig.update_layout(xaxis_title="Month", yaxis_title="Revenue (₹)")
                st.plotly_chart(fig, use_container_width=True)
                
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("Not enough data for monthly trends yet.")
                
    finally:
        db.close()


def show_media_impact():
    db = SessionLocal()
    try:
        st.title("Media Impact Analysis")
        st.markdown("See how your social media posts (reels and stories) affect your sales")
        
        stats = get_media_impact_stats(db, st.session_state.business_id)
        
        if stats["total_posts"] == 0:
            st.info("No media posts found. Add posts in Data Management to see their impact on sales.")
            return
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Posts", stats["total_posts"])
        with col2:
            st.metric("Reels", stats["total_reels"])
        with col3:
            st.metric("Stories", stats["total_stories"])
        with col4:
            st.metric("Avg Engagement", f"{stats['avg_engagement']:.0f}")
        
        col5, col6 = st.columns(2)
        with col5:
            delta_color = "normal" if stats["avg_lift"] >= 0 else "inverse"
            st.metric(
                "Avg Sales Lift",
                f"{stats['avg_lift']:.1f}%",
                help="Average % increase in daily sales after posting"
            )
        with col6:
            st.metric(
                "Est. Incremental Revenue",
                f"₹{stats['total_incremental_revenue']:,.2f}",
                help="Estimated additional revenue generated by posts"
            )
        
        st.divider()
        
        comparison = get_media_type_comparison(db, st.session_state.business_id)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Reels vs Stories Performance")
            
            comparison_data = [
                {"Type": "Reels", "Count": comparison["reels"]["count"], 
                 "Avg Lift %": comparison["reels"]["avg_lift"], 
                 "Avg Engagement": comparison["reels"]["avg_engagement"]},
                {"Type": "Stories", "Count": comparison["stories"]["count"], 
                 "Avg Lift %": comparison["stories"]["avg_lift"], 
                 "Avg Engagement": comparison["stories"]["avg_engagement"]}
            ]
            
            df = pd.DataFrame(comparison_data)
            
            fig = go.Figure(data=[
                go.Bar(name='Avg Sales Lift %', x=df['Type'], y=df['Avg Lift %'], marker_color='#667eea'),
                go.Bar(name='Avg Engagement', x=df['Type'], y=df['Avg Engagement'], marker_color='#764ba2')
            ])
            fig.update_layout(barmode='group', title="Reel vs Story Comparison")
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("Revenue Timeline with Posts")
            
            timeline = get_revenue_with_posts_timeline(db, st.session_state.business_id, 30)
            
            if timeline["revenue_data"]:
                df = pd.DataFrame(timeline["revenue_data"])
                df["date"] = pd.to_datetime(df["date"])
                
                fig = px.line(df, x="date", y="revenue", title="Daily Revenue (Last 30 Days)")
                fig.update_traces(line_color='#667eea')
                
                for marker in timeline["post_markers"]:
                    color = '#ff6b6b' if marker["type"] == "reel" else '#feca57'
                    marker_date = pd.to_datetime(marker["date"])
                    fig.add_shape(
                        type="line",
                        x0=marker_date, x1=marker_date,
                        y0=0, y1=1,
                        yref="paper",
                        line=dict(color=color, width=1, dash="dash")
                    )
                
                fig.update_layout(
                    xaxis_title="Date",
                    yaxis_title="Revenue (₹)",
                    showlegend=False
                )
                st.plotly_chart(fig, use_container_width=True)
                st.caption("R = Reel posted, S = Story posted")
        
        st.subheader("Individual Post Performance")
        
        posts_with_impact = get_posts_with_impact(db, st.session_state.business_id)
        
        if posts_with_impact:
            df = pd.DataFrame(posts_with_impact)
            
            fig = px.bar(
                df,
                x="posted_at",
                y="lift_percent",
                color="post_type",
                color_discrete_map={"reel": "#667eea", "story": "#feca57"},
                title="Sales Lift % by Post",
                hover_data=["caption", "engagement", "incremental_revenue"]
            )
            fig.update_layout(xaxis_title="Post Date", yaxis_title="Sales Lift %")
            st.plotly_chart(fig, use_container_width=True)
            
            display_df = df[["posted_at", "post_type", "caption", "engagement", "lift_percent", "incremental_revenue"]].copy()
            display_df.columns = ["Date", "Type", "Caption", "Engagement", "Lift %", "Incremental ₹"]
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.markdown("### Understanding the Metrics")
            st.markdown("""
            - **Sales Lift %**: How much daily revenue increased in the 3 days after posting compared to the 7-day baseline before
            - **Incremental Revenue**: Estimated additional revenue generated by each post
            - **Engagement**: Total likes, comments, and shares
            """)
            
    finally:
        db.close()


def show_post_recommendations():
    db = SessionLocal()
    try:
        st.title("Post Recommendations")
        st.markdown("Get data-driven recommendations for when to post based on **sales impact**, not just engagement.")
        
        recommendation = get_best_posting_recommendation(db, st.session_state.business_id)
        
        if recommendation.get("error"):
            st.warning(recommendation.get("message", "Add more posts and sales data to get personalized recommendations."))
            
            st.markdown("""
            ### How This Works
            
            Unlike typical social media analytics that focus on likes and engagement, 
            this feature analyzes your **actual sales data** to find:
            
            - **Best Day**: Which day of the week leads to highest sales after posting
            - **Best Time**: Morning, afternoon, or evening - when posting drives the most revenue
            - **Best Content Type**: Whether reels, stories, or images generate more sales
            
            **To get started:**
            1. Add at least 3 media posts in Data Management
            2. Record sales for at least 30 days
            3. Come back to see personalized recommendations
            """)
        else:
            best = recommendation.get("best_overall", {})
            
            post_type = best.get('post_type', 'reel')
            day = best.get('day', 'Friday')
            uplift = best.get('expected_uplift_percent', 0)
            
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); 
                        padding: 24px; border-radius: 16px; color: white; margin-bottom: 24px;">
                <div style="font-size: 1.1rem; opacity: 0.9; margin-bottom: 8px;">AI Recommendation</div>
                <div style="font-size: 1.6rem; font-weight: bold; margin-bottom: 12px;">
                    If you post a {post_type} on {day} evening, your sales are likely to increase by ~{uplift:.0f}%
                </div>
                <div style="font-size: 1rem; opacity: 0.9; margin-top: 8px;">
                    Confidence: {best.get('confidence', 'medium').capitalize()} | Based on your actual sales data
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("""
                <div style="background: #f0fdf4; padding: 20px; border-radius: 12px; text-align: center; border: 2px solid #10b981;">
                    <div style="font-size: 0.9rem; color: #666;">Best Day</div>
                    <div style="font-size: 1.5rem; font-weight: bold; color: #10b981;">{}</div>
                </div>
                """.format(recommendation.get('best_day', 'Friday')), unsafe_allow_html=True)
            
            with col2:
                st.markdown("""
                <div style="background: #eff6ff; padding: 20px; border-radius: 12px; text-align: center; border: 2px solid #3b82f6;">
                    <div style="font-size: 0.9rem; color: #666;">Best Time</div>
                    <div style="font-size: 1.5rem; font-weight: bold; color: #3b82f6;">{}</div>
                </div>
                """.format(recommendation.get('best_time', 'Evening')), unsafe_allow_html=True)
            
            with col3:
                st.markdown("""
                <div style="background: #fef3c7; padding: 20px; border-radius: 12px; text-align: center; border: 2px solid #f59e0b;">
                    <div style="font-size: 0.9rem; color: #666;">Best Content Type</div>
                    <div style="font-size: 1.5rem; font-weight: bold; color: #f59e0b;">{}</div>
                </div>
                """.format(recommendation.get('best_post_type', 'Reel').capitalize()), unsafe_allow_html=True)
            
            st.divider()
            
            st.subheader("Top 5 Posting Scenarios")
            st.markdown("Ranked by expected sales impact")
            
            top_scenarios = recommendation.get("top_5_scenarios", [])
            if top_scenarios:
                scenario_data = []
                for i, s in enumerate(top_scenarios, 1):
                    scenario_data.append({
                        "Rank": i,
                        "Day": s["day"],
                        "Post Type": s["post_type"].capitalize(),
                        "Expected Uplift": f"+{s['uplift_percent']:.1f}%",
                        "Expected Revenue": f"₹{s['expected_revenue']:,.0f}",
                        "Confidence": s.get("confidence", "medium").capitalize()
                    })
                
                st.dataframe(pd.DataFrame(scenario_data), use_container_width=True, hide_index=True)
            
            st.divider()
            
            insights = get_posting_insights(db, st.session_state.business_id)
            
            if insights.get("has_data"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("Performance by Day")
                    day_data = insights.get("day_performance", [])
                    if day_data:
                        df = pd.DataFrame(day_data)
                        fig = px.bar(
                            df,
                            x="day",
                            y="avg_lift",
                            color="avg_lift",
                            color_continuous_scale="RdYlGn",
                            title="Average Sales Lift by Day"
                        )
                        fig.update_layout(xaxis_title="Day", yaxis_title="Avg Sales Lift %")
                        st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    st.subheader("Performance by Content Type")
                    type_data = insights.get("type_performance", [])
                    if type_data:
                        df = pd.DataFrame(type_data)
                        fig = px.bar(
                            df,
                            x="type",
                            y="avg_lift",
                            color="type",
                            color_discrete_map={"reel": "#667eea", "story": "#feca57", "image": "#10b981"},
                            title="Average Sales Lift by Content Type"
                        )
                        fig.update_layout(xaxis_title="Content Type", yaxis_title="Avg Sales Lift %")
                        st.plotly_chart(fig, use_container_width=True)
            
            st.divider()
            
            with st.expander("Train ML Model for Better Predictions"):
                st.markdown("""
                Train a machine learning model on your data for more accurate predictions.
                The model learns from your specific sales patterns and posting history.
                """)
                
                if st.button("Train Model", type="primary"):
                    with st.spinner("Training model..."):
                        result = train_post_impact_model(db, st.session_state.business_id)
                        
                        if result.get("success"):
                            st.success(f"Model trained successfully!")
                            st.markdown(f"""
                            **Model Performance:**
                            - R² Score: {result.get('r2', 0):.3f} (higher is better, max 1.0)
                            - Mean Absolute Error: ₹{result.get('mae', 0):,.2f}
                            - Data points used: {result.get('data_points', 0)}
                            
                            **Top Features:**
                            """)
                            for feat, imp in list(result.get('feature_importance', {}).items())[:5]:
                                st.markdown(f"- {feat}: {imp:.4f}")
                            
                            st.rerun()
                        else:
                            st.error(result.get("error", "Training failed"))
                
                if recommendation.get("model_available"):
                    st.info("A trained model is active and being used for predictions.")
            
            st.markdown("---")
            st.markdown("""
            ### How It Works
            
            This recommendation engine analyzes the relationship between your **posting activity** 
            and **actual sales revenue**, not just likes or engagement metrics.
            
            The system:
            1. Compares sales in the 3 days after each post to the 7-day baseline before
            2. Identifies patterns in which days, times, and content types drive the most sales
            3. Uses machine learning (when trained) to predict expected revenue for different scenarios
            
            **Key insight**: A post that gets fewer likes but drives more sales is more valuable to your business!
            """)
            
    finally:
        db.close()


def show_data_management():
    db = SessionLocal()
    try:
        st.title("Data Management")
        
        products = db.query(Product).filter(
            Product.business_id == st.session_state.business_id
        ).all()
        
        sales_count = 0
        if products:
            product_ids = [p.id for p in products]
            sales_count = db.query(Sale).filter(Sale.product_id.in_(product_ids)).count()
        
        posts_count = db.query(MediaPost).filter(
            MediaPost.business_id == st.session_state.business_id
        ).count()
        
        if not products:
            st.markdown("""
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        padding: 30px; border-radius: 16px; color: white; text-align: center; margin-bottom: 24px;">
                <h2 style="margin: 0 0 10px 0;">Welcome! Let's Get Started</h2>
                <p style="margin: 0; opacity: 0.9;">Follow these simple steps to set up your business analytics</p>
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("""
                <div style="background: #f0fdf4; padding: 20px; border-radius: 12px; text-align: center; border: 2px solid #10b981;">
                    <div style="font-size: 2rem;">1</div>
                    <div style="font-weight: 600; margin: 8px 0;">Add Products</div>
                    <div style="color: #666; font-size: 0.9rem;">Enter your products with prices</div>
                </div>
                """, unsafe_allow_html=True)
            with col2:
                st.markdown("""
                <div style="background: #fef3c7; padding: 20px; border-radius: 12px; text-align: center; border: 2px dashed #f59e0b;">
                    <div style="font-size: 2rem;">2</div>
                    <div style="font-weight: 600; margin: 8px 0;">Record Sales</div>
                    <div style="color: #666; font-size: 0.9rem;">Log your daily sales</div>
                </div>
                """, unsafe_allow_html=True)
            with col3:
                st.markdown("""
                <div style="background: #ede9fe; padding: 20px; border-radius: 12px; text-align: center; border: 2px dashed #8b5cf6;">
                    <div style="font-size: 2rem;">3</div>
                    <div style="font-weight: 600; margin: 8px 0;">View Insights</div>
                    <div style="color: #666; font-size: 0.9rem;">See analytics and recommendations</div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            with col1:
                st.info("Want to explore the app first? Load demo data to see how everything works.")
            with col2:
                if st.button("Load Demo Data to Explore", use_container_width=True, type="primary"):
                    if generate_demo_data(db, st.session_state.business_id):
                        st.success("Demo data loaded! Go to Dashboard to see your insights.")
                        st.rerun()
            
            st.divider()
        else:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Products", len(products))
            with col2:
                st.metric("Sales Recorded", sales_count)
            with col3:
                st.metric("Media Posts", posts_count)
            with col4:
                progress = min(100, (len(products) * 20) + (min(sales_count, 10) * 5) + (posts_count * 5))
                st.metric("Data Completeness", f"{progress}%")
            
            st.divider()
        
        if "data_mgmt_tab" not in st.session_state:
            st.session_state.data_mgmt_tab = "Add Products"
        
        tab_options = ["Add Products", "Record Sales", "Media Posts", "Import / Demo"]
        current_tab_idx = tab_options.index(st.session_state.data_mgmt_tab) if st.session_state.data_mgmt_tab in tab_options else 0
        
        selected_tab = st.radio(
            "Choose Action",
            tab_options,
            index=current_tab_idx,
            horizontal=True,
            key="data_mgmt_tab_radio"
        )
        
        if selected_tab != st.session_state.data_mgmt_tab:
            st.session_state.data_mgmt_tab = selected_tab
        
        st.markdown("---")
        
        if selected_tab == "Add Products":
            st.subheader("Add Your Products")
            st.markdown("Enter the products you sell with their costs and prices.")
            
            with st.form("add_product", clear_on_submit=True):
                st.markdown("**New Product Details**")
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    name = st.text_input("Product Name", placeholder="e.g., Coffee Latte")
                with col2:
                    cost_price = st.number_input("Cost Price (₹)", min_value=0.01, step=0.01, value=1.00)
                with col3:
                    selling_price = st.number_input("Selling Price (₹)", min_value=0.01, step=0.01, value=2.00)
                
                col1, col2 = st.columns([1, 1])
                with col1:
                    category = st.selectbox("Category", 
                        ["Beverages", "Bakery", "Pantry", "Breakfast", "Snacks", "Other"])
                with col2:
                    margin = ((selling_price - cost_price) / selling_price * 100) if selling_price > 0 else 0
                    st.markdown(f"**Profit Margin: {margin:.1f}%**")
                
                submitted = st.form_submit_button("Add Product", use_container_width=True, type="primary")
                
                if submitted:
                    if name and cost_price > 0 and selling_price > 0:
                        product = Product(
                            business_id=st.session_state.business_id,
                            name=name,
                            cost_price=cost_price,
                            selling_price=selling_price,
                            category=category
                        )
                        db.add(product)
                        db.commit()
                        st.success(f"Product '{name}' added successfully!")
                        st.rerun()
                    else:
                        st.error("Please enter a product name")
            
            current_products = db.query(Product).filter(
                Product.business_id == st.session_state.business_id
            ).all()
            
            if current_products:
                st.markdown("---")
                st.markdown(f"**Your Products ({len(current_products)})**")
                product_data = [{
                    "Name": p.name,
                    "Category": p.category,
                    "Cost": f"₹{p.cost_price:.2f}",
                    "Price": f"₹{p.selling_price:.2f}",
                    "Margin": f"{((p.selling_price - p.cost_price) / p.selling_price * 100):.1f}%"
                } for p in current_products]
                st.dataframe(pd.DataFrame(product_data), use_container_width=True, hide_index=True)
            else:
                st.info("No products added yet. Add your first product above!")
        
        elif selected_tab == "Record Sales":
            st.subheader("Record Your Sales")
            st.markdown("Log sales as they happen or at the end of each day.")
            
            all_products = db.query(Product).filter(
                Product.business_id == st.session_state.business_id
            ).all()
            
            if all_products:
                with st.form("add_sale", clear_on_submit=True):
                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col1:
                        product_options = {p.name: p for p in all_products}
                        selected_product = st.selectbox("Select Product", list(product_options.keys()))
                    with col2:
                        quantity = st.number_input("Quantity Sold", min_value=1, value=1)
                    with col3:
                        sale_date = st.date_input("Date", value=datetime.now().date())
                    
                    selected = product_options.get(selected_product)
                    if selected:
                        estimated_total = quantity * selected.selling_price
                        st.markdown(f"**Total: ₹{estimated_total:.2f}** (₹{selected.selling_price:.2f} x {quantity})")
                    
                    submitted = st.form_submit_button("Record Sale", use_container_width=True, type="primary")
                    
                    if submitted:
                        product = product_options[selected_product]
                        total_amount = quantity * product.selling_price
                        
                        sale = Sale(
                            product_id=product.id,
                            quantity=quantity,
                            total_amount=total_amount,
                            sale_date=sale_date
                        )
                        db.add(sale)
                        db.commit()
                        st.success(f"Recorded: {quantity}x {selected_product} = ₹{total_amount:.2f}")
                        st.rerun()
                
                product_ids = [p.id for p in all_products]
                recent_sales = db.query(Sale).filter(
                    Sale.product_id.in_(product_ids)
                ).order_by(Sale.sale_date.desc()).limit(10).all()
                
                if recent_sales:
                    st.markdown("---")
                    st.markdown("**Recent Sales (Last 10)**")
                    sales_data = []
                    for s in recent_sales:
                        prod = next((p for p in all_products if p.id == s.product_id), None)
                        if prod:
                            sales_data.append({
                                "Date": s.sale_date.strftime("%Y-%m-%d"),
                                "Product": prod.name,
                                "Qty": s.quantity,
                                "Total": f"₹{s.total_amount:.2f}"
                            })
                    st.dataframe(pd.DataFrame(sales_data), use_container_width=True, hide_index=True)
            else:
                st.warning("Add products first before recording sales. Go to the 'Add Products' tab.")
        
        elif selected_tab == "Media Posts":
            st.subheader("Media Posts")
            st.markdown("Track your social media posts (reels and stories)")
            
            with st.expander("Add New Post"):
                with st.form("add_media_post"):
                    col1, col2 = st.columns(2)
                    with col1:
                        post_type = st.selectbox("Post Type", ["reel", "story"])
                        posted_at = st.date_input("Post Date", value=datetime.now().date())
                    with col2:
                        impressions = st.number_input("Impressions", min_value=0, value=0)
                        likes = st.number_input("Likes", min_value=0, value=0)
                    
                    col3, col4 = st.columns(2)
                    with col3:
                        comments = st.number_input("Comments", min_value=0, value=0)
                    with col4:
                        shares = st.number_input("Shares", min_value=0, value=0)
                    
                    caption = st.text_area("Caption", max_chars=500)
                    
                    if st.form_submit_button("Add Post"):
                        media_post = MediaPost(
                            business_id=st.session_state.business_id,
                            post_type=post_type,
                            caption=caption,
                            posted_at=posted_at,
                            impressions=impressions,
                            likes=likes,
                            comments=comments,
                            shares=shares
                        )
                        db.add(media_post)
                        db.commit()
                        st.success(f"{post_type.capitalize()} added successfully!")
                        st.rerun()
            
            media_posts = db.query(MediaPost).filter(
                MediaPost.business_id == st.session_state.business_id
            ).order_by(MediaPost.posted_at.desc()).all()
            
            if media_posts:
                posts_data = [{
                    "Date": p.posted_at.strftime("%Y-%m-%d"),
                    "Type": p.post_type.capitalize(),
                    "Caption": (p.caption[:50] + "...") if p.caption and len(p.caption) > 50 else (p.caption or ""),
                    "Impressions": p.impressions,
                    "Likes": p.likes,
                    "Comments": p.comments,
                    "Shares": p.shares,
                    "Engagement": p.likes + p.comments + p.shares
                } for p in media_posts]
                st.dataframe(pd.DataFrame(posts_data), use_container_width=True, hide_index=True)
            else:
                st.info("No media posts added yet. Add posts to track their impact on sales.")
        
        elif selected_tab == "Import / Demo":
            st.subheader("Quick Start with Demo Data")
            demo_col1, demo_col2 = st.columns(2)
            with demo_col1:
                if st.button("Load Demo Data", use_container_width=True, type="primary"):
                    if generate_demo_data(db, st.session_state.business_id):
                        st.success("Demo data loaded! Go to Dashboard to see insights.")
                        st.rerun()
                    else:
                        st.warning("Demo data already exists.")
            with demo_col2:
                if st.button("Clear All Data", use_container_width=True, type="secondary"):
                    clear_demo_data(db, st.session_state.business_id)
                    st.success("All data cleared.")
                    st.rerun()
            
            st.divider()
            
            st.subheader("Import from CSV Files")
            st.info("Import your data in 3 steps: First Products, then Sales, then Media Posts (optional)")
            
            if "import_step" not in st.session_state:
                st.session_state.import_step = 1
            
            step_cols = st.columns(3)
            with step_cols[0]:
                step1_active = st.session_state.import_step == 1
                step1_bg = "#1e40af" if step1_active else "#374151"
                st.markdown(f"""
                <div style="background: {step1_bg}; color: white; padding: 12px 16px; border-radius: 8px; 
                            text-align: center; font-weight: 600; cursor: pointer; margin-bottom: 8px;">
                    1. Products {"✓" if st.session_state.import_step > 1 else ""}
                </div>
                """, unsafe_allow_html=True)
                if st.button("Select Products", use_container_width=True, key="step1_btn", type="secondary" if not step1_active else "primary"):
                    st.session_state.import_step = 1
                    st.rerun()
            with step_cols[1]:
                step2_active = st.session_state.import_step == 2
                step2_bg = "#1e40af" if step2_active else "#374151"
                st.markdown(f"""
                <div style="background: {step2_bg}; color: white; padding: 12px 16px; border-radius: 8px; 
                            text-align: center; font-weight: 600; cursor: pointer; margin-bottom: 8px;">
                    2. Sales {"✓" if st.session_state.import_step > 2 else ""}
                </div>
                """, unsafe_allow_html=True)
                if st.button("Select Sales", use_container_width=True, key="step2_btn", type="secondary" if not step2_active else "primary"):
                    st.session_state.import_step = 2
                    st.rerun()
            with step_cols[2]:
                step3_active = st.session_state.import_step == 3
                step3_bg = "#1e40af" if step3_active else "#374151"
                st.markdown(f"""
                <div style="background: {step3_bg}; color: white; padding: 12px 16px; border-radius: 8px; 
                            text-align: center; font-weight: 600; cursor: pointer; margin-bottom: 8px;">
                    3. Media Posts
                </div>
                """, unsafe_allow_html=True)
                if st.button("Select Media Posts", use_container_width=True, key="step3_btn", type="secondary" if not step3_active else "primary"):
                    st.session_state.import_step = 3
                    st.rerun()
            
            st.markdown("---")
            
            if st.session_state.import_step == 1:
                st.markdown("### Step 1: Import Products")
                st.markdown("""
                <div style="background: #eff6ff; padding: 16px; border-radius: 8px; margin-bottom: 16px;">
                    <strong>Required Columns:</strong>
                    <table style="width: 100%; margin-top: 8px;">
                        <tr><td><code>name</code></td><td>Product name (e.g., Masala Chai)</td></tr>
                        <tr><td><code>cost_price</code></td><td>Your cost in ₹ (e.g., 15)</td></tr>
                        <tr><td><code>selling_price</code></td><td>Selling price in ₹ (e.g., 30)</td></tr>
                    </table>
                    <strong style="margin-top: 8px; display: block;">Optional:</strong>
                    <table style="width: 100%; margin-top: 8px;">
                        <tr><td><code>category</code></td><td>Product category (e.g., Beverages)</td></tr>
                    </table>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("**Example CSV:**")
                st.code("name,cost_price,selling_price,category\nMasala Chai,15,30,Beverages\nSamosa,8,20,Snacks", language="csv")
                
                products_file = st.file_uploader("Upload Products CSV", type="csv", key="products_csv")
                
                if products_file is not None:
                    try:
                        df = pd.read_csv(products_file)
                        st.dataframe(df.head(5), use_container_width=True)
                        
                        if st.button("Import Products & Go to Sales", use_container_width=True, type="primary", key="import_products_btn"):
                            imported = 0
                            for _, row in df.iterrows():
                                name = str(row.get('name', '')).strip()
                                if name:
                                    product = Product(
                                        business_id=st.session_state.business_id,
                                        name=name,
                                        cost_price=float(row.get('cost_price', 0)),
                                        selling_price=float(row.get('selling_price', 0)),
                                        category=str(row.get('category', 'General')) if pd.notna(row.get('category')) else 'General'
                                    )
                                    db.add(product)
                                    imported += 1
                            db.commit()
                            st.success(f"Successfully imported {imported} products! Moving to Sales import...")
                            st.session_state.import_step = 2
                            st.session_state.data_mgmt_tab = "Import / Demo"
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
            
            elif st.session_state.import_step == 2:
                st.markdown("### Step 2: Import Sales")
                st.warning("Make sure you have imported Products first! Product names must match exactly.")
                
                st.markdown("""
                <div style="background: #f0fdf4; padding: 16px; border-radius: 8px; margin-bottom: 16px;">
                    <strong>Required Columns:</strong>
                    <table style="width: 100%; margin-top: 8px;">
                        <tr><td><code>product_name</code></td><td>Must match your product names exactly</td></tr>
                        <tr><td><code>quantity</code></td><td>Number sold (e.g., 5)</td></tr>
                        <tr><td><code>sale_date</code></td><td>Date in YYYY-MM-DD format (e.g., 2025-01-15)</td></tr>
                    </table>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("**Example CSV:**")
                st.code("product_name,quantity,sale_date\nMasala Chai,5,2025-01-15\nSamosa,10,2025-01-15", language="csv")
                
                sales_file = st.file_uploader("Upload Sales CSV", type="csv", key="sales_csv")
                
                if sales_file is not None:
                    try:
                        df = pd.read_csv(sales_file)
                        st.dataframe(df.head(5), use_container_width=True)
                        
                        if st.button("Import Sales", use_container_width=True, type="primary", key="import_sales_btn"):
                            import_products = db.query(Product).filter(
                                Product.business_id == st.session_state.business_id
                            ).all()
                            product_map = {p.name.lower(): p for p in import_products}
                            
                            imported = 0
                            errors = 0
                            error_names = []
                            
                            for _, row in df.iterrows():
                                product_name = str(row.get('product_name', '')).strip().lower()
                                if product_name in product_map:
                                    product = product_map[product_name]
                                    quantity = int(row.get('quantity', 1))
                                    sale_date = pd.to_datetime(row.get('sale_date')).date()
                                    
                                    sale = Sale(
                                        product_id=product.id,
                                        quantity=quantity,
                                        total_amount=quantity * product.selling_price,
                                        sale_date=sale_date
                                    )
                                    db.add(sale)
                                    imported += 1
                                else:
                                    errors += 1
                                    if product_name not in error_names:
                                        error_names.append(product_name)
                            
                            db.commit()
                            if errors > 0:
                                st.warning(f"Imported {imported} sales. Skipped {errors} (product not found: {', '.join(error_names[:5])})")
                            else:
                                st.success(f"Successfully imported {imported} sales! Moving to Media Posts...")
                            st.session_state.import_step = 3
                            st.session_state.data_mgmt_tab = "Import / Demo"
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
            
            elif st.session_state.import_step == 3:
                st.markdown("### Step 3: Import Media Posts (Optional)")
                st.markdown("Import your social media posts to get AI-powered posting recommendations.")
                
                st.markdown("""
                <div style="background: #fef3c7; padding: 16px; border-radius: 8px; margin-bottom: 16px;">
                    <strong>Required Columns:</strong>
                    <table style="width: 100%; margin-top: 8px;">
                        <tr><td><code>post_type</code></td><td>reel, story, or image</td></tr>
                        <tr><td><code>posted_at</code></td><td>Date in YYYY-MM-DD format</td></tr>
                    </table>
                    <strong style="margin-top: 8px; display: block;">Optional Columns:</strong>
                    <table style="width: 100%; margin-top: 8px;">
                        <tr><td><code>caption</code></td><td>Post caption text</td></tr>
                        <tr><td><code>post_time</code></td><td>Time in HH:MM:SS format (e.g., 18:30:00)</td></tr>
                        <tr><td><code>platform</code></td><td>instagram, facebook, etc.</td></tr>
                        <tr><td><code>impressions</code></td><td>View count</td></tr>
                        <tr><td><code>likes</code></td><td>Likes count</td></tr>
                        <tr><td><code>comments</code></td><td>Comments count</td></tr>
                        <tr><td><code>shares</code></td><td>Shares count</td></tr>
                    </table>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("**Example CSV:**")
                st.code("post_type,posted_at,post_time,caption,platform,impressions,likes,comments,shares\nreel,2025-01-10,18:30:00,New menu!,instagram,5000,200,25,15\nstory,2025-01-12,12:00:00,Behind scenes,instagram,2000,150,10,5", language="csv")
                
                posts_file = st.file_uploader("Upload Media Posts CSV", type="csv", key="posts_csv")
                
                if posts_file is not None:
                    try:
                        df = pd.read_csv(posts_file)
                        st.dataframe(df.head(5), use_container_width=True)
                        
                        if st.button("Import Media Posts", use_container_width=True, type="primary", key="import_posts_btn"):
                            from datetime import time as dt_time
                            imported = 0
                            for _, row in df.iterrows():
                                post_type = str(row.get('post_type', 'image')).strip().lower()
                                if post_type in ['reel', 'story', 'image']:
                                    posted_at = pd.to_datetime(row.get('posted_at')).date()
                                    
                                    post_time = None
                                    if pd.notna(row.get('post_time')):
                                        try:
                                            time_parts = str(row.get('post_time')).split(':')
                                            post_time = dt_time(int(time_parts[0]), int(time_parts[1]), int(time_parts[2]) if len(time_parts) > 2 else 0)
                                        except:
                                            pass
                                    
                                    post = MediaPost(
                                        business_id=st.session_state.business_id,
                                        post_type=post_type,
                                        caption=str(row.get('caption', ''))[:500] if pd.notna(row.get('caption')) else '',
                                        posted_at=posted_at,
                                        post_time=post_time,
                                        platform=str(row.get('platform', 'instagram')) if pd.notna(row.get('platform')) else 'instagram',
                                        impressions=int(row.get('impressions', 0)) if pd.notna(row.get('impressions')) else 0,
                                        likes=int(row.get('likes', 0)) if pd.notna(row.get('likes')) else 0,
                                        comments=int(row.get('comments', 0)) if pd.notna(row.get('comments')) else 0,
                                        shares=int(row.get('shares', 0)) if pd.notna(row.get('shares')) else 0
                                    )
                                    db.add(post)
                                    imported += 1
                            db.commit()
                            st.success(f"Successfully imported {imported} media posts! Redirecting to Dashboard...")
                            st.session_state.redirect_to_dashboard = True
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
                    
    finally:
        db.close()


def main():
    if not st.session_state.authenticated:
        show_auth_page()
    else:
        if st.session_state.get("redirect_to_dashboard"):
            st.session_state.redirect_to_dashboard = False
            st.session_state.current_page = "Dashboard"
        
        if "current_page" not in st.session_state:
            st.session_state.current_page = "Dashboard"
        
        with st.sidebar:
            st.title("Navigation")
            st.markdown(f"**{st.session_state.business_name}**")
            st.divider()
            
            pages = ["Dashboard", "Product Analytics", "Best Day", "Trends", "Media Impact", "Post Recommendations", "Data Management"]
            current_index = pages.index(st.session_state.current_page) if st.session_state.current_page in pages else 0
            
            page = st.radio(
                "Go to",
                pages,
                index=current_index,
                label_visibility="collapsed"
            )
            
            if page != st.session_state.current_page:
                st.session_state.current_page = page
            
            st.divider()
            
            if st.button("Logout", use_container_width=True):
                st.session_state.authenticated = False
                st.session_state.business_id = None
                st.session_state.business_name = None
                st.rerun()
        
        if page == "Dashboard":
            show_dashboard()
        elif page == "Product Analytics":
            show_products_analytics()
        elif page == "Best Day":
            show_best_day()
        elif page == "Trends":
            show_trends()
        elif page == "Media Impact":
            show_media_impact()
        elif page == "Post Recommendations":
            show_post_recommendations()
        elif page == "Data Management":
            show_data_management()


if __name__ == "__main__":
    main()
