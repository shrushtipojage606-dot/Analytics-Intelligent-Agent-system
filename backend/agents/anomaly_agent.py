"""
Anomaly Detection Agent
-------------------------
Automatically selects an appropriate anomaly-detection technique per metric:

- Time-series metrics (a datetime column exists): rolling mean/std + z-score
  on the residual, so it adapts to trend/seasonality rather than flagging
  every naturally-growing value.
- Non-time-series numeric columns: IQR-based extreme-value detection.
- Cross-cutting: Isolation Forest across all numeric columns together, to
  catch multivariate outliers (e.g. an order that is unremarkable on any
  single column but unusual in combination).

Every detected anomaly is enriched with a plain-language business-impact
statement and explanation — grounded strictly in computed numbers.
"""
from __future__ import annotations
import re
import uuid
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from models.schemas import Anomaly, DatasetProfile, Severity

DIMENSION_HINTS = re.compile(r"(region|category|product|segment|channel|store|country|state|city)", re.I)


def _severity_from_z(z: float) -> Severity:
    az = abs(z)
    if az >= 4:
        return Severity.CRITICAL
    if az >= 3:
        return Severity.HIGH
    if az >= 2.2:
        return Severity.MEDIUM
    if az >= 1.5:
        return Severity.LOW
    return Severity.NORMAL


def _severity_from_pct(pct: float) -> Severity:
    apct = abs(pct)
    if apct >= 60:
        return Severity.CRITICAL
    if apct >= 30:
        return Severity.HIGH
    if apct >= 15:
        return Severity.MEDIUM
    if apct >= 7:
        return Severity.LOW
    return Severity.NORMAL


def _business_impact(metric: str, pct: float) -> str:
    direction = "decline" if pct < 0 else "increase"
    if re.search(r"profit|margin", metric, re.I):
        return f"A {direction} in {metric} directly affects bottom-line profitability."
    if re.search(r"revenue|sales", metric, re.I):
        return f"A {direction} in {metric} affects top-line growth and forecast accuracy."
    if re.search(r"churn", metric, re.I):
        return "Rising churn increases customer-acquisition cost pressure and threatens recurring revenue."
    if re.search(r"cost", metric, re.I):
        return f"An unexpected {direction} in {metric} may erode margins if not offset by revenue."
    return f"This {direction} in {metric} is outside the normal operating range and may warrant investigation."


def detect_time_series_anomalies(
    df: pd.DataFrame, date_col: str, metric: str, dimension_col: Optional[str] = None,
    window: int = 7,
) -> list[Anomaly]:
    """Rolling mean/std z-score anomaly detection, optionally per-dimension (e.g. per Region)."""
    anomalies: list[Anomaly] = []
    work = df[[date_col, metric] + ([dimension_col] if dimension_col else [])].copy()
    work[date_col] = pd.to_datetime(work[date_col], errors="coerce")
    work = work.dropna(subset=[date_col])
    work[metric] = pd.to_numeric(work[metric], errors="coerce")

    groups = work.groupby(dimension_col) if dimension_col else [(None, work)]
    for dim_value, group in groups:
        daily = group.set_index(date_col)[metric].resample("D").sum().fillna(0)
        if len(daily) < window * 2:
            continue
        # Shift by 1 so the current day is never part of its own baseline — otherwise a
        # genuine anomaly pulls its own expected mean toward itself and gets masked.
        baseline = daily.shift(1)
        rolling_mean = baseline.rolling(window=window, min_periods=window).mean()
        rolling_std = baseline.rolling(window=window, min_periods=window).std().replace(0, np.nan)
        z_scores = (daily - rolling_mean) / rolling_std

        for date, z in z_scores.dropna().items():
            if abs(z) < 1.5:
                continue
            expected = float(rolling_mean.loc[date])
            actual = float(daily.loc[date])
            diff = actual - expected
            pct_dev = round(100 * diff / expected, 1) if expected else 0.0
            # Combine both signals: a statistically mild z-score can still represent a huge,
            # business-material percentage swing (e.g. -98% on a volatile series) — take the
            # more severe of the two so real-world magnitude isn't hidden by noisy variance.
            from models.schemas import SEVERITY_ORDER
            severity = max(_severity_from_z(z), _severity_from_pct(pct_dev), key=lambda s: SEVERITY_ORDER[s])
            if severity == Severity.NORMAL:
                continue
            dim_label = f"{dimension_col}={dim_value}" if dimension_col else None
            direction = "dropped below" if diff < 0 else "spiked above"
            explanation = (
                f"{metric}{' in ' + str(dim_value) if dimension_col else ''} {direction} its expected "
                f"{window}-day rolling range on {date.date()}. Observed {actual:,.2f} vs an expected "
                f"~{expected:,.2f} ({pct_dev:+.1f}%)."
            )
            anomalies.append(Anomaly(
                id=str(uuid.uuid4()), metric=metric, dimension=dim_label, date=str(date.date()),
                current_value=round(actual, 2), expected_value=round(expected, 2),
                difference=round(diff, 2), pct_deviation=pct_dev, severity=severity,
                method="Rolling mean/std z-score",
                business_impact=_business_impact(metric, pct_dev),
                explanation=explanation,
            ))
    return anomalies


