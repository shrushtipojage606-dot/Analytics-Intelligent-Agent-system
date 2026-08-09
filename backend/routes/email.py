"""
Email Alerts routes.

These are additive endpoints that give the frontend's "Email Alerts" page an
API surface named the way the product spec expects (`/api/email/...`), while
reusing the exact same AlertSettings model and SQLite-backed alert_settings
table that already powers `/api/alerts/settings` and the alert pipeline in
agents/alert_agent.py. No separate storage layer, no duplicated logic.
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from models.schemas import AlertSettings, EmailSubscribeRequest
from utils import db

logger = logging.getLogger("analytics_agent.routes.email")
router = APIRouter(prefix="/api/email", tags=["email"])

# Single-tenant demo app: alert settings are stored under one row, exactly like
# routes/alerts.py. If you outgrow single-tenant, key this by settings.email instead.
DEFAULT_USER_KEY = "default"


@router.post("/subscribe", response_model=AlertSettings)
async def subscribe(payload: EmailSubscribeRequest) -> AlertSettings:
    settings = AlertSettings(
        email=payload.email,
        severity_threshold=payload.severity_threshold,
        metrics_to_monitor=payload.metrics_to_monitor,
        alert_frequency=payload.alert_frequency,
        enabled=True,
        notify_critical=payload.notify_critical,
        notify_high=payload.notify_high,
        notify_metric_drops=payload.notify_metric_drops,
        notify_metric_increases=payload.notify_metric_increases,
        notify_data_quality=payload.notify_data_quality,
        notify_daily_summary=payload.notify_daily_summary,
        notify_weekly_summary=payload.notify_weekly_summary,
        threshold_pct=payload.threshold_pct,
        subscribed_at=datetime.now(timezone.utc),
    )
    db.save_alert_settings(DEFAULT_USER_KEY, settings.model_dump(mode="json"))
    logger.info("Email alerts enabled for %s", payload.email)
    return settings


@router.post("/unsubscribe")
async def unsubscribe(email: str | None = None) -> dict:
    stored = db.get_alert_settings(DEFAULT_USER_KEY)
    if not stored:
        raise HTTPException(status_code=404, detail="No active subscription found.")
    settings = AlertSettings(**stored)
    settings.enabled = False
    db.save_alert_settings(DEFAULT_USER_KEY, settings.model_dump(mode="json"))
    return {"status": "unsubscribed", "email": settings.email}


@router.get("/preferences", response_model=AlertSettings)
async def get_preferences() -> AlertSettings:
    stored = db.get_alert_settings(DEFAULT_USER_KEY)
    if not stored:
        raise HTTPException(status_code=404, detail="No email alert preferences saved yet.")
    return AlertSettings(**stored)


@router.put("/preferences", response_model=AlertSettings)
async def update_preferences(settings: AlertSettings) -> AlertSettings:
    db.save_alert_settings(DEFAULT_USER_KEY, settings.model_dump(mode="json"))
    return settings
