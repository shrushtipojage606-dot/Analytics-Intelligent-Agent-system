"""
Visualization Agent
----------------------
Decides which chart types are most meaningful for the dataset and produces
ready-to-render chart specs (the frontend just maps these to Recharts
components — no chart logic duplicated on the client).

Rules of thumb encoded here:
  time + numeric metric        -> line chart (with anomaly markers)
  category + numeric metric    -> bar chart
  two related numeric metrics  -> scatter plot
  distribution of one metric   -> histogram
  outlier inspection           -> box plot
"""
from __future__ import annotations
import uuid

import numpy as np
import pandas as pd

from models.schemas import Anomaly, ChartSpec, DatasetProfile


def _line_chart(df: pd.DataFrame, date_col: str, metric: str, anomalies: list[Anomaly]) -> ChartSpec:
    work = df[[date_col, metric]].copy()
    work[date_col] = pd.to_datetime(work[date_col], errors="coerce")
    work = work.dropna(subset=[date_col])
    work[metric] = pd.to_numeric(work[metric], errors="coerce")
    span_days = (work[date_col].max() - work[date_col].min()).days
    freq = "W" if span_days > 60 else "D"
    series = work.set_index(date_col)[metric].resample(freq).sum().fillna(0)
    data = [{"period": str(idx.date()), "value": round(float(v), 2)} for idx, v in series.items()]
    marker_dates = {a.date for a in anomalies if a.metric == metric and a.date}
    return ChartSpec(
        id=str(uuid.uuid4()), chart_type="line", title=f"{metric} Over Time",
        x_field="period", y_field="value", data=data,
        anomaly_markers=[d["period"] for d in data if d["period"] in marker_dates],
    )


def _bar_chart(df: pd.DataFrame, category_col: str, metric: str) -> ChartSpec:
    grouped = df.groupby(category_col)[metric].apply(lambda s: pd.to_numeric(s, errors="coerce").sum())
    grouped = grouped.sort_values(ascending=False).head(12)
    data = [{"category": str(k), "value": round(float(v), 2)} for k, v in grouped.items()]
    return ChartSpec(
        id=str(uuid.uuid4()), chart_type="bar", title=f"{metric} by {category_col}",
        x_field="category", y_field="value", data=data,
    )


def _scatter_chart(df: pd.DataFrame, metric_x: str, metric_y: str) -> ChartSpec:
    sample = df[[metric_x, metric_y]].apply(pd.to_numeric, errors="coerce").dropna()
    if len(sample) > 500:
        sample = sample.sample(500, random_state=42)
    data = [{"x": round(float(r[metric_x]), 2), "y": round(float(r[metric_y]), 2)} for _, r in sample.iterrows()]
    return ChartSpec(
        id=str(uuid.uuid4()), chart_type="scatter", title=f"{metric_x} vs {metric_y}",
        x_field="x", y_field="y", data=data,
    )


def _histogram(df: pd.DataFrame, metric: str, bins: int = 20) -> ChartSpec:
    series = pd.to_numeric(df[metric], errors="coerce").dropna()
    counts, edges = np.histogram(series, bins=bins)
    data = [{"bucket": f"{edges[i]:,.0f}–{edges[i+1]:,.0f}", "value": int(counts[i])} for i in range(len(counts))]
    return ChartSpec(
        id=str(uuid.uuid4()), chart_type="histogram", title=f"Distribution of {metric}",
        x_field="bucket", y_field="value", data=data,
    )


def _box_plot(df: pd.DataFrame, metric: str, category_col: str | None = None) -> ChartSpec:
    if category_col:
        data = []
        for cat, sub in df.groupby(category_col):
            series = pd.to_numeric(sub[metric], errors="coerce").dropna()
            if len(series) < 5:
                continue
            q1, q2, q3 = series.quantile([0.25, 0.5, 0.75])
            data.append({
                "category": str(cat), "min": round(float(series.min()), 2), "q1": round(float(q1), 2),
                "median": round(float(q2), 2), "q3": round(float(q3), 2), "max": round(float(series.max()), 2),
            })
    else:
        series = pd.to_numeric(df[metric], errors="coerce").dropna()
        q1, q2, q3 = series.quantile([0.25, 0.5, 0.75])
        data = [{"category": metric, "min": round(float(series.min()), 2), "q1": round(float(q1), 2),
                 "median": round(float(q2), 2), "q3": round(float(q3), 2), "max": round(float(series.max()), 2)}]
    return ChartSpec(id=str(uuid.uuid4()), chart_type="box", title=f"{metric} Spread & Outliers", data=data)


def generate_charts(df: pd.DataFrame, profile: DatasetProfile, anomalies: list[Anomaly], max_charts: int = 8) -> list[ChartSpec]:
    charts: list[ChartSpec] = []
    date_col = profile.datetime_columns[0] if profile.datetime_columns else None
    metrics = profile.kpi_candidate_columns[:4]
    category_col = profile.categorical_columns[0] if profile.categorical_columns else None

    if date_col:
        for m in metrics[:3]:
            charts.append(_line_chart(df, date_col, m, anomalies))

    if category_col:
        for m in metrics[:2]:
            charts.append(_bar_chart(df, category_col, m))

    if len(metrics) >= 2:
        charts.append(_scatter_chart(df, metrics[0], metrics[1]))

    if metrics:
        charts.append(_histogram(df, metrics[0]))
        charts.append(_box_plot(df, metrics[0], category_col))

    return charts[:max_charts]
