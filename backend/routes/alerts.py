from __future__ import annotations
import logging

from fastapi import APIRouter, HTTPException

from agents.alert_agent import evaluate_and_alert, get_alert_history
from models.schemas import AlertSettings, AlertRecord, AnalysisResult
from utils import db
from utils.dataset_store import exists, get_filename

logger = logging.getLogger("analytics_agent.routes.alerts")
router = APIRouter(prefix="/api/alerts", tags=["alerts"])

DEFAULT_USER_KEY = "default"


@router.get("/settings", response_model=AlertSettings)
async def get_settings() -> AlertSettings:
    stored = db.get_alert_settings(DEFAULT_USER_KEY)
    return AlertSettings(**stored) if stored else AlertSettings()


@router.put("/settings", response_model=AlertSettings)
async def update_settings(settings: AlertSettings) -> AlertSettings:
    db.save_alert_settings(DEFAULT_USER_KEY, settings.model_dump(mode="json"))
    return settings


@router.post("/{dataset_id}/evaluate", response_model=list[AlertRecord])
async def evaluate_alerts(dataset_id: str) -> list[AlertRecord]:
    if not exists(dataset_id):
        raise HTTPException(status_code=404, detail="Dataset not found. Please upload it again.")
    cached = db.get_analysis_result(dataset_id)
    if not cached:
        raise HTTPException(status_code=400, detail="Run analysis before evaluating alerts.")
    result = AnalysisResult(**cached)

    stored_settings = db.get_alert_settings(DEFAULT_USER_KEY)
    settings = AlertSettings(**stored_settings) if stored_settings else AlertSettings()

    filename = get_filename(dataset_id) or "dataset"
    records = evaluate_and_alert(dataset_id, filename, result.anomalies, settings)
    db.save_alert_records(dataset_id, [r.model_dump(mode="json") for r in records])
    return records


@router.get("/history", response_model=list[AlertRecord])
async def alert_history() -> list[AlertRecord]:
    rows = db.list_alert_history()
    return [AlertRecord(**r) for r in rows]
