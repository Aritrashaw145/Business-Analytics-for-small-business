import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
import io
import csv

from models import init_db, SessionLocal, Product, Sale
from auth import create_business, authenticate_business, get_business_by_email
from analytics import (
    get_dashboard_stats,
    get_best_selling_products,
    get_most_profitable_products,
    get_best_day_of_week,
    get_weekly_trends,
    get_monthly_trends,
    get_low_performing_products,
    get_revenue_by_product
)
from demo_data import generate_demo_data, clear_demo_data

init_db()

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
            with st.form("login_form"):
                email = st.text_input("Email", key="login_email")
                password = st.text_input("Password", type="password", key="login_password")
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
                value=f"${stats['total_revenue']:,.2f}",
                delta=None
            )
        
        with col2:
            st.metric(
                label="Total Profit",
                value=f"${stats['total_profit']:,.2f}",
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
            fig.update_layout(xaxis_title="Week Starting", yaxis_title="Revenue ($)")
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
                st.metric("Revenue on Best Day", f"${best_day_data['revenue']:,.2f}")
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
                    yaxis_title="Revenue ($)"
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
                fig.update_layout(xaxis_title="Week Starting", yaxis_title="Revenue ($)")
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
                fig.update_layout(xaxis_title="Month", yaxis_title="Revenue ($)")
                st.plotly_chart(fig, use_container_width=True)
                
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("Not enough data for monthly trends yet.")
                
    finally:
        db.close()


def show_data_management():
    db = SessionLocal()
    try:
        st.title("Data Management")
        
        tab1, tab2, tab3 = st.tabs(["Products", "Add Sale", "Import Data"])
        
        with tab1:
            st.subheader("Your Products")
            
            with st.expander("Add New Product"):
                with st.form("add_product"):
                    col1, col2 = st.columns(2)
                    with col1:
                        name = st.text_input("Product Name")
                        category = st.selectbox("Category", 
                            ["Beverages", "Bakery", "Pantry", "Breakfast", "Snacks", "Other"])
                    with col2:
                        cost_price = st.number_input("Cost Price ($)", min_value=0.01, step=0.01)
                        selling_price = st.number_input("Selling Price ($)", min_value=0.01, step=0.01)
                    
                    if st.form_submit_button("Add Product"):
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
                            st.error("Please fill in all fields correctly")
            
            products = db.query(Product).filter(
                Product.business_id == st.session_state.business_id
            ).all()
            
            if products:
                product_data = [{
                    "ID": p.id,
                    "Name": p.name,
                    "Category": p.category,
                    "Cost Price": f"${p.cost_price:.2f}",
                    "Selling Price": f"${p.selling_price:.2f}",
                    "Margin": f"{((p.selling_price - p.cost_price) / p.selling_price * 100):.1f}%"
                } for p in products]
                st.dataframe(pd.DataFrame(product_data), use_container_width=True, hide_index=True)
            else:
                st.info("No products added yet.")
        
        with tab2:
            st.subheader("Record a Sale")
            
            products = db.query(Product).filter(
                Product.business_id == st.session_state.business_id
            ).all()
            
            if products:
                with st.form("add_sale"):
                    product_options = {p.name: p.id for p in products}
                    selected_product = st.selectbox("Product", list(product_options.keys()))
                    quantity = st.number_input("Quantity", min_value=1, value=1)
                    sale_date = st.date_input("Sale Date", value=datetime.now().date())
                    
                    if st.form_submit_button("Record Sale"):
                        product = next(p for p in products if p.name == selected_product)
                        total_amount = quantity * product.selling_price
                        
                        sale = Sale(
                            product_id=product.id,
                            quantity=quantity,
                            total_amount=total_amount,
                            sale_date=sale_date
                        )
                        db.add(sale)
                        db.commit()
                        st.success(f"Sale recorded: {quantity}x {selected_product} = ${total_amount:.2f}")
                        st.rerun()
            else:
                st.warning("Please add products first before recording sales.")
        
        with tab3:
            st.subheader("Import Sales Data (CSV)")
            
            st.markdown("""
            Upload a CSV file with the following columns:
            - `product_name`: Name of the product
            - `quantity`: Number of units sold
            - `sale_date`: Date of sale (YYYY-MM-DD format)
            """)
            
            uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
            
            if uploaded_file is not None:
                try:
                    df = pd.read_csv(uploaded_file)
                    st.dataframe(df.head(), use_container_width=True)
                    
                    if st.button("Import Sales"):
                        products = db.query(Product).filter(
                            Product.business_id == st.session_state.business_id
                        ).all()
                        product_map = {p.name.lower(): p for p in products}
                        
                        imported = 0
                        errors = 0
                        
                        for _, row in df.iterrows():
                            product_name = str(row.get('product_name', '')).lower()
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
                        
                        db.commit()
                        st.success(f"Imported {imported} sales. {errors} rows skipped (product not found).")
                        
                except Exception as e:
                    st.error(f"Error processing file: {str(e)}")
            
            st.divider()
            
            st.subheader("Demo Data")
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("Load Demo Data", use_container_width=True):
                    if generate_demo_data(db, st.session_state.business_id):
                        st.success("Demo data loaded successfully!")
                        st.rerun()
                    else:
                        st.warning("Demo data already exists for this account.")
            
            with col2:
                if st.button("Clear All Data", use_container_width=True, type="secondary"):
                    clear_demo_data(db, st.session_state.business_id)
                    st.success("All data cleared.")
                    st.rerun()
                    
    finally:
        db.close()


def main():
    if not st.session_state.authenticated:
        show_auth_page()
    else:
        with st.sidebar:
            st.title("Navigation")
            st.markdown(f"**{st.session_state.business_name}**")
            st.divider()
            
            page = st.radio(
                "Go to",
                ["Dashboard", "Product Analytics", "Best Day", "Trends", "Data Management"],
                label_visibility="collapsed"
            )
            
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
        elif page == "Data Management":
            show_data_management()


if __name__ == "__main__":
    main()
