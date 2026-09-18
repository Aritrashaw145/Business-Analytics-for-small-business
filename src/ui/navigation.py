import streamlit as st

from src.ui.state import business_name, logout
from src.ui.dashboard_page import show_dashboard
from src.ui.product_analytics_page import show_products_analytics
from src.ui.best_day_page import show_best_day
from src.ui.trends_page import show_trends
from src.ui.media_impact_page import show_media_impact
from src.ui.post_recommendations_page import show_post_recommendations
from src.ui.data_management_page import show_data_management

PAGES = {
    "Dashboard": show_dashboard,
    "Product Analytics": show_products_analytics,
    "Best Day": show_best_day,
    "Sales Trends": show_trends,
    "Media Impact": show_media_impact,
    "Post Recommendations": show_post_recommendations,
    "Data Management": show_data_management,
}


def show_app() -> None:
    with st.sidebar:
        st.markdown(f"### {business_name()}")
        st.divider()

        for page_name in PAGES:
            if st.button(page_name, use_container_width=True, key=f"nav_{page_name}"):
                st.session_state.current_page = page_name

        st.divider()
        if st.button("Logout", use_container_width=True):
            logout()
            st.rerun()

    page_fn = PAGES.get(st.session_state.current_page, show_dashboard)
    page_fn()
