"""
AI-Powered Analytics Agent — FastAPI backend entrypoint.

Run locally:
    uvicorn main:app --reload --port 8000

API docs: http://localhost:8000/docs
"""
from __future__ import annotations
import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("analytics_agent")

from utils.db import init_db  # noqa: E402
from routes import upload, analysis, alerts, email, report  # noqa: E402

app = FastAPI(
    title="AI-Powered Analytics Agent",
    description="Upload a dataset and let an agent pipeline detect trends, anomalies, "
                "and generate business insights automatically.",
    version="1.0.0",
)

allowed_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup() -> None:
    init_db()
    logger.info("Database initialized. Analytics Agent API ready.")


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error. Check server logs."})


@app.get("/api/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok", "service": "analytics-agent-api"}


app.include_router(upload.router)
app.include_router(analysis.router)
app.include_router(alerts.router)
app.include_router(email.router)
app.include_router(report.router)
