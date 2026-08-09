import io
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("SQLITE_PATH", str(Path(__file__).resolve().parent / "test_analytics.db"))

import pandas as pd
from fastapi.testclient import TestClient

from main import app

# Using the context-manager form ensures FastAPI's startup event (DB init) runs.
client = TestClient(app)
client.__enter__()


def _sample_csv_bytes() -> bytes:
    df = pd.DataFrame({
        "Date": pd.date_range("2026-01-01", periods=60).strftime("%Y-%m-%d"),
        "Revenue": [1000 + i * 5 for i in range(60)],
        "Profit": [200 + i for i in range(60)],
        "Region": (["North", "South", "East", "West"] * 15),
    })
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    return buf.getvalue()


def test_health_check():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_upload_and_analyze_flow():
    files = {"file": ("sample.csv", _sample_csv_bytes(), "text/csv")}
    upload_resp = client.post("/api/upload", files=files)
    assert upload_resp.status_code == 200
    profile = upload_resp.json()
    assert profile["n_rows"] == 60
    dataset_id = profile["dataset_id"]

    analysis_resp = client.get(f"/api/analysis/{dataset_id}")
    assert analysis_resp.status_code == 200
    result = analysis_resp.json()
    assert "kpis" in result and len(result["kpis"]) > 0
    assert "executive_summary" in result


def test_upload_rejects_unsupported_extension():
    files = {"file": ("sample.txt", b"not,real,csv", "text/plain")}
    resp = client.post("/api/upload", files=files)
    assert resp.status_code == 400


def test_analysis_404_for_unknown_dataset():
    resp = client.get("/api/analysis/does-not-exist")
    assert resp.status_code == 404


def test_alert_settings_roundtrip():
    payload = {"email": "ops@example.com", "severity_threshold": "High", "enabled": True}
    put_resp = client.put("/api/alerts/settings", json=payload)
    assert put_resp.status_code == 200
    get_resp = client.get("/api/alerts/settings")
    assert get_resp.json()["email"] == "ops@example.com"
