"""
Analytics Agent
-----------------
Identifies KPIs, computes period-over-period trends, and reasons about
which numeric columns matter most from a business perspective. All numbers
here are computed deterministically from the data — nothing is invented.
"""
from __future__ import annotations
import re
from typing import Optional

import numpy as np
import pandas as pd

from models.schemas import DatasetProfile, KPI, MetricTrend, TrendPoint

CURRENCY_HINTS = re.compile(r"(revenue|sales|profit|cost|price|amount|value|margin)", re.I)
COUNT_HINTS = re.compile(r"(quantity|qty|count|orders|units|customers)", re.I)
RATE_HINTS = re.compile(r"(rate|pct|percent|margin|conversion|churn)", re.I)


def _format_value(name: str, value: float) -> str:
    if RATE_HINTS.search(name) and abs(value) <= 100:
        return f"{value:,.1f}%"
    if CURRENCY_HINTS.search(name):
        if abs(value) >= 1_00_00_000:  # 1 crore
            return f"₹{value/1_00_00_000:.2f}Cr"
        if abs(value) >= 1_00_000:
            return f"₹{value/1_00_000:.2f}L"
        return f"₹{value:,.0f}"
    if COUNT_HINTS.search(name):
        return f"{value:,.0f}"
    return f"{value:,.2f}"


def find_primary_date_column(profile: DatasetProfile) -> Optional[str]:
    return profile.datetime_columns[0] if profile.datetime_columns else None


