# Business Analytics Dashboard — Project Guide

## Overview

A full-stack analytics application for small businesses. Owners manage
products and sales data, then use the dashboard to understand revenue,
profit, product performance, daily patterns, sales trends, media impact,
and recommended posting times based on **expected sales uplift** — not
just engagement.

## Tech Stack

- **Frontend:** Streamlit (Python)
- **Database:** PostgreSQL, with a SQLite fallback for local development
- **ORM:** SQLAlchemy
- **Charts:** Plotly
- **Machine learning:** scikit-learn (`GradientBoostingRegressor`)
- **Authentication:** bcrypt password hashing and session-based auth
- **Testing:** pytest, with an in-memory SQLite database per test

## Project Structure

```text
├── app.py                      # Streamlit entrypoint (thin - wires pages together)
├── src/
│   ├── config.py                # Env var loading in one place
│   ├── db/
│   │   ├── models.py             # Business, Product, Sale, MediaPost, ModelRun, PredictionLog
│   │   ├── session.py            # Engine/session setup, init_db()
│   │   └── migrations.py         # Additive, idempotent schema migrations
│   ├── auth/
│   │   └── service.py            # Hashing, signup, login
│   ├── core/
│   │   ├── validation.py         # All input validation (forms + CSV)
│   │   ├── csv_import.py         # CSV import with row-level error reporting
│   │   ├── analytics.py          # Dashboard/product/trend/media-impact calculations
│   │   └── demo_data.py          # Demo data generation and clearing
│   ├── ml/
│   │   ├── features.py           # Feature engineering from real Sale/MediaPost rows
│   │   ├── data_quality.py       # Pre-training data-quality gate
│   │   ├── training.py           # The only place a model is ever fit
│   │   ├── storage.py            # Model pickle + ModelRun audit-trail persistence
│   │   ├── prediction.py         # Recommendation logic (model-based or fallback)
│   │   └── evaluation.py         # Feedback loop: log predictions, compare to outcomes
│   └── ui/                       # One Streamlit screen per file
│       ├── state.py, styles.py, navigation.py
│       ├── auth_page.py, dashboard_page.py, product_analytics_page.py
│       ├── best_day_page.py, trends_page.py, media_impact_page.py
│       ├── post_recommendations_page.py, data_management_page.py
├── tests/                       # pytest suite (unit + integration)
├── docs/
│   └── TEST_CHECKLIST.md         # Manual test checklist with real sample data
├── requirements.txt / pyproject.toml
├── .env.example
└── .streamlit/config.toml
```

## Core Rules

1. **Tenant isolation.** Every query and mutation is scoped to the
   authenticated business (`business_id`). See the isolation tests in
   `tests/test_data_isolation.py`.
2. **Business-critical calculations.** Sales, profit, and recommendation
   math prefer clear, testable logic over clever shortcuts. Profit is
   always `(selling_price - cost_price) * quantity`.
3. **Passwords.** Stored only as bcrypt hashes. Nothing logs a password,
   password hash, or session secret.
4. **Validation.** All user-entered product, sale, CSV, and media-post
   data is validated before saving (`src/core/validation.py`).
5. **Graceful empty/partial states.** The dashboard shows useful empty
   states rather than failing on missing data.
6. **Database portability.** PostgreSQL in production; SQLite fallback for
   local development (`src/config.py`, `src/db/session.py`).
7. **Separation of responsibility.** UI code, persistence models,
   analytics, authentication, and ML logic are separated into their own
   packages (see Project Structure above).

## Feature Rules

### Authentication

- Every business-specific screen and action requires authentication.
- Signup/login use hashed passwords and session-based access
  (`st.session_state`).
- One business can never view or edit another business's data.

### Dashboard and Analytics

- Total revenue, total profit, order count, and product count are always
  shown clearly.
- Profit = `(selling_price - cost_price) × quantity`.
- Best-selling products, most-profitable products, low performers, best
  day of week, and weekly/monthly trends are all supported.
- Currency is formatted with `₹` and explicit date ranges are shown on
  charts and tables.

### Data Management

- A guided Demo Data flow lets a new account explore every feature before
  entering real data — and refuses to run on an account that already has
  products, so demo and real data never mix.
- Product/sale/media-post entry uses the same validators as CSV import, so
  a form typo and a CSV typo get the same message.
- CSV import validates columns, types, dates, and row-level values before
  writing anything; rejected rows are reported with a row number and
  reason instead of being silently dropped (`src/core/csv_import.py`).

