import pandas as pd
import plotly.express as px
import streamlit as st

from src.db.session import SessionLocal
from src.core.analytics import (
    get_dashboard_stats,
    get_best_selling_products,
    get_revenue_by_product,
    get_weekly_trends,
    get_business_recommendations,
)
from src.ui.state import business_id, business_name


def show_dashboard() -> None:
    db = SessionLocal()
    try:
        stats = get_dashboard_stats(db, business_id())

        st.title(f"Dashboard - {business_name()}")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(label="Total Revenue", value=f"₹{stats['total_revenue']:,.2f}")
        with col2:
            st.metric(label="Total Profit", value=f"₹{stats['total_profit']:,.2f}")
        with col3:
            st.metric(label="Total Orders", value=f"{stats['total_orders']:,}")
        with col4:
            st.metric(label="Products", value=f"{stats['total_products']}")

        recommendations = get_business_recommendations(db, business_id())

        trend_icon = "📈" if recommendations.get("growth_trend") == "growing" else (
            "📉" if recommendations.get("growth_trend") == "declining" else "➡️"
        )

        outcome_btn = st.button(
            "🎯 VIEW YOUR ACTION ITEMS - Click to see what to do next!",
            use_container_width=True,
            type="primary",
            key="outcome_btn",
        )
        if outcome_btn:
            st.session_state.show_outcome = not st.session_state.show_outcome

        if st.session_state.show_outcome:
            st.markdown(
                f"""
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        padding: 20px; border-radius: 12px; color: white; text-align: center; margin: 16px 0;">
                <div style="font-size: 1.2rem; margin-bottom: 8px;">Business Health Score</div>
                <div style="font-size: 3rem; font-weight: bold;">{recommendations["health_score"]}/100</div>
                <div style="font-size: 1rem; opacity: 0.9; margin-top: 8px;">
                    {trend_icon} Sales {recommendations.get("growth_trend", "stable").capitalize()} | Focus: {recommendations["focus_area"]}
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )

            st.markdown("### What You Should Do Next")
            for rec in recommendations["recommendations"]:
                if rec["priority"] == "high":
                    priority_color, bg_color, border_color, priority_label = "#ef4444", "#fef2f2", "#fecaca", "HIGH PRIORITY"
                elif rec["priority"] == "medium":
                    priority_color, bg_color, border_color, priority_label = "#f59e0b", "#fffbeb", "#fde68a", "MEDIUM"
                else:
                    priority_color, bg_color, border_color, priority_label = "#10b981", "#ecfdf5", "#a7f3d0", "LOW"

                st.markdown(
                    f"""
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
                """,
                    unsafe_allow_html=True,
                )

        st.divider()

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Top Selling Products")
            best_products = get_best_selling_products(db, business_id(), 5)
            if best_products:
                df = pd.DataFrame(best_products)
                fig = px.bar(df, x="name", y="quantity_sold", color="category", title="Units Sold by Product")
                fig.update_layout(xaxis_title="", yaxis_title="Quantity Sold")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No sales data yet. Add products and sales to see insights.")

        with col2:
            st.subheader("Revenue by Product")
            revenue_data = get_revenue_by_product(db, business_id())
            if revenue_data:
                df = pd.DataFrame(revenue_data)
                fig = px.pie(df, values="revenue", names="name", title="Revenue Distribution")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No revenue data available yet.")

        st.subheader("Weekly Sales Trends")
        weekly_trends = get_weekly_trends(db, business_id(), 8)
        if weekly_trends:
            df = pd.DataFrame(weekly_trends)
            fig = px.line(df, x="week", y="revenue", markers=True, title="Revenue Over Time")
            fig.update_layout(xaxis_title="Week Starting", yaxis_title="Revenue (₹)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Not enough data for trends yet.")

    finally:
        db.close()