def _split_periods(df: pd.DataFrame, date_col: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split into 'current period' (most recent half) vs 'previous period' by date."""
    dates = pd.to_datetime(df[date_col], errors="coerce")
    valid = df[dates.notna()].copy()
    valid["_date"] = dates[dates.notna()]
    valid = valid.sort_values("_date")
    if valid.empty:
        return df.copy(), df.iloc[0:0].copy()
    midpoint = valid["_date"].min() + (valid["_date"].max() - valid["_date"].min()) / 2
    current = valid[valid["_date"] >= midpoint]
    previous = valid[valid["_date"] < midpoint]
    return current, previous


def generate_kpis(df: pd.DataFrame, profile: DatasetProfile) -> list[KPI]:
    """Generate KPIs from numeric columns, plus derived ratios where columns support it."""
    kpis: list[KPI] = []
    date_col = find_primary_date_column(profile)
    current, previous = (_split_periods(df, date_col) if date_col else (df, df.iloc[0:0]))

    candidates = profile.kpi_candidate_columns[:6]
    lower_cols = {c.lower(): c for c in df.columns}

    for col in candidates:
        cur_val = pd.to_numeric(current[col], errors="coerce").sum()
        prev_val = pd.to_numeric(previous[col], errors="coerce").sum() if len(previous) else None
        pct = round(100 * (cur_val - prev_val) / prev_val, 1) if prev_val else None
        trend = None
        if pct is not None:
            trend = "up" if pct > 1 else ("down" if pct < -1 else "flat")
        kpis.append(KPI(
            name=f"Total {col}",
            value=round(float(cur_val), 2),
            formatted_value=_format_value(col, float(cur_val)),
            previous_value=round(float(prev_val), 2) if prev_val is not None else None,
            pct_change=pct,
            trend=trend,
        ))

    # Order/record count KPI
    cur_count, prev_count = len(current), len(previous)
    count_pct = round(100 * (cur_count - prev_count) / prev_count, 1) if prev_count else None
    kpis.append(KPI(
        name="Total Orders" if "customerid" in lower_cols or "orderid" in lower_cols else "Total Records",
        value=float(cur_count), formatted_value=f"{cur_count:,.0f}",
        previous_value=float(prev_count) if prev_count else None,
        pct_change=count_pct,
        trend=("up" if (count_pct or 0) > 1 else "down" if (count_pct or 0) < -1 else "flat") if count_pct is not None else None,
    ))

    # Derived: Average Order Value = Revenue / Orders
    rev_col = next((c for c in df.columns if re.search(r"revenue|sales", c, re.I) and c in profile.numeric_columns), None)
    if rev_col and cur_count:
        aov_cur = pd.to_numeric(current[rev_col], errors="coerce").sum() / cur_count
        aov_prev = (pd.to_numeric(previous[rev_col], errors="coerce").sum() / prev_count) if prev_count else None
        aov_pct = round(100 * (aov_cur - aov_prev) / aov_prev, 1) if aov_prev else None
        kpis.append(KPI(
            name="Average Order Value", value=round(aov_cur, 2), formatted_value=_format_value(rev_col, aov_cur),
            previous_value=round(aov_prev, 2) if aov_prev else None, pct_change=aov_pct,
            trend=("up" if (aov_pct or 0) > 1 else "down" if (aov_pct or 0) < -1 else "flat") if aov_pct is not None else None,
        ))

    # Derived: Profit Margin = Profit / Revenue
    profit_col = next((c for c in df.columns if re.search(r"profit", c, re.I) and c in profile.numeric_columns), None)
    if rev_col and profit_col:
        cur_rev, cur_profit = pd.to_numeric(current[rev_col], errors="coerce").sum(), pd.to_numeric(current[profit_col], errors="coerce").sum()
        margin_cur = round(100 * cur_profit / cur_rev, 2) if cur_rev else 0
        margin_prev = None
        if len(previous):
            prev_rev, prev_profit = pd.to_numeric(previous[rev_col], errors="coerce").sum(), pd.to_numeric(previous[profit_col], errors="coerce").sum()
            margin_prev = round(100 * prev_profit / prev_rev, 2) if prev_rev else None
        margin_pct = round(margin_cur - margin_prev, 2) if margin_prev is not None else None
        kpis.append(KPI(
            name="Profit Margin", value=margin_cur, formatted_value=f"{margin_cur:.1f}%",
            previous_value=margin_prev, pct_change=margin_pct,
            trend=("up" if (margin_pct or 0) > 0.5 else "down" if (margin_pct or 0) < -0.5 else "flat") if margin_pct is not None else None,
        ))

    # Derived: Customer count if an ID column looks customer-like
    cust_col = next((c for c in profile.id_columns if re.search(r"customer", c, re.I)), None)
    if cust_col:
        cur_c, prev_c = current[cust_col].nunique(), previous[cust_col].nunique() if len(previous) else None
        c_pct = round(100 * (cur_c - prev_c) / prev_c, 1) if prev_c else None
        kpis.append(KPI(
            name="Unique Customers", value=float(cur_c), formatted_value=f"{cur_c:,.0f}",
            previous_value=float(prev_c) if prev_c else None, pct_change=c_pct,
            trend=("up" if (c_pct or 0) > 1 else "down" if (c_pct or 0) < -1 else "flat") if c_pct is not None else None,
        ))

    return kpis


def detect_trends(df: pd.DataFrame, profile: DatasetProfile, top_n: int = 6) -> list[MetricTrend]:
    """Resample important numeric metrics over time and classify their direction."""
    date_col = find_primary_date_column(profile)
    if not date_col:
        return []

    work = df.copy()
    work["_date"] = pd.to_datetime(work[date_col], errors="coerce")
    work = work.dropna(subset=["_date"])
    if work.empty:
        return []

    span_days = (work["_date"].max() - work["_date"].min()).days
    freq = "W" if span_days > 60 else "D"

    trends: list[MetricTrend] = []
    metrics = profile.kpi_candidate_columns[:top_n]
    for metric in metrics:
        series = work.set_index("_date")[metric].apply(pd.to_numeric, errors="coerce")
        resampled = series.resample(freq).sum().dropna()
        if len(resampled) < 4:
            continue

        values = resampled.values
        current_value = float(values[-4:].mean())
        previous_value = float(values[-8:-4].mean()) if len(values) >= 8 else float(values[:-4].mean() if len(values) > 4 else values[0])
        abs_change = current_value - previous_value
        pct_change = round(100 * abs_change / previous_value, 2) if previous_value else 0.0

        volatility = float(np.std(values[-8:]) / (np.mean(values[-8:]) + 1e-9)) if len(values) >= 4 else 0
        if volatility > 0.5:
            direction = "Volatile"
        elif pct_change > 3:
            direction = "Increasing"
        elif pct_change < -3:
            direction = "Decreasing"
        else:
            direction = "Stable"

        series_points = [TrendPoint(period=str(idx.date()), value=round(float(v), 2)) for idx, v in resampled.items()]
        trends.append(MetricTrend(
            metric=metric, direction=direction,
            current_value=round(current_value, 2), previous_value=round(previous_value, 2),
            absolute_change=round(abs_change, 2), pct_change=pct_change,
            series=series_points,
        ))

    # Prioritize by absolute magnitude of pct_change (i.e. the metrics moving the most)
    trends.sort(key=lambda t: abs(t.pct_change), reverse=True)
    return trends
