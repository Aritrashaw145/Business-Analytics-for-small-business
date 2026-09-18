"""
Streamlit entrypoint.

Run with: streamlit run app.py --server.port 5000

This file is intentionally thin - it only wires up page config, session
state, the database, and routes to the auth screen or the main app shell.
All actual logic lives under `src/`.
"""
import streamlit as st

from src.db.session import init_db
from src.ui.state import init_session_state
from src.ui.styles import APP_CSS
from src.ui.auth_page import show_auth_page
from src.ui.navigation import show_app

st.set_page_config(page_title="Business Analytics Dashboard", page_icon="📊", layout="wide")
st.markdown(APP_CSS, unsafe_allow_html=True)

init_db()
init_session_state()

if not st.session_state.authenticated:
    show_auth_page()
else:
    show_app()
