import pandas as pd
import plotly.express as px
import streamlit as st

from src.db.session import SessionLocal
from src.ml.prediction import get_best_posting_recommendation, get_posting_insights, get_model_status
from src.ml.training import train_post_impact_model
from src.ml.evaluation import log_prediction, get_prediction_accuracy_summary
from src.ui.state import business_id


def _render_model_status_panel(db) -> None:
    status = get_model_status(db, business_id())

    with st.expander("ML Model Status & Training", expanded=status["status"] in ("never_trained", "insufficient_data")):
        if status["status"] == "never_trained":
            st.info("No model has been trained yet. Predictions are using the plain historical-average fallback below.")
        elif status["status"] == "insufficient_data":
            st.warning("The last training attempt didn't have enough data to produce a reliable model.")
            for w in status.get("warnings", []):
                st.markdown(f"- {w}")
        else:
            st.markdown(f"**Last trained:** {status['trained_at']}")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("R² Score", f"{status['r2']:.3f}" if status.get("r2") is not None else "N/A")
            with col2:
                st.metric("Mean Abs. Error", f"₹{status['mae']:,.2f}" if status.get("mae") is not None else "N/A")
            with col3:
                st.metric("Training Data Points", status.get("data_points", 0))

            if status.get("warnings"):
                st.caption("Data quality notes from training:")
                for w in status["warnings"]:
                    st.caption(f"- {w}")

            if status.get("feature_importance"):
                st.markdown("**Top Features:**")
                for feat, imp in list(status["feature_importance"].items())[:5]:
                    st.markdown(f"- {feat}: {imp:.4f}")

        st.markdown(
            f"Since last training: **{status.get('new_sales_days_since_training', 0)}** new sales days, "
            f"**{status.get('new_posts_since_training', 0)}** new posts."
        )
        if status.get("should_retrain"):
            st.info("New data is available - retraining may improve accuracy.")

        if st.button("Train / Retrain Model", type="primary", key="train_model_btn"):
            with st.spinner("Training model on your real sales and posting history..."):
                result = train_post_impact_model(db, business_id())
                if result.get("success"):
                    st.success("Model trained successfully!")
                    st.markdown(
                        f"""
                        **Model Performance:**
                        - R² Score: {result.get('r2', 0):.3f} (higher is better, max 1.0)
                        - Mean Absolute Error: ₹{result.get('mae', 0):,.2f}
                        - Data points used: {result.get('data_points', 0)}
                        """
                    )
                    st.rerun()
                else:
                    st.error(result.get("error", "Training failed"))
                    for w in result.get("warnings", []):
                        st.markdown(f"- {w}")


def _render_accuracy_panel(db) -> None:
    summary = get_prediction_accuracy_summary(db, business_id())

    with st.expander("Recommendation Accuracy (Feedback Loop)"):
        st.markdown(
            "Every time you track a recommendation below, we compare the predicted sales uplift "
            "to what actually happened once enough time has passed. This never changes the model "
            "automatically - it's here so you (and a future retraining decision) can judge whether "
            "the model's predictions are actually holding up."
        )
        if not summary["has_data"]:
            st.info(
                f"No evaluated recommendations yet ({summary['pending_count']} pending). "
                "Click 'Track This Recommendation' below to start building a track record."
            )
            return

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Evaluated Recommendations", summary["evaluated_count"])
        with col2:
            st.metric("Within ±20pp of Actual", f"{summary['accuracy_within_20pp_percent']:.0f}%")

        if summary.get("mean_absolute_error") is not None:
            st.caption(f"Mean absolute error on daily revenue: ₹{summary['mean_absolute_error']:,.2f}")
        st.caption(f"{summary['pending_count']} more recommendations awaiting their outcome window.")

        if summary["recent"]:
            st.dataframe(pd.DataFrame(summary["recent"]), use_container_width=True, hide_index=True)


