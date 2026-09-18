from datetime import date

import pandas as pd
import streamlit as st

from src.db.session import SessionLocal
from src.db.models import Product, Sale, MediaPost
from src.core.validation import validate_product, validate_sale, validate_media_post, VALID_CATEGORIES, VALID_POST_TYPES
from src.core.csv_import import import_products_csv, import_sales_csv, import_media_posts_csv
from src.core.demo_data import generate_demo_data, clear_demo_data
from src.ui.state import business_id


def _add_products_tab(db) -> None:
    st.subheader("Add a Product")
    with st.form("add_product_form", clear_on_submit=True):
        name = st.text_input("Product Name")
        col1, col2 = st.columns(2)
        with col1:
            cost_price = st.number_input("Cost Price (₹)", min_value=0.0, step=1.0)
        with col2:
            selling_price = st.number_input("Selling Price (₹)", min_value=0.0, step=1.0)
        category = st.selectbox("Category", VALID_CATEGORIES)
        submit = st.form_submit_button("Add Product", type="primary")

        if submit:
            validation = validate_product(name, cost_price, selling_price, category)
            if not validation.is_valid:
                for e in validation.errors:
                    st.error(e)
            else:
                c = validation.cleaned
                product = Product(
                    business_id=business_id(), name=c["name"], cost_price=c["cost_price"],
                    selling_price=c["selling_price"], category=c["category"],
                )
                db.add(product)
                db.commit()
                st.success(f"Added product: {c['name']}")

    st.divider()
    st.subheader("Your Products")
    products = db.query(Product).filter(Product.business_id == business_id()).all()
    if products:
        df = pd.DataFrame(
            [{"Name": p.name, "Category": p.category, "Cost": p.cost_price, "Price": p.selling_price} for p in products]
        )
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No products added yet.")


def _add_sales_tab(db) -> None:
    st.subheader("Record a Sale")
    products = db.query(Product).filter(Product.business_id == business_id()).all()

    if not products:
        st.warning("Add at least one product before recording sales.")
        return

    with st.form("add_sale_form", clear_on_submit=True):
        product_options = {p.name: p.id for p in products}
        product_name = st.selectbox("Product", list(product_options.keys()))
        col1, col2 = st.columns(2)
        with col1:
            quantity = st.number_input("Quantity", min_value=1, step=1, value=1)
        with col2:
            sale_date = st.date_input("Sale Date", value=date.today(), max_value=date.today())
        submit = st.form_submit_button("Record Sale", type="primary")

        if submit:
            product_id = product_options[product_name]
            validation = validate_sale(quantity, sale_date, product_id=product_id)
            if not validation.is_valid:
                for e in validation.errors:
                    st.error(e)
            else:
                c = validation.cleaned
                product = db.query(Product).get(product_id)
                sale = Sale(
                    product_id=product_id, quantity=c["quantity"],
                    total_amount=round(c["quantity"] * product.selling_price, 2), sale_date=c["sale_date"],
                )
                db.add(sale)
                db.commit()
                st.success(f"Recorded sale: {c['quantity']} x {product_name}")


def _add_media_post_tab(db) -> None:
    st.subheader("Track a Social Media Post")
    with st.form("add_media_form", clear_on_submit=True):
        post_type = st.selectbox("Post Type", VALID_POST_TYPES)
        caption = st.text_input("Caption (optional)")
        col1, col2 = st.columns(2)
        with col1:
            posted_at = st.date_input("Post Date", value=date.today(), max_value=date.today())
        with col2:
            post_time = st.time_input("Post Time (optional)", value=None)
        platform = st.selectbox("Platform", ["instagram", "facebook", "tiktok", "other"])

        col3, col4, col5, col6 = st.columns(4)
        with col3:
            impressions = st.number_input("Impressions", min_value=0, step=1)
        with col4:
            likes = st.number_input("Likes", min_value=0, step=1)
        with col5:
            comments = st.number_input("Comments", min_value=0, step=1)
        with col6:
            shares = st.number_input("Shares", min_value=0, step=1)

        submit = st.form_submit_button("Add Post", type="primary")

        if submit:
            validation = validate_media_post(
                post_type, posted_at, caption, post_time, platform, impressions, likes, comments, shares
            )
            if not validation.is_valid:
                for e in validation.errors:
                    st.error(e)
            else:
                c = validation.cleaned
                post = MediaPost(business_id=business_id(), **c)
                db.add(post)
                db.commit()
                st.success("Post added!")

    st.divider()
    st.subheader("Your Recent Posts")
    posts = (
        db.query(MediaPost).filter(MediaPost.business_id == business_id())
        .order_by(MediaPost.posted_at.desc()).limit(10).all()
    )
    if posts:
        df = pd.DataFrame(
            [
                {"Date": p.posted_at.strftime("%Y-%m-%d"), "Type": p.post_type, "Caption": p.caption,
                 "Likes": p.likes, "Comments": p.comments, "Shares": p.shares}
                for p in posts
            ]
        )
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No posts tracked yet.")


