from __future__ import annotations
import io
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from agents.analytics_agent import detect_trends, generate_kpis
from agents.anomaly_agent import run_anomaly_detection
from agents.business_intelligence_agent import generate_executive_summary, generate_insights
from agents.profiling_agent import build_dataset_profile
from agents.report_agent import assemble_analysis_result, render_markdown_report, render_pdf_report
from agents.visualization_agent import generate_charts
from models.schemas import AnalysisResult
from utils import db
from utils.dataset_store import exists, get, get_filename

logger = logging.getLogger("analytics_agent.routes.analysis")
router = APIRouter(prefix="/api/analysis", tags=["analysis"])


def _run_pipeline(dataset_id: str) -> AnalysisResult:
    """
    Data Ingestion Agent (already ran at upload) → Profiling Agent → Analytics Agent
    → Anomaly Detection Agent → Business Intelligence Agent → Visualization Agent → Report Agent
    """
    df = get(dataset_id)
    if df is None:
        raise HTTPException(status_code=404, detail="Dataset not found. Please upload it again.")
    filename = get_filename(dataset_id) or "dataset"

    profile = build_dataset_profile(df, filename, dataset_id=dataset_id)
    kpis = generate_kpis(df, profile)
    trends = detect_trends(df, profile)
    anomalies = run_anomaly_detection(df, profile)
    charts = generate_charts(df, profile, anomalies)
    insights = generate_insights(anomalies, trends)
    executive_summary = generate_executive_summary(kpis, trends, anomalies, insights)

    result = assemble_analysis_result(
        dataset_id, profile, kpis, trends, anomalies, charts, insights, executive_summary,
    )
    db.save_analysis_result(dataset_id, result.model_dump(mode="json"))
    return result


@router.post("/{dataset_id}/run", response_model=AnalysisResult)
async def run_analysis(dataset_id: str) -> AnalysisResult:
    if not exists(dataset_id):
        raise HTTPException(status_code=404, detail="Dataset not found. Please upload it again.")
    return _run_pipeline(dataset_id)


@router.get("/{dataset_id}", response_model=AnalysisResult)
async def get_analysis(dataset_id: str) -> AnalysisResult:
    cached = db.get_analysis_result(dataset_id)
    if cached:
        return AnalysisResult(**cached)
    if not exists(dataset_id):
        raise HTTPException(status_code=404, detail="Dataset not found. Please upload it again.")
    return _run_pipeline(dataset_id)


@router.get("/{dataset_id}/report.md")
async def get_markdown_report(dataset_id: str) -> dict:
    cached = db.get_analysis_result(dataset_id)
    result = AnalysisResult(**cached) if cached else _run_pipeline(dataset_id)
    return {"markdown": render_markdown_report(result)}


@router.get("/{dataset_id}/report.pdf")
async def get_pdf_report(dataset_id: str) -> StreamingResponse:
    """Generates a branded PDF report from the real, already-computed analysis
    result (runs the pipeline first if it hasn't been run yet). Used by the
    frontend's "Download Analysis Report" button."""
    if not exists(dataset_id):
        raise HTTPException(status_code=404, detail="Dataset not found. Please upload it again.")
    cached = db.get_analysis_result(dataset_id)
    result = AnalysisResult(**cached) if cached else _run_pipeline(dataset_id)
    filename = get_filename(dataset_id) or "dataset"

    pdf_bytes = render_pdf_report(result)
    safe_name = "".join(c for c in filename.rsplit(".", 1)[0] if c.isalnum() or c in ("-", "_")) or "report"
    headers = {"Content-Disposition": f'attachment; filename="{safe_name}_analytics_report.pdf"'}
    return StreamingResponse(io.BytesIO(pdf_bytes), media_type="application/pdf", headers=headers)
