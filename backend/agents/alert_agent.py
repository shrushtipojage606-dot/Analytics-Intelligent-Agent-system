"""
Alert Agent
-------------
Watches anomalies coming out of the Anomaly Detection Agent, compares
severity against the user's configured threshold, and triggers deduplicated
email alerts through the Email Service. Alert history is persisted so the
same anomaly is never re-sent.
"""
from __future__ import annotations
import logging
import uuid
from datetime import datetime, timezone

from models.schemas import Anomaly, AlertRecord, AlertSettings, Severity, SEVERITY_ORDER
from services.email_service import email_service

logger = logging.getLogger("analytics_agent.alerts")

# In-memory store as a simple default; swappable for a DB-backed store (see utils/db.py) in production.
_alert_history: list[AlertRecord] = []
_sent_signatures: set[str] = set()


def _signature(dataset_id: str, anomaly: Anomaly) -> str:
    return f"{dataset_id}:{anomaly.metric}:{anomaly.dimension}:{anomaly.date}"


def evaluate_and_alert(dataset_id: str, dataset_name: str, anomalies: list[Anomaly], settings: AlertSettings) -> list[AlertRecord]:
    """Runs the alert pipeline for a batch of anomalies against the given settings."""
    records: list[AlertRecord] = []

    if not settings.enabled:
        for a in anomalies:
            if SEVERITY_ORDER[a.severity] >= SEVERITY_ORDER[settings.severity_threshold]:
                records.append(_record(dataset_id, a, "Disabled", settings.email))
        _alert_history.extend(records)
        return records

    for a in anomalies:
        if SEVERITY_ORDER[a.severity] < SEVERITY_ORDER[settings.severity_threshold]:
            continue
        if settings.metrics_to_monitor and a.metric not in settings.metrics_to_monitor:
            continue
        # Per-category preferences from the Email Alerts page.
        if a.severity == Severity.CRITICAL and not settings.notify_critical:
            continue
        if a.severity == Severity.HIGH and not settings.notify_high:
            continue
        is_drop = a.difference < 0
        if is_drop and not settings.notify_metric_drops:
            continue
        if not is_drop and not settings.notify_metric_increases and a.difference > 0:
            continue
        if abs(a.pct_deviation) < settings.threshold_pct:
            continue

        sig = _signature(dataset_id, a)
        if sig in _sent_signatures:
            records.append(_record(dataset_id, a, "Skipped (duplicate)", settings.email))
            continue

        if not settings.email:
            records.append(_record(dataset_id, a, "Failed", None))
            continue

        success = email_service.send_alert(settings.email, dataset_name, a)
        status = "Sent" if success else "Failed"
        if success:
            _sent_signatures.add(sig)
        records.append(_record(dataset_id, a, status, settings.email))

    _alert_history.extend(records)
    return records


def _record(dataset_id: str, anomaly: Anomaly, status: str, email: str | None) -> AlertRecord:
    return AlertRecord(
        id=str(uuid.uuid4()),
        date=anomaly.date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        metric=anomaly.metric, severity=anomaly.severity, status=status, email=email,
    )


def get_alert_history() -> list[AlertRecord]:
    return sorted(_alert_history, key=lambda r: r.date, reverse=True)