def _import_csv_tab(db) -> None:
    st.subheader("Bulk Import via CSV")

    import_type = st.selectbox("What are you importing?", ["Products", "Sales", "Media Posts"])

    columns_help = {
        "Products": "Required columns: `name`, `cost_price`, `selling_price`. Optional: `category`.",
        "Sales": "Required columns: `product_name`, `quantity`, `sale_date`. Product names must match existing products.",
        "Media Posts": "Required columns: `post_type` (reel/story/image), `posted_at`. Optional: `caption`, `post_time`, `platform`, `impressions`, `likes`, `comments`, `shares`.",
    }
    st.caption(columns_help[import_type])

    uploaded = st.file_uploader("Upload CSV file", type=["csv"], key=f"upload_{import_type}")
    if uploaded is None:
        return

    try:
        df = pd.read_csv(uploaded)
    except Exception as e:
        st.error(f"Could not read this file as CSV: {e}")
        return

    if st.button("Import", type="primary"):
        with st.spinner("Validating and importing..."):
            if import_type == "Products":
                result = import_products_csv(db, business_id(), df)
            elif import_type == "Sales":
                result = import_sales_csv(db, business_id(), df)
            else:
                result = import_media_posts_csv(db, business_id(), df)

        if result.missing_columns:
            st.error(f"Missing required columns: {', '.join(result.missing_columns)}. No rows were imported.")
            return

        if result.imported_count:
            st.success(f"Imported {result.imported_count} row(s) successfully.")
        if result.rejected:
            st.warning(f"{len(result.rejected)} row(s) were rejected. No data was lost - see details below.")
            st.dataframe(result.rejected_dataframe(), use_container_width=True, hide_index=True)
        if not result.imported_count and not result.rejected:
            st.info("The file had no data rows.")


def _demo_data_tab(db) -> None:
    st.subheader("Demo Data")
    st.markdown(
        "Populate this account with realistic sample products, sales, and posts so you can explore "
        "every feature before entering your own data. Demo data is only ever generated for an account "
        "that has no products yet, so it can't be mixed into your real records."
    )

    existing_products = db.query(Product).filter(Product.business_id == business_id()).count()

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Generate Demo Data", disabled=existing_products > 0):
            with st.spinner("Generating 90 days of sample data..."):
                created = generate_demo_data(db, business_id())
            if created:
                st.success("Demo data generated! Explore the Dashboard and other screens.")
                st.rerun()
            else:
                st.warning("This account already has products - demo data was not generated.")

    with col2:
        if st.button("Clear All Data", type="secondary"):
            st.session_state["confirm_clear"] = True

    if st.session_state.get("confirm_clear"):
        st.error("This will permanently delete all products, sales, and posts for this account.")
        col3, col4 = st.columns(2)
        with col3:
            if st.button("Yes, delete everything", type="primary"):
                clear_demo_data(db, business_id())
                st.session_state["confirm_clear"] = False
                st.success("All data cleared.")
                st.rerun()
        with col4:
            if st.button("Cancel"):
                st.session_state["confirm_clear"] = False
                st.rerun()

    if existing_products > 0:
        st.info(f"This account already has {existing_products} product(s).")


def show_data_management() -> None:
    db = SessionLocal()
    try:
        st.title("Data Management")
        tab1, tab2, tab3, tab4, tab5 = st.tabs(
            ["Add Products", "Add Sales", "Add Media Post", "Import CSV", "Demo Data"]
        )
        with tab1:
            _add_products_tab(db)
        with tab2:
            _add_sales_tab(db)
        with tab3:
            _add_media_post_tab(db)
        with tab4:
            _import_csv_tab(db)
        with tab5:
            _demo_data_tab(db)
    finally:
        db.close()
