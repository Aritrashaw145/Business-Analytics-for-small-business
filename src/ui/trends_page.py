import pandas as pd
import plotly.express as px
import streamlit as st

from src.db.session import SessionLocal
from src.core.analytics import get_weekly_trends, get_monthly_trends
from src.ui.state import business_id


def show_trends() -> None:
    db = SessionLocal()
    try:
        st.title("Sales Trends")
        tab1, tab2 = st.tabs(["Weekly Trends", "Monthly Trends"])

        with tab1:
            st.subheader("Weekly Sales Trends")
            weekly = get_weekly_trends(db, business_id(), 12)
            if weekly:
                df = pd.DataFrame(weekly)
                fig = px.line(df, x="week", y="revenue", markers=True, title="Weekly Revenue")
                fig.update_traces(line_color="#667eea", marker_size=10)
                fig.update_layout(xaxis_title="Week Starting", yaxis_title="Revenue (₹)")
                st.plotly_chart(fig, use_container_width=True)

                fig2 = px.bar(df, x="week", y="orders", title="Weekly Orders Count")
                fig2.update_traces(marker_color="#764ba2")
                st.plotly_chart(fig2, use_container_width=True)

                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("Not enough data for weekly trends yet.")

        with tab2:
            st.subheader("Monthly Sales Trends")
            monthly = get_monthly_trends(db, business_id(), 12)
            if monthly:
                df = pd.DataFrame(monthly)
                fig = px.area(df, x="month", y="revenue", title="Monthly Revenue")
                fig.update_traces(fill="tozeroy", line_color="#667eea")
                fig.update_layout(xaxis_title="Month", yaxis_title="Revenue (₹)")
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("Not enough data for monthly trends yet.")

    finally:
        db.close()