### Media Impact and Recommendations

- Every media post tracks type, caption, posting date/time, platform, and
  engagement metrics.
- Recommendations are ranked by observed or predicted **sales uplift**,
  never by engagement alone.
- A recommendation is never presented as reliable when historical data is
  insufficient — the UI shows the limitation and a practical fallback (the
  plain slot-average analysis) instead of a bare number.
- Model retraining is always explicit and the UI always shows when the
  current model was last trained, along with its performance.

## How the ML System Stays Controlled

This was a specific requirement, so it's worth spelling out exactly how
the pieces enforce it:

- **Training is manual only.** `src/ml/training.py:train_post_impact_model`
  is invoked only by an explicit user action (the "Train / Retrain Model"
  button, or a script). Nothing anywhere retrains automatically or edits
  model weights on a schedule.
- **Training reads real data only.** `src/ml/features.py:get_sales_features`
  builds its feature table entirely from `Sale` and `MediaPost` rows —
  actual transactions and actual posts. Predictions and recommendations
  are never fed back in as training features, so a bad prediction can't
  bias the next training run.
- **A data-quality gate runs before every training attempt**
  (`src/ml/data_quality.py`). Below `MIN_TRAINING_DAYS` days of sales
  history or `MIN_TRAINING_POSTS` tracked posts (both in `.env`), training
  is refused outright rather than producing an unreliable model, and the
  refusal is logged (see below) with the specific reason.
- **Every training attempt is permanently recorded** in the `model_runs`
  table (`src/db/models.py`) — trained_at, status, data points, sales
  days, post count, MAE, R², feature importance, and any data-quality
  warnings — whether it succeeded, failed, or was refused for insufficient
  data. This is what lets the UI show training status/date/performance
  without ever unpickling a model, and what keeps a failed retrain from
  silently taking a good model out of service (a failed attempt is
  recorded but never marked "active").
- **The feedback loop is read-only with respect to training.**
  `src/ml/evaluation.py` logs a prediction (`log_prediction`) tied to a
  concrete future date, and once that date has passed, compares it to
  what actually happened in real `Sale` rows (`evaluate_predictions`).
  `get_prediction_accuracy_summary` surfaces this in the UI so a human can
  judge whether the model is worth trusting and decide whether to
  retrain — the evaluation itself never touches model weights or writes
  anything used as a training feature.
- **Confidence is never overstated.** A recommendation's `confidence`
  field is `"low"` whenever there's no trained model (the plain
  before/after slot-average fallback is used instead), and is derived
  from the trained model's own held-out R² otherwise.

## Development Loop

For each feature or defect:

1. Define the user outcome, acceptance criteria, and affected data
   boundaries.
2. Inspect the existing model, analytics, UI, and tests before changing
   code.
3. Implement the smallest complete change that satisfies the criteria.
4. Add or update focused tests for the intended behavior and edge cases.
5. Run the relevant test suite (`pytest`) and manually verify the affected
   Streamlit flow (see `docs/TEST_CHECKLIST.md`).
6. Review calculations, authentication scope, empty states, and error
   handling.
7. Document any schema migration, configuration change, or retraining
   requirement.

Do not begin unrelated refactors during a feature loop. Record follow-up
work separately.

## Testing

```bash
pip install -e ".[dev]"     # or: pip install -r requirements.txt pytest pytest-cov
pytest                       # run the full suite
pytest --cov=src --cov-report=term-missing   # with coverage
```

The suite is organized by concern:

- `tests/test_auth.py` — hashing, signup/login, credential validation
- `tests/test_validation.py` — every validator, normal/empty/invalid/
  boundary cases
- `tests/test_analytics.py` — revenue/profit/trend calculations and
  cross-business isolation
- `tests/test_csv_import.py` — valid files, missing columns, malformed and
  partially-invalid rows
- `tests/test_ml_features.py` — feature engineering shape and correctness
- `tests/test_ml_training.py` — insufficient-data refusal, successful
  training, audit trail, "failed retrain doesn't lose the last good model"
- `tests/test_ml_evaluation.py` — the feedback loop: logging, evaluation
  timing, accuracy aggregation, read-only guarantee
- `tests/test_data_isolation.py` — cross-cutting isolation checks across
  analytics, CSV import, ML features, trained models, and prediction logs
