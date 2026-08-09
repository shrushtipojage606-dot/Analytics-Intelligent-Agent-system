"""
In-memory dataset cache.

Uploaded files are parsed once into a DataFrame and kept here for the life
of the process, keyed by dataset_id, so repeated analysis/alert calls don't
need to re-upload. This is intentionally simple for a portfolio project —
swap for Redis/S3-backed storage in a real multi-instance deployment.
"""
from __future__ import annotations
import pandas as pd

_datasets: dict[str, pd.DataFrame] = {}
_filenames: dict[str, str] = {}


def put(dataset_id: str, filename: str, df: pd.DataFrame) -> None:
    _datasets[dataset_id] = df
    _filenames[dataset_id] = filename


def get(dataset_id: str) -> pd.DataFrame | None:
    return _datasets.get(dataset_id)


def get_filename(dataset_id: str) -> str | None:
    return _filenames.get(dataset_id)


def exists(dataset_id: str) -> bool:
    return dataset_id in _datasets
