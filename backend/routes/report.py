"""
Report download route — thin alias over the analysis pipeline so the API
surface matches `GET /api/report/download/{dataset_id}` as requested by the
frontend spec, while reusing the exact same PDF generation used under
`/api/analysis/{dataset_id}/report.pdf`.
"""
from __future__ import annotations
import io
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from agents.report_agent import render_pdf_report
from models.schemas import AnalysisResult
from routes.analysis import _run_pipeline
from utils import db
from utils.dataset_store import exists, get_filename

logger = logging.getLogger("analytics_agent.routes.report")
router = APIRouter(prefix="/api/report", tags=["report"])


@router.get("/download/{dataset_id}")
async def download_report(dataset_id: str) -> StreamingResponse:
    if not exists(dataset_id):
        raise HTTPException(status_code=404, detail="Dataset not found. Please upload it again.")
    cached = db.get_analysis_result(dataset_id)
    result = AnalysisResult(**cached) if cached else _run_pipeline(dataset_id)
    filename = get_filename(dataset_id) or "dataset"

    pdf_bytes = render_pdf_report(result)
    safe_name = "".join(c for c in filename.rsplit(".", 1)[0] if c.isalnum() or c in ("-", "_")) or "report"
    headers = {"Content-Disposition": f'attachment; filename="{safe_name}_analytics_report.pdf"'}
    return StreamingResponse(io.BytesIO(pdf_bytes), media_type="application/pdf", headers=headers)
