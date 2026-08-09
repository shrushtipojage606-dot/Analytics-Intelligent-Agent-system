"""
Data Ingestion Agent
---------------------
Reads uploaded CSV / XLSX / XLS files into a pandas DataFrame, without ever
mutating or overwriting the original uploaded file. Handles sheet detection
for Excel workbooks and basic encoding/delimiter resilience for CSVs.
"""
from __future__ import annotations
import io
import logging
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger("analytics_agent.ingestion")

SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls"}


class IngestionError(Exception):
    pass


def list_excel_sheets(file_bytes: bytes) -> list[str]:
    try:
        xls = pd.ExcelFile(io.BytesIO(file_bytes))
        return xls.sheet_names
    except Exception as exc:  # noqa: BLE001
        raise IngestionError(f"Could not read Excel workbook: {exc}") from exc


def read_dataset(filename: str, file_bytes: bytes, sheet_name: Optional[str] = None) -> pd.DataFrame:
    """Reads raw bytes into a DataFrame. Never writes back to the source file."""
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise IngestionError(f"Unsupported file type '{ext}'. Supported: {sorted(SUPPORTED_EXTENSIONS)}")

    try:
        if ext == ".csv":
            # Resilient CSV read: try utf-8 first, fall back to latin-1; sniff delimiter.
            try:
                df = pd.read_csv(io.BytesIO(file_bytes), encoding="utf-8", sep=None, engine="python")
            except UnicodeDecodeError:
                df = pd.read_csv(io.BytesIO(file_bytes), encoding="latin-1", sep=None, engine="python")
        else:
            df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=sheet_name or 0)
    except Exception as exc:  # noqa: BLE001
        raise IngestionError(f"Failed to parse '{filename}': {exc}") from exc

    if df.empty or df.shape[1] == 0:
        raise IngestionError("The uploaded file contains no usable data.")

    # Normalize column names: strip whitespace, keep original casing for display.
    df.columns = [str(c).strip() for c in df.columns]
    logger.info("Ingested %s: %d rows x %d cols", filename, *df.shape)
    return df
