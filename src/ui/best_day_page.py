import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.db.session import SessionLocal
from src.core.analytics import get_best_day_of_week
from src.ui.state import business_id


def show_best_day() -> None:
    db = SessionLocal()
    try:
        st.title("Best Day Analysis")
        best_day_data = get_best_day_of_week(db, business_id())

        if best_day_data["day"] != "N/A":
            col1, col2 = st.columns([1, 2])
            with col1:
                st.markdown("### Your Best Day")
                st.markdown(f"## {best_day_data['day']}")
                st.metric("Revenue on Best Day", f"₹{best_day_data['revenue']:,.2f}")
                st.markdown("---")
                st.info(
                    "This is the day when your business generates the most revenue. "
                    "Consider scheduling promotions or increasing staff on this day."
                )

            with col2:
                df = pd.DataFrame(best_day_data["daily_breakdown"])
                colors = ["#667eea" if day != best_day_data["day"] else "#ff6b6b" for day in df["day"]]
                fig = go.Figure(data=[go.Bar(x=df["day"], y=df["revenue"], marker_color=colors)])
                fig.update_layout(title="Revenue by Day of Week", xaxis_title="Day", yaxis_title="Revenue (₹)")
                st.plotly_chart(fig, use_container_width=True)

            st.subheader("Daily Revenue Breakdown")
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No sales data available yet. Add sales to see which day performs best.")

    finally:
        db.close()