- `tests/test_integration_flows.py` — end-to-end flows: signup → data
  entry → dashboard; CSV import → analytics; demo data → clear; full ML
  train → recommend → track → evaluate loop

See `docs/TEST_CHECKLIST.md` for the manual, click-through checklist to
run with real sample data before calling a change complete.

## Completion Rules

A change is complete only when:

- The agreed user outcome and acceptance criteria are met.
- The relevant automated tests pass.
- The changed Streamlit workflow works in a manual check
  (`docs/TEST_CHECKLIST.md`).
- Calculations and business scoping are reviewed for correctness.
- Empty states, validation errors, and failure paths have been handled.
- Documentation, environment variables, migrations, and model-retraining
  instructions are updated when affected.
- No secrets, temporary diagnostics, or unrelated code changes remain.

## Major Changes

Treat the following as major changes and plan them explicitly before
implementation — define migration and rollback steps, back up affected
data, test with representative historical records, and document
user-visible effects before release:

- Database schema or migration changes
- Authentication, authorization, or session-management changes
- Changes to revenue, profit, sales attribution, or uplift formulas
- CSV import/export format changes
- ML model, training-data, feature-engineering, or recommendation-logic
  changes
- Replacing the database backend or changing deployment configuration
- Any change that affects existing businesses' historical data

## Data Model

### Business
`id`, `name`, `owner_name`, `email`, `password_hash`, `category`, `created_at`

### Product
`id`, `business_id`, `name`, `cost_price`, `selling_price`, `category`

### Sale
`id`, `product_id`, `quantity`, `total_amount`, `sale_date`, `sale_time` (optional)

### MediaPost
`id`, `business_id`, `post_type`, `caption`, `posted_at`, `post_time`, `platform`, `impressions`, `likes`, `comments`, `shares`

### ModelRun *(new)*
`id`, `business_id`, `trained_at`, `status` (`trained` / `insufficient_data` / `failed`),
`data_points`, `sales_days_count`, `posts_count`, `mae`, `r2`,
`feature_importance_json`, `data_quality_notes_json`, `model_file_path`, `is_active`

Permanent audit trail of every training attempt — never overwritten, only
appended to. `is_active` marks the model currently used for predictions.

### PredictionLog *(new)*
`id`, `business_id`, `created_at`, `model_run_id`, `target_date`, `day_of_week`,
`post_type`, `predicted_daily_revenue`, `predicted_uplift_percent`, `confidence`,
`status` (`pending` / `evaluated`), `actual_daily_revenue`, `actual_uplift_percent`,
`absolute_error`, `evaluated_at`

The feedback loop's raw material — see "How the ML System Stays
Controlled" above.

## Key Capabilities

- Secure business login and signup
- Revenue, profit, order, and product dashboards
- Product, day-of-week, and sales-trend analysis
- Product and sales data entry, CSV import (with rejected-row reporting),
  and demo data
- Media-impact analysis by post type and timing
- ML-assisted recommendations for the best day, time, and content type to
  post, with a non-ML fallback when a model isn't trained yet
- Manual model training/retraining from the UI, with visible status, date,
  and performance
- A feedback loop that tracks recommendations and compares them to real
  outcomes

## Running the Application

```bash
pip install -r requirements.txt
streamlit run app.py --server.port 5000
```

## Environment Variables

See `.env.example` for the full list with defaults:

- `DATABASE_URL` — PostgreSQL connection string (falls back to a local
  SQLite file if unset)
- `SESSION_SECRET` — secure session secret
- `MODEL_DIR` — where trained model `.pkl` files are stored
- `DEMO_EMAIL` / `DEMO_PASSWORD` — shown as a hint on the login screen
- `MIN_TRAINING_DAYS` / `MIN_TRAINING_POSTS` — data-quality thresholds
  before training is allowed
- `PREDICTION_EVAL_WINDOW_DAYS` — how many days after a tracked
  recommendation's target date to wait before evaluating it

## Migrations

`src/db/session.py:init_db()` calls `Base.metadata.create_all()` (creates
any new table, including `model_runs` and `prediction_logs` on first run)
followed by `src/db/migrations.py:run_migrations()`, which additively adds
columns to tables that may already exist from an earlier version of the
app (`sale_time`, `post_time`, `platform`). Each migration step is a no-op
if the column already exists, so it's safe to run on every startup. If you
add a new nullable column to an existing table, add one more guarded
`ADD COLUMN` block there and document it here.