def show_post_recommendations() -> None:
    db = SessionLocal()
    try:
        st.title("Post Recommendations")
        st.markdown("Get data-driven recommendations for when to post based on **sales impact**, not just engagement.")

        recommendation = get_best_posting_recommendation(db, business_id())

        if recommendation.get("error"):
            st.warning(recommendation.get("message", "Add more posts and sales data to get personalized recommendations."))
            st.markdown(
                """
            ### How This Works

            Unlike typical social media analytics that focus on likes and engagement,
            this feature analyzes your **actual sales data** to find:

            - **Best Day**: Which day of the week leads to highest sales after posting
            - **Best Time**: Morning, afternoon, or evening - when posting drives the most revenue
            - **Best Content Type**: Whether reels, stories, or images generate more sales

            **To get started:**
            1. Add at least 3 media posts in Data Management
            2. Record sales for at least 30 days
            3. Come back to see personalized recommendations
            """
            )
        else:
            best = recommendation.get("best_overall", {})
            post_type = best.get("post_type", "reel")
            day = best.get("day", "Friday")
            uplift = best.get("expected_uplift_percent", 0)

            st.markdown(
                f"""
            <div style="background: linear-gradient(135deg, #10b981 0%, #059669 100%);
                        padding: 24px; border-radius: 16px; color: white; margin-bottom: 24px;">
                <div style="font-size: 1.1rem; opacity: 0.9; margin-bottom: 8px;">AI Recommendation</div>
                <div style="font-size: 1.6rem; font-weight: bold; margin-bottom: 12px;">
                    If you post a {post_type} on {day} evening, your sales are likely to increase by ~{uplift:.0f}%
                </div>
                <div style="font-size: 1rem; opacity: 0.9; margin-top: 8px;">
                    Confidence: {best.get('confidence', 'medium').capitalize()} | Based on your actual sales data
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )

            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(
                    f"""
                <div style="background: #f0fdf4; padding: 20px; border-radius: 12px; text-align: center; border: 2px solid #10b981;">
                    <div style="font-size: 0.9rem; color: #666;">Best Day</div>
                    <div style="font-size: 1.5rem; font-weight: bold; color: #10b981;">{recommendation.get('best_day', 'Friday')}</div>
                </div>
                """,
                    unsafe_allow_html=True,
                )
            with col2:
                st.markdown(
                    f"""
                <div style="background: #eff6ff; padding: 20px; border-radius: 12px; text-align: center; border: 2px solid #3b82f6;">
                    <div style="font-size: 0.9rem; color: #666;">Best Time</div>
                    <div style="font-size: 1.5rem; font-weight: bold; color: #3b82f6;">{recommendation.get('best_time', 'Evening')}</div>
                </div>
                """,
                    unsafe_allow_html=True,
                )
            with col3:
                st.markdown(
                    f"""
                <div style="background: #fef3c7; padding: 20px; border-radius: 12px; text-align: center; border: 2px solid #f59e0b;">
                    <div style="font-size: 0.9rem; color: #666;">Best Content Type</div>
                    <div style="font-size: 1.5rem; font-weight: bold; color: #f59e0b;">{recommendation.get('best_post_type', 'Reel').capitalize()}</div>
                </div>
                """,
                    unsafe_allow_html=True,
                )

            if st.button("📌 Track This Recommendation", help="Log this prediction so we can check it against real sales later"):
                log_prediction(
                    db,
                    business_id(),
                    day_of_week=best.get("day_of_week", 0),
                    post_type=post_type,
                    predicted_daily_revenue=best.get("expected_revenue", 0),
                    predicted_uplift_percent=uplift,
                    confidence=best.get("confidence", "medium"),
                )
                st.success("Tracked! Come back after the target day to see how the prediction held up.")

            st.divider()

            st.subheader("Top 5 Posting Scenarios")
            st.markdown("Ranked by expected sales impact")
            top_scenarios = recommendation.get("top_5_scenarios", [])
            if top_scenarios:
                scenario_data = [
                    {
                        "Rank": i,
                        "Day": s["day"],
                        "Post Type": s["post_type"].capitalize(),
                        "Expected Uplift": f"+{s['uplift_percent']:.1f}%",
                        "Expected Revenue": f"₹{s['expected_revenue']:,.0f}",
                        "Confidence": s.get("confidence", "medium").capitalize(),
                    }
                    for i, s in enumerate(top_scenarios, 1)
                ]
                st.dataframe(pd.DataFrame(scenario_data), use_container_width=True, hide_index=True)

            st.divider()

            insights = get_posting_insights(db, business_id())
            if insights.get("has_data"):
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("Performance by Day")
                    day_data = insights.get("day_performance", [])
                    if day_data:
                        df = pd.DataFrame(day_data)
                        fig = px.bar(
                            df, x="day", y="avg_lift", color="avg_lift", color_continuous_scale="RdYlGn",
                            title="Average Sales Lift by Day",
                        )
                        fig.update_layout(xaxis_title="Day", yaxis_title="Avg Sales Lift %")
                        st.plotly_chart(fig, use_container_width=True)
                with col2:
                    st.subheader("Performance by Content Type")
                    type_data = insights.get("type_performance", [])
                    if type_data:
                        df = pd.DataFrame(type_data)
                        fig = px.bar(
                            df, x="type", y="avg_lift", color="type",
                            color_discrete_map={"reel": "#667eea", "story": "#feca57", "image": "#10b981"},
                            title="Average Sales Lift by Content Type",
                        )
                        fig.update_layout(xaxis_title="Content Type", yaxis_title="Avg Sales Lift %")
                        st.plotly_chart(fig, use_container_width=True)

            st.markdown("---")
            st.markdown(
                """
            ### How It Works

            This recommendation engine analyzes the relationship between your **posting activity**
            and **actual sales revenue**, not just likes or engagement metrics.

            The system:
            1. Compares sales in the 3 days after each post to the 7-day baseline before
            2. Identifies patterns in which days, times, and content types drive the most sales
            3. Uses machine learning (when trained) to predict expected revenue for different scenarios

            **Key insight**: A post that gets fewer likes but drives more sales is more valuable to your business!
            """
            )

        st.divider()
        _render_model_status_panel(db)
        _render_accuracy_panel(db)

    finally:
        db.close()
