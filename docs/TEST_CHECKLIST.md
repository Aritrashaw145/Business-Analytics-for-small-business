# Manual Test Checklist

Use this alongside the automated test suite (`pytest`) to manually verify
every major feature with real, hands-on data before calling a change
complete. Check items off top to bottom - later steps assume earlier ones
are done.

## 0. Setup

- [ ] `pip install -r requirements.txt` (or `pip install -e ".[dev]"`)
- [ ] Copy `.env.example` to `.env` and fill in `DATABASE_URL` (or leave
      unset to use the local SQLite fallback) and `SESSION_SECRET`
- [ ] `streamlit run app.py --server.port 5000`
- [ ] Confirm the app loads to the Login / Register screen with no errors
      in the terminal

## 1. Authentication

- [ ] **Register** a new account with a real email, a business name, and a
      password ≥ 6 characters → you land on the Dashboard, logged in
- [ ] Log out, then **log back in** with the same credentials → succeeds
- [ ] Try logging in with the **wrong password** → clear error, not logged in
- [ ] Try registering a **second account with the same email** → rejected
      with "already exists"
- [ ] Try registering with **mismatched passwords** → rejected before any
      account is created
- [ ] Open a private/incognito window and confirm you **cannot see**
      Business A's data without logging in as Business A

## 2. Data isolation (two businesses)

- [ ] Register a second business ("Business B")
- [ ] Add a product to Business B with an unmistakable name (e.g.
      "ISOLATION-TEST-PRODUCT")
- [ ] Log back into Business A → confirm "ISOLATION-TEST-PRODUCT" does
      **not** appear anywhere (Dashboard, Product Analytics, CSV import
      product-name matching)

## 3. Product & sales entry

- [ ] Data Management → Add Products: add 3-5 real products with distinct
      cost/selling prices
- [ ] Try adding a product with a **blank name** → rejected with a message
- [ ] Try adding a product with **cost price > selling price** → rejected
- [ ] Add Sales: record a handful of sales across different dates (some
      today, some a few days back) for different products
- [ ] Try recording a sale with **quantity 0** → rejected
- [ ] Try recording a sale with a **future date** → rejected
- [ ] Dashboard → total revenue and total profit match what you'd compute
      by hand from the rows you entered

## 4. CSV import

- [ ] Export or write a small `products.csv` with columns
      `name,cost_price,selling_price,category` - include one row missing
      `name` and one with a non-numeric price
- [ ] Import it → the valid rows import, the two bad rows are listed with
      row numbers and reasons (nothing silently disappears)
- [ ] Write a `sales.csv` with `product_name,quantity,sale_date` -
      including one row referencing a product that doesn't exist
- [ ] Import it → matching rows import, the unmatched-product row is
      rejected and shown
- [ ] Upload a CSV **missing a required column** entirely → clear error,
      zero rows imported

## 5. Analytics screens

- [ ] Product Analytics → Best Sellers / Most Profitable / Low Performers
      all populate and the numbers are plausible given what you entered
- [ ] Best Day → highlights the day you concentrated sales on
- [ ] Sales Trends → weekly and monthly charts render without errors, even
      with only a few days of data

## 6. Media impact

- [ ] Data Management → Add Media Post: add 3+ posts (mix of reel/story/
      image) on dates that overlap your sales history
- [ ] Media Impact page → totals, reel-vs-story comparison, and the
      revenue timeline all render
- [ ] Confirm the "Sales Lift %" on a post you know coincided with a sales
      bump is positive, and roughly matches a manual before/after check

## 7. ML training & recommendations

- [ ] Post Recommendations, with < 3 posts or < 7 days of sales → shows
      the "add more data" message, not a fake confident recommendation
- [ ] Data Management → Demo Data → Generate Demo Data (on a clean
      account) → 90 days of realistic products/sales/posts appear
- [ ] Post Recommendations → expand "ML Model Status & Training" → click
      **Train / Retrain Model** → see a success message with R², MAE, and
      data point count
- [ ] Reload the page → the trained-at date and metrics persist (they're
      read from the database, not recomputed)
- [ ] Best-day/time/content-type recommendation appears with a
      **confidence label** (not presented as a bare fact)
- [ ] Click **Track This Recommendation** → confirmation message appears
- [ ] Expand "Recommendation Accuracy (Feedback Loop)" → shows at least
      one pending recommendation
- [ ] (Optional, needs waiting or backdating test data) After the target
      date + a few days pass and new sales are recorded, reload the page →
      the tracked recommendation moves from pending to evaluated with an
      actual-vs-predicted comparison

## 8. Insufficient-data safety

- [ ] On a fresh account with only 1-2 days of sales and no posts, open
      Post Recommendations and the model-status panel → confirm the app
      says data is insufficient rather than guessing
- [ ] Click **Train / Retrain Model** on that same account → training is
      refused with a specific reason (not a crash, not a silently "trained"
      model)

## 9. Demo data hygiene

- [ ] On an account that already has real products, go to Demo Data → the
      "Generate Demo Data" button is disabled / refuses to run
- [ ] "Clear All Data" requires an explicit confirmation step before
      deleting anything

## 10. Automated tests

- [ ] `pytest` → all tests pass
- [ ] `pytest --cov=src --cov-report=term-missing` → spot-check that
      analytics, validation, csv_import, and ml modules have real coverage,
      not just imports

## 11. Regression check after any change

- [ ] Re-run steps 3, 4, and 7 above (entry, CSV import, ML training) -
      these are the three most business-critical flows and should be
      re-verified by hand after any change, even a small one
