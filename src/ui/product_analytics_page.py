import pandas as pd
import plotly.express as px
import streamlit as st

from src.db.session import SessionLocal
from src.core.analytics import get_best_selling_products, get_most_profitable_products, get_low_performing_products
from src.ui.state import business_id


def show_products_analytics() -> None:
    db = SessionLocal()
    try:
        st.title("Product Analytics")
        tab1, tab2, tab3 = st.tabs(["Best Sellers", "Most Profitable", "Low Performers"])

        with tab1:
            st.subheader("Best Selling Products")
            st.markdown("Products ranked by total quantity sold")
            best_products = get_best_selling_products(db, business_id(), 10)
            if best_products:
                df = pd.DataFrame(best_products)
                fig = px.bar(
                    df, x="quantity_sold", y="name", orientation="h", color="revenue",
                    color_continuous_scale="Viridis", title="Top 10 Best Selling Products",
                )
                fig.update_layout(yaxis={"categoryorder": "total ascending"})
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("No sales data available yet.")

        with tab2:
            st.subheader("Most Profitable Products")
            st.markdown("Products ranked by total profit generated")
            profitable = get_most_profitable_products(db, business_id(), 10)
            if profitable:
                df = pd.DataFrame(profitable)
                fig = px.bar(
                    df, x="profit", y="name", orientation="h", color="profit_margin",
                    color_continuous_scale="RdYlGn", title="Top 10 Most Profitable Products",
                )
                fig.update_layout(yaxis={"categoryorder": "total ascending"})
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("No profit data available yet.")

        with tab3:
            st.subheader("Low Performing Products")
            st.markdown("Products with lowest revenue in the last 30 days")
            low_performers = get_low_performing_products(db, business_id(), 10)
            if low_performers:
                df = pd.DataFrame(low_performers)
                fig = px.bar(
                    df, x="revenue", y="name", orientation="h", color="quantity_sold",
                    color_continuous_scale="Reds_r", title="Low Performing Products (Last 30 Days)",
                )
                fig.update_layout(yaxis={"categoryorder": "total descending"})
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("No product data available yet.")

    finally:
        db.close()
