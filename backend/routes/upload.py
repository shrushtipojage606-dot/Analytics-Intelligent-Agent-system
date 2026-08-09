from __future__ import annotations
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, Query

from agents.data_ingestion_agent import IngestionError, list_excel_sheets, read_dataset
from agents.profiling_agent import build_dataset_profile
from models.schemas import DatasetProfile
from utils import db
from utils.dataset_store import put

logger = logging.getLogger("analytics_agent.routes.upload")
router = APIRouter(prefix="/api/upload", tags=["upload"])

MAX_FILE_SIZE_MB = 50


@router.post("/sheets")
async def get_sheets(file: UploadFile = File(...)) -> dict:
    """For Excel workbooks, returns available sheet names before full ingestion."""
    if not file.filename.lower().endswith((".xlsx", ".xls")):
        return {"sheets": []}
    content = await file.read()
    try:
        sheets = list_excel_sheets(content)
    except IngestionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"sheets": sheets}


@router.post("", response_model=DatasetProfile)
async def upload_dataset(file: UploadFile = File(...), sheet_name: str | None = Query(default=None)) -> DatasetProfile:
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(status_code=413, detail=f"File exceeds {MAX_FILE_SIZE_MB}MB limit ({size_mb:.1f}MB).")

    try:
        df = read_dataset(file.filename, content, sheet_name=sheet_name)
    except IngestionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    dataset_id = str(uuid.uuid4())
    profile = build_dataset_profile(df, file.filename, dataset_id=dataset_id)

    put(dataset_id, file.filename, df)
    db.save_dataset_metadata(
        dataset_id, file.filename, datetime.now(timezone.utc).isoformat(), profile.n_rows, profile.n_columns,
    )
    logger.info("Uploaded dataset %s (%s): %d rows", dataset_id, file.filename, profile.n_rows)
    return profile


@router.get("")
async def list_uploaded_datasets() -> list[dict]:
    return db.list_datasets()


@router.get("/reports")
async def list_reports() -> list[dict]:
    """Used by the Reports page: every uploaded dataset plus its analysis
    status and anomaly count, so users can re-download past reports."""
    return db.list_datasets_with_analysis()


SAMPLE_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "sample_sales_data.csv"


@router.post("/sample", response_model=DatasetProfile)
async def upload_sample_dataset() -> DatasetProfile:
    """Loads the bundled sample sales dataset so the app can be explored without a real file."""
    if not SAMPLE_DATA_PATH.exists():
        raise HTTPException(status_code=404, detail="Sample dataset not found on the server.")
    content = SAMPLE_DATA_PATH.read_bytes()
    try:
        df = read_dataset("sample_sales_data.csv", content)
    except IngestionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    dataset_id = str(uuid.uuid4())
    profile = build_dataset_profile(df, "sample_sales_data.csv", dataset_id=dataset_id)
    put(dataset_id, "sample_sales_data.csv", df)
    db.save_dataset_metadata(
        dataset_id, "sample_sales_data.csv", datetime.now(timezone.utc).isoformat(), profile.n_rows, profile.n_columns,
    )
    return profile
