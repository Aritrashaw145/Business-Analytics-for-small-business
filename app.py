"""
Streamlit entrypoint.

Run with: streamlit run app.py --server.port 5000

This file is intentionally thin - it only wires up page config, session
state, the database, and routes to the auth screen or the main app shell.
All actual logic lives under `src/`.
"""
import streamlit as st

from src.auth.service import create_business, get_business_by_email
from src.config import settings
from src.core.demo_data import generate_demo_data
from src.db.session import SessionLocal, init_db
from src.ui.state import init_session_state
from src.ui.styles import APP_CSS
from src.ui.auth_page import show_auth_page
from src.ui.navigation import show_app

st.set_page_config(page_title="Business Analytics Dashboard", page_icon="📊", layout="wide")
st.markdown(APP_CSS, unsafe_allow_html=True)

init_db()


def ensure_demo_account() -> None:
    """Create the public demo account and seed it once on a fresh database."""
    db = SessionLocal()
    try:
        demo_business = get_business_by_email(db, settings.demo_email)
        if demo_business is None:
            demo_business = create_business(
                db,
                name="Demo Business",
                owner_name="Demo User",
                email=settings.demo_email,
                password=settings.demo_password,
                category="Retail",
            )
        # This is a no-op once the demo business has products, so it never
        # overwrites the existing demo dataset on reruns.
        generate_demo_data(db, demo_business.id)
    finally:
        db.close()


ensure_demo_account()
init_session_state()

if not st.session_state.authenticated:
    show_auth_page()
else:
    show_app()
