import streamlit as st

from src.config import settings
from src.db.session import SessionLocal
from src.auth.service import authenticate_business, create_business, get_business_by_email
from src.core.validation import validate_signup


def show_auth_page() -> None:
    st.title("Business Analytics Dashboard")
    st.markdown("Track your sales, identify trends, and grow your business with actionable insights.")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        tab1, tab2 = st.tabs(["Login", "Register"])

        with tab1:
            st.subheader("Welcome Back")
            st.caption(f"Demo: {settings.demo_email} / {settings.demo_password}")
            with st.form("login_form"):
                email = st.text_input("Email", placeholder=settings.demo_email, key="login_email")
                password = st.text_input("Password", type="password", placeholder=settings.demo_password, key="login_password")
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
                category = st.selectbox(
                    "Business Category", ["Retail", "Food & Beverage", "Services", "E-commerce", "Other"], key="reg_category"
                )
                email = st.text_input("Email", key="reg_email")
                password = st.text_input("Password", type="password", key="reg_password")
                confirm_password = st.text_input("Confirm Password", type="password", key="reg_confirm")
                submit = st.form_submit_button("Create Account", use_container_width=True)

                if submit:
                    validation = validate_signup(business_name, owner_name, email, password, confirm_password)
                    if not validation.is_valid:
                        for error in validation.errors:
                            st.error(error)
                    else:
                        c = validation.cleaned
                        db = SessionLocal()
                        try:
                            existing = get_business_by_email(db, c["email"])
                            if existing:
                                st.error("An account with this email already exists")
                            else:
                                business = create_business(
                                    db, c["business_name"], c["owner_name"], c["email"], c["password"], category
                                )
                                st.session_state.authenticated = True
                                st.session_state.business_id = business.id
                                st.session_state.business_name = business.name
                                st.success("Account created successfully!")
                                st.rerun()
                        finally:
                            db.close()