def detect_non_timeseries_anomalies(df: pd.DataFrame, metric: str, id_col: Optional[str] = None) -> list[Anomaly]:
    """IQR-based extreme value detection for a single numeric column (row-level outliers)."""
    series = pd.to_numeric(df[metric], errors="coerce").dropna()
    if len(series) < 20:
        return []
    q1, q3 = series.quantile(0.25), series.quantile(0.75)
    iqr = q3 - q1
    if iqr == 0:
        return []
    median = float(series.median())
    lower, upper = q1 - 3 * iqr, q3 + 3 * iqr

    anomalies = []
    outlier_idx = series[(series < lower) | (series > upper)].index
    for idx in outlier_idx[:25]:  # cap to avoid flooding
        actual = float(series.loc[idx])
        diff = actual - median
        pct_dev = round(100 * diff / median, 1) if median else 0.0
        severity = _severity_from_pct(pct_dev)
        if severity == Severity.NORMAL:
            continue
        row_label = str(df.loc[idx, id_col]) if id_col and id_col in df.columns else f"row {idx}"
        anomalies.append(Anomaly(
            id=str(uuid.uuid4()), metric=metric, dimension=row_label, date=None,
            current_value=round(actual, 2), expected_value=round(median, 2),
            difference=round(diff, 2), pct_deviation=pct_dev, severity=severity,
            method="IQR extreme-value detection",
            business_impact=_business_impact(metric, pct_dev),
            explanation=f"A single record for {row_label} has {metric} of {actual:,.2f}, far outside the "
                        f"typical range (median {median:,.2f}). This is a {abs(pct_dev):.0f}% deviation.",
        ))
    return anomalies


def detect_multivariate_anomalies(df: pd.DataFrame, numeric_cols: list[str], id_col: Optional[str] = None,
                                   contamination: float = 0.01) -> list[Anomaly]:
    """Isolation Forest across multiple numeric columns jointly, for combination-level outliers."""
    cols = [c for c in numeric_cols if c in df.columns][:8]
    if len(cols) < 2:
        return []
    data = df[cols].apply(pd.to_numeric, errors="coerce").dropna()
    if len(data) < 50:
        return []

    model = IsolationForest(contamination=contamination, random_state=42, n_estimators=150)
    preds = model.fit_predict(data)
    scores = model.decision_function(data)
    outlier_positions = np.where(preds == -1)[0]

    anomalies = []
    means = data.mean()
    for pos in outlier_positions[:20]:
        idx = data.index[pos]
        score = float(scores[pos])
        # Identify which column deviates most, for a human-readable explanation
        row = data.loc[idx]
        z_per_col = ((row - means) / data.std().replace(0, np.nan)).abs()
        top_col = z_per_col.idxmax()
        severity = Severity.HIGH if score < -0.15 else Severity.MEDIUM
        row_label = str(df.loc[idx, id_col]) if id_col and id_col in df.columns else f"row {idx}"
        anomalies.append(Anomaly(
            id=str(uuid.uuid4()), metric=" + ".join(cols), dimension=row_label, date=None,
            current_value=round(float(row[top_col]), 2), expected_value=round(float(means[top_col]), 2),
            difference=round(float(row[top_col] - means[top_col]), 2),
            pct_deviation=round(100 * (row[top_col] - means[top_col]) / (means[top_col] or 1), 1),
            severity=severity, method="Isolation Forest (multivariate)",
            business_impact=f"Record {row_label} is unusual across a combination of {', '.join(cols)}, "
                             f"which single-column checks would likely miss.",
            explanation=f"{row_label} was flagged as a multivariate outlier (isolation score {score:.3f}); "
                        f"'{top_col}' deviates most from the typical combination of values.",
        ))
    return anomalies


def run_anomaly_detection(df: pd.DataFrame, profile: DatasetProfile, max_per_metric: int = 15) -> list[Anomaly]:
    """Agent entry point: selects the right method(s) per column and aggregates results."""
    all_anomalies: list[Anomaly] = []
    date_col = profile.datetime_columns[0] if profile.datetime_columns else None
    dimension_col = next((c for c in profile.categorical_columns if DIMENSION_HINTS.search(c)), None)
    id_col = profile.id_columns[0] if profile.id_columns else None
    metrics = profile.kpi_candidate_columns[:6]

    for metric in metrics:
        if date_col:
            found = detect_time_series_anomalies(df, date_col, metric, dimension_col=dimension_col)
            all_anomalies.extend(found[:max_per_metric])
            # also check row-level extreme values even when time-series exists (e.g. the "whale" order)
            all_anomalies.extend(detect_non_timeseries_anomalies(df, metric, id_col=id_col)[:5])
        else:
            all_anomalies.extend(detect_non_timeseries_anomalies(df, metric, id_col=id_col)[:max_per_metric])

    all_anomalies.extend(detect_multivariate_anomalies(df, metrics, id_col=id_col))

    # De-duplicate near-identical anomalies (same metric+date+dimension), keep highest severity
    from models.schemas import SEVERITY_ORDER
    seen: dict[tuple, Anomaly] = {}
    for a in all_anomalies:
        key = (a.metric, a.date, a.dimension)
        if key not in seen or SEVERITY_ORDER[a.severity] > SEVERITY_ORDER[seen[key].severity]:
            seen[key] = a
    deduped = list(seen.values())
    deduped.sort(key=lambda a: SEVERITY_ORDER[a.severity], reverse=True)
    return deduped
