from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import median
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
GEOJSON_FILE = DATA_DIR / "requests.geojson"


def parse_dt(val: Optional[str]) -> Optional[datetime]:
    if not val:
        return None
    try:
        return datetime.fromisoformat(val.replace("Z", "+00:00"))
    except Exception:
        return None


def load_features() -> List[Dict[str, Any]]:
    if not GEOJSON_FILE.exists():
        return []
    try:
        fc = json.loads(GEOJSON_FILE.read_text())
        return fc.get("features", [])
    except Exception:
        return []


def status_is_closed(status: str) -> bool:
    s = (status or "").lower()
    return any(k in s for k in ["closed", "resolved", "complete"]) and not ("incomplete" in s)


def within_days(dt: Optional[datetime], days: int) -> bool:
    if not dt:
        return False
    return dt >= datetime.now(timezone.utc) - timedelta(days=days)


def filter_features(
    features: List[Dict[str, Any]],
    status: Optional[str] = None,
    category: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> List[Dict[str, Any]]:
    df = parse_dt(date_from)
    dt = parse_dt(date_to)

    out: List[Dict[str, Any]] = []
    for f in features:
        props = f.get("properties", {})
        s = str(props.get("status", ""))
        c = str(props.get("category", ""))
        created_at = parse_dt(props.get("created_at"))

        if status and status.lower() not in s.lower():
            continue
        if category and category.lower() not in c.lower():
            continue
        if df and (not created_at or created_at < df):
            continue
        if dt and (not created_at or created_at > dt):
            continue
        out.append(f)
    return out


app = FastAPI(title="Montgomery Civic Service Transparency — Phase 1", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/requests.geojson")
def get_requests_geojson(
    status: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    date_from: Optional[str] = Query(default=None, description="ISO date e.g., 2025-01-01T00:00:00Z"),
    date_to: Optional[str] = Query(default=None, description="ISO date e.g., 2025-12-31T23:59:59Z"),
):
    feats = load_features()
    feats = filter_features(feats, status=status, category=category, date_from=date_from, date_to=date_to)
    return JSONResponse({"type": "FeatureCollection", "features": feats})


@app.get("/api/requests")
def get_requests(
    limit: int = Query(default=100, ge=1, le=10000),
    status: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
):
    feats = filter_features(load_features(), status=status, category=category)
    feats = feats[:limit]
    # Return properties only for compactness
    return [f.get("properties", {}) for f in feats]


@app.get("/api/kpis")
def get_kpis():
    feats = load_features()
    total = len(feats)
    open_count = 0
    closed_30 = 0
    closed_90 = 0
    durations_days: List[float] = []
    on_time_closed = 0
    on_time_denominator = 0
    max_updated: Optional[datetime] = None

    for f in feats:
        props = f.get("properties", {})
        status = str(props.get("status", ""))
        created = parse_dt(props.get("created_at"))
        updated = parse_dt(props.get("updated_at"))
        sla_due = parse_dt(props.get("sla_due_at"))

        if not max_updated or (updated and updated > max_updated):
            max_updated = updated

        if status_is_closed(status):
            if created and updated and updated >= created:
                durations_days.append((updated - created).total_seconds() / 86400.0)
            if within_days(updated, 30):
                closed_30 += 1
            if within_days(updated, 90):
                closed_90 += 1
            if sla_due and updated:
                on_time_denominator += 1
                if updated <= sla_due:
                    on_time_closed += 1
        else:
            open_count += 1

    med_res = median(durations_days) if durations_days else None
    on_time_pct = (on_time_closed / on_time_denominator * 100.0) if on_time_denominator else None

    return {
        "total": total,
        "open": open_count,
        "closed_30": closed_30,
        "closed_90": closed_90,
        "median_resolution_days": med_res,
        "on_time_percent": on_time_pct,
        "last_updated": (max_updated.isoformat() if max_updated else None),
    }


# Serve the static dashboard from / (web directory)
WEB_DIR = ROOT / "web"
WEB_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="static")
