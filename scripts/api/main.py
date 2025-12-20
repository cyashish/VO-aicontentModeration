"""FastAPI backend that exposes dashboard-friendly endpoints.

These endpoints are called by Next.js API routes:
- GET /metrics/hourly
- GET /queue
- GET /realtime/recent

The implementation is intentionally simple: query Postgres tables that
the pipeline writes to.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Query

from lib.database import db


app = FastAPI(title="Moderation API", version="0.1.0")


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics/hourly")
def metrics_hourly(hours: int = Query(default=24, ge=1, le=168)) -> Dict[str, Any]:
    """Return a dashboard summary + a small hourly series.

    Shape is aligned to the UI KPI cards in [`app/page.tsx`](../../app/page.tsx:14).
    """
    # Prefer computed metrics (always available once pipeline writes moderation_results)
    summary = db.get_moderation_summary(hours=hours)
    series_rows = db.get_moderation_hourly_series(hours=hours)

    window_seconds = hours * 3600
    throughput = int(summary["totalProcessed"] / max(1, window_seconds))

    pending_review = db.get_review_queue_count()

    series = [
        {
            "hour": (r.get("hour") or datetime.utcnow()).isoformat(),
            "total": int(r.get("total", 0) or 0),
            "approved": int(r.get("approved", 0) or 0),
            "rejected": int(r.get("rejected", 0) or 0),
            "avgLatencyMs": float(r.get("avg_latency_ms", 0) or 0),
        }
        for r in series_rows
    ]

    return {
        **summary,
        "pendingReview": pending_review,
        "throughputPerSec": throughput,
        "slaCompliance": 95.0,
        "series": series,
    }


@app.get("/queue")
def queue(priority: Optional[str] = None, limit: int = Query(default=50, ge=1, le=200)) -> List[Dict[str, Any]]:
    return db.get_review_queue(priority=priority, limit=limit)


@app.get("/realtime/recent")
def realtime_recent(limit: int = Query(default=100, ge=1, le=500)) -> List[Dict[str, Any]]:
    return db.get_realtime_recent(limit=limit)

