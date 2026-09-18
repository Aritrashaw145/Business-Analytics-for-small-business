"""Small helpers for initializing and reading Streamlit session state."""
from __future__ import annotations

import streamlit as st


def init_session_state() -> None:
    defaults = {
        "authenticated": False,
        "business_id": None,
        "business_name": None,
        "current_page": "Dashboard",
        "show_outcome": False,
        "data_mgmt_tab": "Add Products",
        "import_step": 1,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def logout() -> None:
    st.session_state.authenticated = False
    st.session_state.business_id = None
    st.session_state.business_name = None


def business_id() -> int:
    return st.session_state.business_id


def business_name() -> str:
    return st.session_state.business_name
