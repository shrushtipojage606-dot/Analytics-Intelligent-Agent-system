"""
Data Profiling Agent
----------------------
Understands the schema of an uploaded dataset (numeric / categorical /
datetime / id columns), and runs a deterministic data-quality assessment
that produces a 0-100 quality score with actionable issues. Never mutates
the original DataFrame that was ingested.
"""
from __future__ import annotations
import re
import uuid
from typing import Any

import numpy as np
import pandas as pd

from models.schemas import ColumnProfile, DataQualityIssue, DataQualityReport, DatasetProfile, Severity

ID_NAME_PATTERN = re.compile(r"(^id$|_id$|^id_|customer.?id|order.?id|transaction.?id|invoice.?id)", re.I)
DATE_NAME_PATTERN = re.compile(r"(date|time|timestamp|period|month|year)", re.I)
KPI_NAME_HINTS = re.compile(
    r"(revenue|sales|profit|cost|price|amount|quantity|qty|churn|conversion|order|value|margin|units)", re.I
)


def _infer_datetime(series: pd.Series) -> bool:
    if pd.api.types.is_datetime64_any_dtype(series):
        return True
    if series.dtype == object and DATE_NAME_PATTERN.search(str(series.name) or ""):
        parsed = pd.to_datetime(series, errors="coerce")
        return parsed.notna().mean() > 0.6
    return False


def infer_column_type(df: pd.DataFrame, col: str) -> str:
    series = df[col]
    if ID_NAME_PATTERN.search(col) and series.nunique(dropna=True) > 1:
        return "id"
    if _infer_datetime(series):
        return "datetime"
    if pd.api.types.is_numeric_dtype(series):
        # Business-metric-like names always stay numeric, even with low cardinality in small samples.
        if KPI_NAME_HINTS.search(col):
            return "numeric"
        # Low-cardinality small integers that look like codes -> categorical (only for
        # reasonably-sized datasets, so small test/demo frames aren't misclassified).
        if len(series) >= 30 and series.nunique(dropna=True) <= 12 and series.dtype != float:
            return "categorical"
        return "numeric"
    if series.nunique(dropna=True) <= max(50, int(0.05 * len(series))):
        return "categorical"
    return "text"


def profile_columns(df: pd.DataFrame) -> list[ColumnProfile]:
    profiles = []
    n = len(df)
    for col in df.columns:
        series = df[col]
        inferred = infer_column_type(df, col)
        missing = int(series.isna().sum())
        unique = int(series.nunique(dropna=True))
        sample = [v for v in series.dropna().unique()[:5].tolist()]
        profiles.append(ColumnProfile(
            name=col,
            inferred_type=inferred,
            dtype=str(series.dtype),
            missing_count=missing,
            missing_pct=round(100 * missing / n, 2) if n else 0.0,
            unique_count=unique,
            is_constant=unique <= 1,
            is_highly_sparse=(missing / n) > 0.5 if n else False,
            sample_values=[str(s) for s in sample],
        ))
    return profiles


