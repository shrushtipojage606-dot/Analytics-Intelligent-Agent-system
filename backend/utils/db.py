"""
Lightweight SQLite persistence layer.

Stores:
  - dataset metadata (filename, upload time, row/col counts)
  - analysis results (as JSON, keyed by dataset_id)
  - alert settings (single-row config, keyed by user — simplified to 'default' here)
  - alert history

Uses SQLite by default (DATABASE_URL=sqlite:///./analytics.db) but the schema
is simple enough to port to Postgres by swapping the connection string and
using a real driver (e.g. psycopg2) in a production deployment.
"""
from __future__ import annotations
import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

DB_PATH = os.getenv("SQLITE_PATH", str(Path(__file__).resolve().parent.parent / "analytics.db"))


def init_db() -> None:
    with _connect() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS datasets (
            dataset_id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            uploaded_at TEXT NOT NULL,
            n_rows INTEGER,
            n_columns INTEGER
        );
        CREATE TABLE IF NOT EXISTS analysis_results (
            dataset_id TEXT PRIMARY KEY,
            result_json TEXT NOT NULL,
            FOREIGN KEY(dataset_id) REFERENCES datasets(dataset_id)
        );
        CREATE TABLE IF NOT EXISTS alert_settings (
            user_key TEXT PRIMARY KEY,
            settings_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS alert_history (
            id TEXT PRIMARY KEY,
            dataset_id TEXT,
            date TEXT,
            metric TEXT,
            severity TEXT,
            status TEXT,
            email TEXT
        );
        """)


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def save_dataset_metadata(dataset_id: str, filename: str, uploaded_at: str, n_rows: int, n_columns: int) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO datasets (dataset_id, filename, uploaded_at, n_rows, n_columns) VALUES (?,?,?,?,?)",
            (dataset_id, filename, uploaded_at, n_rows, n_columns),
        )


def save_analysis_result(dataset_id: str, result_json: dict[str, Any]) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO analysis_results (dataset_id, result_json) VALUES (?,?)",
            (dataset_id, json.dumps(result_json, default=str)),
        )


def get_analysis_result(dataset_id: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute("SELECT result_json FROM analysis_results WHERE dataset_id=?", (dataset_id,)).fetchone()
        return json.loads(row[0]) if row else None


def list_datasets() -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute("SELECT dataset_id, filename, uploaded_at, n_rows, n_columns FROM datasets ORDER BY uploaded_at DESC").fetchall()
        return [dict(zip(["dataset_id", "filename", "uploaded_at", "n_rows", "n_columns"], r)) for r in rows]


def list_datasets_with_analysis() -> list[dict[str, Any]]:
    """Same as list_datasets(), but also reports whether analysis has been run
    and how many anomalies were found — used by the Reports page."""
    with _connect() as conn:
        rows = conn.execute("""
            SELECT d.dataset_id, d.filename, d.uploaded_at, d.n_rows, d.n_columns,
                   a.result_json
            FROM datasets d
            LEFT JOIN analysis_results a ON a.dataset_id = d.dataset_id
            ORDER BY d.uploaded_at DESC
        """).fetchall()
        out = []
        for dataset_id, filename, uploaded_at, n_rows, n_columns, result_json in rows:
            anomaly_count = 0
            status = "Not analyzed"
            if result_json:
                try:
                    parsed = json.loads(result_json)
                    anomaly_count = len(parsed.get("anomalies", []))
                    status = "Ready"
                except (json.JSONDecodeError, TypeError):
                    status = "Error"
            out.append({
                "dataset_id": dataset_id, "filename": filename, "uploaded_at": uploaded_at,
                "n_rows": n_rows, "n_columns": n_columns, "anomaly_count": anomaly_count, "status": status,
            })
        return out


def save_alert_settings(user_key: str, settings_json: dict[str, Any]) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO alert_settings (user_key, settings_json) VALUES (?,?)",
            (user_key, json.dumps(settings_json, default=str)),
        )


def get_alert_settings(user_key: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute("SELECT settings_json FROM alert_settings WHERE user_key=?", (user_key,)).fetchone()
        return json.loads(row[0]) if row else None


def save_alert_records(dataset_id: str, records: list[dict[str, Any]]) -> None:
    with _connect() as conn:
        for r in records:
            conn.execute(
                "INSERT OR REPLACE INTO alert_history (id, dataset_id, date, metric, severity, status, email) VALUES (?,?,?,?,?,?,?)",
                (r["id"], dataset_id, r["date"], r["metric"], r["severity"], r["status"], r.get("email")),
            )


def list_alert_history() -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute("SELECT id, dataset_id, date, metric, severity, status, email FROM alert_history ORDER BY date DESC").fetchall()
        cols = ["id", "dataset_id", "date", "metric", "severity", "status", "email"]
        return [dict(zip(cols, r)) for r in rows]
