"""
Generates data/sample_sales_data.csv — a realistic 2-year daily sales dataset
with intentionally injected anomalies so the anomaly-detection engine has
real signal to find (not just noise).

Run: python generate_sample_data.py
"""
import numpy as np
import pandas as pd

np.random.seed(42)

START = "2024-06-01"
END = "2026-08-07"
dates = pd.date_range(START, END, freq="D")

regions = ["North", "South", "East", "West"]
products = ["Product A", "Product B", "Product C", "Product D", "Product E"]
categories = {
    "Product A": "Electronics", "Product B": "Electronics",
    "Product C": "Home & Kitchen", "Product D": "Apparel", "Product E": "Apparel",
}
region_weight = {"North": 1.15, "South": 1.0, "East": 0.9, "West": 1.05}
product_price = {"Product A": 220, "Product B": 340, "Product C": 85, "Product D": 45, "Product E": 60}

rows = []
customer_pool = [f"CUST-{i:05d}" for i in range(1, 3000)]

for d_i, d in enumerate(dates):
    # base daily order count with weekly seasonality + slow growth trend
    weekday_factor = 1.25 if d.weekday() in (4, 5) else 1.0
    growth = 1 + (d_i / len(dates)) * 0.35  # gentle upward trend over 2 years
    n_orders = int(np.random.poisson(38 * weekday_factor * growth))

    for _ in range(n_orders):
        region = np.random.choice(regions, p=[0.3, 0.25, 0.2, 0.25])
        product = np.random.choice(products, p=[0.28, 0.22, 0.2, 0.15, 0.15])
        qty = max(1, int(np.random.poisson(3)))
        unit_price = product_price[product] * region_weight[region]
        discount_pct = np.random.choice([0, 0, 0, 5, 10, 15, 20], p=[0.4, 0.1, 0.1, 0.15, 0.1, 0.1, 0.05])
        revenue = round(qty * unit_price * (1 - discount_pct / 100), 2)
        cost = round(qty * unit_price * np.random.uniform(0.55, 0.7), 2)
        profit = round(revenue - cost, 2)

        rows.append({
            "Date": d.strftime("%Y-%m-%d"),
            "CustomerID": np.random.choice(customer_pool),
            "Product": product,
            "Category": categories[product],
            "Region": region,
            "Quantity": qty,
            "Revenue": revenue,
            "Cost": cost,
            "Profit": profit,
            "Discount": discount_pct,
        })

df = pd.DataFrame(rows)

# ---- Inject deliberate, explainable anomalies -----------------------------

# 1. Sudden revenue DROP: West region goes quiet for 3 days near the end (recent, so it's "live")
crash_dates = pd.date_range("2026-08-04", "2026-08-06")
mask = df["Date"].isin(crash_dates.strftime("%Y-%m-%d")) & (df["Region"] == "West")
drop_idx = df[mask].sample(frac=0.75, random_state=1).index
df = df.drop(drop_idx)

# 2. Unusually HIGH single transaction (outlier order) — a bulk/whale order
whale_row = {
    "Date": "2026-07-15", "CustomerID": "CUST-00042", "Product": "Product A",
    "Category": "Electronics", "Region": "North", "Quantity": 480,
    "Revenue": 98500.00, "Cost": 51200.00, "Profit": 47300.00, "Discount": 5,
}
df = pd.concat([df, pd.DataFrame([whale_row])], ignore_index=True)

# 3. Profit margin decline: inflate cost (without raising price) for Product C in the last 30 days
recent = pd.date_range("2026-07-08", "2026-08-07")
pc_mask = df["Date"].isin(recent.strftime("%Y-%m-%d")) & (df["Product"] == "Product C")
df.loc[pc_mask, "Cost"] = (df.loc[pc_mask, "Cost"] * 1.45).round(2)
df.loc[pc_mask, "Profit"] = (df.loc[pc_mask, "Revenue"] - df.loc[pc_mask, "Cost"]).round(2)

# 4. Regional sales anomaly: South region has an unexplained spike in mid-March 2026
spike_dates = pd.date_range("2026-03-10", "2026-03-12")
extra_rows = []
for d in spike_dates:
    for _ in range(60):
        product = np.random.choice(products)
        qty = max(1, int(np.random.poisson(4)))
        unit_price = product_price[product] * region_weight["South"] * 1.6  # priced up too
        revenue = round(qty * unit_price, 2)
        cost = round(qty * unit_price * 0.6, 2)
        extra_rows.append({
            "Date": d.strftime("%Y-%m-%d"), "CustomerID": np.random.choice(customer_pool),
            "Product": product, "Category": categories[product], "Region": "South",
            "Quantity": qty, "Revenue": revenue, "Cost": cost, "Profit": round(revenue - cost, 2),
            "Discount": 0,
        })
df = pd.concat([df, pd.DataFrame(extra_rows)], ignore_index=True)

# A handful of intentional data-quality issues (missing/duplicate/invalid) to exercise the profiler
dq_sample = df.sample(25, random_state=2).index
df.loc[dq_sample[:10], "Discount"] = np.nan
dup_rows = df.sample(14, random_state=3)
df = pd.concat([df, dup_rows], ignore_index=True)
df.loc[df.sample(3, random_state=4).index, "Date"] = "invalid-date"

df = df.sort_values("Date").reset_index(drop=True)
df.to_csv("sample_sales_data.csv", index=False)
print(f"Wrote sample_sales_data.csv with {len(df)} rows")
