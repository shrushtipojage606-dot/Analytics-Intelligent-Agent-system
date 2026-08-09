# Analytics Intelligence Agent

An AI-powered autonomous analytics platform. Upload a CSV or Excel file and an
agent pipeline reads the schema, scores data quality, detects anomalies,
finds trends, and writes business-context explanations — without you
defining a single KPI or chart.

**Upload → AI Understands → AI Analyzes → AI Detects → AI Explains → AI Alerts → AI Recommends**

![status](https://img.shields.io/badge/tests-14%20passing-2dd9c3) ![python](https://img.shields.io/badge/python-3.11%2B-blue) ![node](https://img.shields.io/badge/node-18%2B-green)

---

## What it does

- **Understands any dataset automatically** — infers numeric, categorical,
  datetime, and ID columns from a raw CSV/XLSX, no configuration required.
- **Scores data quality** (0–100) — missing values, duplicates, invalid
  dates, outliers, negative values, constant/sparse columns, inconsistent
  categories — each with a concrete fix recommendation.
- **Detects anomalies** with the right method per situation: rolling
  mean/std z-score for time series (per dimension, e.g. per region),
  IQR extreme-value detection for row-level outliers, and Isolation Forest
  for multivariate outliers that no single column would catch alone.
- **Separates fact from inference.** Every insight is structured as
  Observed Facts → Possible Causes → Business Impact → Recommended Action.
  The system never states an inferred cause as a confirmed fact, and never
  invents a number — every statistic is computed in Python, not guessed by
  an LLM.
- **Picks its own charts** — line charts for time series (with anomaly
  markers), bar charts for category comparisons, scatter plots for
  correlated metrics, histograms for distributions, box plots for spread.
- **Alerts your team** — configurable severity threshold, deduplicated
  email alerts via SMTP, and a persisted alert history.

## Architecture

```
Data Ingestion Agent      reads CSV/XLSX, detects Excel sheets
        ↓
Data Profiling Agent      infers schema, scores data quality
        ↓
Analytics Agent           generates KPIs, detects trends
        ↓
Anomaly Detection Agent   z-score / IQR / Isolation Forest
        ↓
Business Intelligence     turns statistics into fact vs. inference narrative
Agent                     (deterministic templates; optional Claude API
                           for prose polish — never for the numbers)
        ↓
Visualization Agent       chooses chart types, builds chart specs
        ↓
Alert Agent               evaluates severity threshold, sends deduplicated
                           email alerts, records history
        ↓
Report Agent              assembles the final AnalysisResult / markdown report
```

Each agent is a plain Python module in `backend/agents/` with a single,
testable entry point — no framework magic, no hidden state.

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 19 + TypeScript, Vite, Tailwind CSS v4, Recharts |
| Backend | Python, FastAPI, Pandas, NumPy, scikit-learn (Isolation Forest) |
| Database | SQLite by default (swappable for Postgres — see `backend/utils/db.py`) |
| AI (optional) | Anthropic API for narrative polish; the app runs fully without a key |
| Email | SMTP via `smtplib`; runs in dry-run/logging mode without credentials |

## Project structure

```
backend/
  agents/                 the 8-agent pipeline described above
  services/
    email_service.py      SMTP wrapper, dry-run when unconfigured
  models/
    schemas.py             all Pydantic request/response models
  routes/
    upload.py  analysis.py  alerts.py
  utils/
    db.py                  SQLite persistence
    dataset_store.py       in-process DataFrame cache
  tests/
    test_anomaly.py  test_profiling.py  test_api.py
  data/
    sample_sales_data.csv       2 years, ~38k rows, real injected anomalies
    generate_sample_data.py     regenerate it if you want different data
  main.py  requirements.txt  .env.example

frontend/
  src/
    pages/    UploadPage · DashboardPage · AlertSettingsPage
    components/ KpiCard · SignalStrip · ChartCard · InsightCard · AnomalyTable · SeverityBadge
    lib/api.ts  types/api.ts
  .env.example
```

## Setup

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # optional but recommended
pip install -r requirements.txt
cp .env.example .env       # fill in ANTHROPIC_API_KEY / SMTP_* if you want them — both optional
uvicorn main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

Run the tests:
```bash
pytest tests/ -v
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env       # points at http://localhost:8000 by default
npm run dev
```

Open http://localhost:5173 — drop a CSV/XLSX, or click "explore with the
sample sales dataset" to see the full pipeline run against pre-loaded data
with real, intentionally injected anomalies (a regional revenue drop, a
bulk-order outlier, a margin squeeze, and an unexplained regional spike).

## Design notes

- **Numbers are never invented.** All KPIs, trends, and anomaly values are
  computed deterministically in Python (`pandas`/`numpy`/`scikit-learn`).
  If `ANTHROPIC_API_KEY` is set, the Business Intelligence Agent asks Claude
  to phrase those pre-computed numbers as fluent prose — it is explicitly
  instructed not to alter or invent them, and the pipeline works identically
  (via template-based narrative) without the key.
- **The rolling anomaly baseline excludes the current point** — an early
  version accidentally let the anomalous day pull down its own "expected"
  value, masking the anomaly. The baseline is now computed strictly on the
  trailing window.
- **Severity blends statistical and business magnitude** — a mild z-score
  can still represent a business-material percentage swing on a volatile
  series, so severity takes the more serious of the two signals.
- **The original uploaded file is never modified.** All cleaning/scoring
  happens on an in-memory copy.

## Extending it

- Swap SQLite for Postgres: replace the `sqlite3` calls in `backend/utils/db.py`
  with `psycopg2`/`SQLAlchemy` — the schema is already normalized.
- Add more anomaly methods per metric in `agents/anomaly_agent.py`
  (e.g. seasonal decomposition for strongly seasonal series).
- Add authentication/multi-tenancy: `utils/dataset_store.py` and the alert
  settings table are the two places that currently assume a single user.