def assess_data_quality(df: pd.DataFrame, columns: list[ColumnProfile]) -> DataQualityReport:
    issues: list[DataQualityIssue] = []
    n_rows, n_cols = df.shape
    penalty = 0.0

    total_missing = sum(c.missing_count for c in columns)
    missing_pct_overall = round(100 * total_missing / (n_rows * n_cols), 2) if n_rows and n_cols else 0.0
    if total_missing > 0:
        sev = Severity.HIGH if missing_pct_overall > 10 else (Severity.MEDIUM if missing_pct_overall > 3 else Severity.LOW)
        penalty += min(20, missing_pct_overall * 1.5)
        issues.append(DataQualityIssue(
            kind="missing_values",
            description=f"{missing_pct_overall}% of all cells are missing across the dataset.",
            severity=sev,
            affected_count=total_missing,
            recommendation="Impute, backfill, or flag missing values before running downstream analysis; "
                            "avoid dropping rows unless missingness is concentrated in non-critical columns.",
        ))

    dup_count = int(df.duplicated().sum())
    if dup_count > 0:
        dup_pct = round(100 * dup_count / n_rows, 2) if n_rows else 0
        sev = Severity.MEDIUM if dup_pct > 2 else Severity.LOW
        penalty += min(15, dup_pct * 3)
        issues.append(DataQualityIssue(
            kind="duplicate_rows",
            description=f"{dup_count} duplicate records found ({dup_pct}% of rows).",
            severity=sev,
            affected_count=dup_count,
            recommendation="Deduplicate on a natural key (e.g. order/transaction ID) before computing KPIs "
                            "to avoid double-counting revenue or volume.",
        ))

    # Invalid dates: any column that looks like a date but fails to parse for some rows
    for c in columns:
        if c.inferred_type == "datetime":
            parsed = pd.to_datetime(df[c.name], errors="coerce")
            invalid = int(parsed.isna().sum() - df[c.name].isna().sum())
            if invalid > 0:
                penalty += min(10, invalid / n_rows * 100)
                issues.append(DataQualityIssue(
                    kind="invalid_dates",
                    description=f"{invalid} values in '{c.name}' could not be parsed as valid dates.",
                    severity=Severity.MEDIUM if invalid > 5 else Severity.LOW,
                    affected_count=invalid,
                    recommendation=f"Standardize the date format in '{c.name}' (e.g. YYYY-MM-DD) at the source.",
                ))

    # Outliers via IQR on numeric columns
    for c in columns:
        if c.inferred_type == "numeric":
            series = pd.to_numeric(df[c.name], errors="coerce").dropna()
            if len(series) < 10:
                continue
            q1, q3 = series.quantile(0.25), series.quantile(0.75)
            iqr = q3 - q1
            if iqr == 0:
                continue
            lower, upper = q1 - 3 * iqr, q3 + 3 * iqr
            n_outliers = int(((series < lower) | (series > upper)).sum())
            if n_outliers > 0:
                penalty += min(8, n_outliers / len(series) * 100)
                issues.append(DataQualityIssue(
                    kind="outliers",
                    description=f"{n_outliers} extreme outlier values detected in '{c.name}' (IQR method).",
                    severity=Severity.LOW if n_outliers < 5 else Severity.MEDIUM,
                    affected_count=n_outliers,
                    recommendation=f"Review outliers in '{c.name}' individually — they may be legitimate "
                                    f"bulk transactions or data-entry errors.",
                ))
            # Negative values where a metric name implies non-negativity
            if KPI_NAME_HINTS.search(c.name) and not re.search(r"(profit|margin|change|growth|delta)", c.name, re.I):
                n_negative = int((series < 0).sum())
                if n_negative > 0:
                    penalty += min(6, n_negative / len(series) * 100)
                    issues.append(DataQualityIssue(
                        kind="negative_values",
                        description=f"{n_negative} negative values found in '{c.name}', which is unexpected for this metric.",
                        severity=Severity.MEDIUM,
                        affected_count=n_negative,
                        recommendation=f"Confirm whether negative '{c.name}' values represent refunds/returns "
                                        f"or are data-entry errors, and tag them explicitly if legitimate.",
                    ))

    for c in columns:
        if c.is_constant and n_rows > 1:
            penalty += 1
            issues.append(DataQualityIssue(
                kind="constant_column",
                description=f"Column '{c.name}' has a single constant value across all rows.",
                severity=Severity.LOW,
                affected_count=n_rows,
                recommendation=f"'{c.name}' carries no analytical signal and can likely be dropped or documented as metadata.",
            ))
        if c.is_highly_sparse:
            penalty += 2
            issues.append(DataQualityIssue(
                kind="highly_sparse_column",
                description=f"Column '{c.name}' is more than 50% missing.",
                severity=Severity.MEDIUM,
                affected_count=c.missing_count,
                recommendation=f"Consider excluding '{c.name}' from KPI/trend calculations unless missingness "
                                f"is itself meaningful (e.g. optional field).",
            ))

    # Inconsistent categorical values (case/whitespace variants of the same label)
    for c in columns:
        if c.inferred_type == "categorical" and df[c.name].dtype == object:
            values = df[c.name].dropna().astype(str)
            normalized = values.str.strip().str.lower()
            if normalized.nunique() < values.nunique():
                n_affected = int(values.nunique() - normalized.nunique())
                penalty += 2
                issues.append(DataQualityIssue(
                    kind="inconsistent_categories",
                    description=f"Column '{c.name}' has {n_affected} likely duplicate categories differing only "
                                f"by case or whitespace (e.g. 'North' vs 'north ').",
                    severity=Severity.LOW,
                    affected_count=n_affected,
                    recommendation=f"Normalize casing/whitespace in '{c.name}' before grouping or aggregating.",
                ))

    score = max(0.0, round(100 - penalty, 1))
    return DataQualityReport(
        score=score, total_rows=n_rows, total_columns=n_cols,
        duplicate_rows=dup_count, issues=issues,
    )


def build_dataset_profile(df: pd.DataFrame, filename: str, dataset_id: str | None = None) -> DatasetProfile:
    columns = profile_columns(df)
    quality = assess_data_quality(df, columns)

    numeric_cols = [c.name for c in columns if c.inferred_type == "numeric"]
    categorical_cols = [c.name for c in columns if c.inferred_type == "categorical"]
    datetime_cols = [c.name for c in columns if c.inferred_type == "datetime"]
    id_cols = [c.name for c in columns if c.inferred_type == "id"]
    kpi_candidates = [c for c in numeric_cols if KPI_NAME_HINTS.search(c)] or numeric_cols

    preview_df = df.head(20).copy()
    for c in preview_df.columns:
        if pd.api.types.is_datetime64_any_dtype(preview_df[c]):
            preview_df[c] = preview_df[c].astype(str)
    preview = preview_df.replace({np.nan: None}).to_dict(orient="records")

    return DatasetProfile(
        dataset_id=dataset_id or str(uuid.uuid4()),
        filename=filename,
        n_rows=len(df),
        n_columns=df.shape[1],
        columns=columns,
        numeric_columns=numeric_cols,
        categorical_columns=categorical_cols,
        datetime_columns=datetime_cols,
        id_columns=id_cols,
        kpi_candidate_columns=kpi_candidates,
        preview=preview,
        quality=quality,
    )
