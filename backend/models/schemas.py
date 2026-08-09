"""Pydantic models shared across routes, agents and services."""
from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, EmailStr, Field


class Severity(str, Enum):
    NORMAL = "Normal"
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


SEVERITY_ICON = {
    Severity.NORMAL: "🟢", Severity.LOW: "🟡", Severity.MEDIUM: "🟠",
    Severity.HIGH: "🔴", Severity.CRITICAL: "🚨",
}
SEVERITY_ORDER = {Severity.NORMAL: 0, Severity.LOW: 1, Severity.MEDIUM: 2, Severity.HIGH: 3, Severity.CRITICAL: 4}


class ColumnProfile(BaseModel):
    name: str
    inferred_type: str  # numeric | categorical | datetime | id | text
    dtype: str
    missing_count: int
    missing_pct: float
    unique_count: int
    is_constant: bool = False
    is_highly_sparse: bool = False
    sample_values: list[Any] = Field(default_factory=list)


class DataQualityIssue(BaseModel):
    kind: str
    description: str
    severity: Severity
    affected_count: int
    recommendation: str


class DataQualityReport(BaseModel):
    score: float
    total_rows: int
    total_columns: int
    duplicate_rows: int
    issues: list[DataQualityIssue]


class DatasetProfile(BaseModel):
    dataset_id: str
    filename: str
    n_rows: int
    n_columns: int
    columns: list[ColumnProfile]
    numeric_columns: list[str]
    categorical_columns: list[str]
    datetime_columns: list[str]
    id_columns: list[str]
    kpi_candidate_columns: list[str]
    preview: list[dict[str, Any]]
    quality: DataQualityReport


class KPI(BaseModel):
    name: str
    value: float
    formatted_value: str
    previous_value: Optional[float] = None
    pct_change: Optional[float] = None
    trend: Optional[str] = None  # up | down | flat


class TrendPoint(BaseModel):
    period: str
    value: float


class MetricTrend(BaseModel):
    metric: str
    direction: str  # Increasing | Decreasing | Stable | Volatile
    current_value: float
    previous_value: float
    absolute_change: float
    pct_change: float
    series: list[TrendPoint]


class Anomaly(BaseModel):
    id: str
    metric: str
    dimension: Optional[str] = None  # e.g. "Region=West"
    date: Optional[str] = None
    current_value: float
    expected_value: float
    difference: float
    pct_deviation: float
    severity: Severity
    method: str
    business_impact: str
    explanation: str
    status: str = "Open"


class ChartSpec(BaseModel):
    id: str
    chart_type: str  # line | bar | area | scatter | histogram | box | heatmap | pie
    title: str
    x_field: Optional[str] = None
    y_field: Optional[str] = None
    series_field: Optional[str] = None
    data: list[dict[str, Any]]
    anomaly_markers: list[str] = Field(default_factory=list)


class BusinessInsight(BaseModel):
    id: str
    title: str
    severity: Severity
    observed_facts: list[str]
    possible_causes: list[str]
    business_impact: str
    recommended_action: str


class ExecutiveSummary(BaseModel):
    summary: str
    key_positive_trends: list[str]
    key_negative_trends: list[str]
    critical_anomalies: list[str]
    business_risks: list[str]
    business_opportunities: list[str]
    recommended_actions: list[str]


class AnalysisResult(BaseModel):
    dataset_id: str
    profile: DatasetProfile
    kpis: list[KPI]
    trends: list[MetricTrend]
    anomalies: list[Anomaly]
    charts: list[ChartSpec]
    insights: list[BusinessInsight]
    executive_summary: ExecutiveSummary
    generated_at: datetime


class AlertSettings(BaseModel):
    email: Optional[EmailStr] = None
    severity_threshold: Severity = Severity.HIGH
    metrics_to_monitor: list[str] = Field(default_factory=list)
    alert_frequency: str = "immediate"  # immediate | hourly | daily
    enabled: bool = True

    # Extended per-category preferences (Email Alerts page). Kept optional/defaulted
    # so existing clients relying on the original fields above keep working unchanged.
    notify_critical: bool = True
    notify_high: bool = True
    notify_metric_drops: bool = True
    notify_metric_increases: bool = False
    notify_data_quality: bool = False
    notify_daily_summary: bool = False
    notify_weekly_summary: bool = False
    threshold_pct: float = 10.0
    subscribed_at: Optional[datetime] = None


class EmailSubscribeRequest(BaseModel):
    email: EmailStr
    notify_critical: bool = True
    notify_high: bool = True
    notify_metric_drops: bool = True
    notify_metric_increases: bool = False
    notify_data_quality: bool = False
    notify_daily_summary: bool = False
    notify_weekly_summary: bool = False
    threshold_pct: float = 10.0
    severity_threshold: Severity = Severity.HIGH
    metrics_to_monitor: list[str] = Field(default_factory=list)
    alert_frequency: str = "immediate"


class AlertRecord(BaseModel):
    id: str
    date: str
    metric: str
    severity: Severity
    status: str  # Sent | Skipped (duplicate) | Failed | Disabled
    email: Optional[str] = None
