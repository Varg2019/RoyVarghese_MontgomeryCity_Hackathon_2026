import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

BASE = "https://gis.montgomeryal.gov/server/rest/services/HostedDatasets/Received_311_Service_Request/FeatureServer/0"

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = DATA_DIR / "last_sync.json"
GEOJSON_FILE = DATA_DIR / "requests.geojson"
LIST_FILE = DATA_DIR / "requests_list.json"


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def load_last_sync_ms(default_days_back: int = 30) -> int:
    if STATE_FILE.exists():
        try:
            obj = json.loads(STATE_FILE.read_text())
            return int(obj.get("last_sync_epoch_ms", 0))
        except Exception:
            pass
    dt = now_utc() - timedelta(days=default_days_back)
    return int(dt.timestamp() * 1000)


def save_last_sync_ms(ms: int) -> None:
    STATE_FILE.write_text(json.dumps({"last_sync_epoch_ms": ms, "saved_at": int(time.time() * 1000)}, indent=2))


def arcgis_query(where: str, out_fields: str = "*", result_offset: int = 0, result_record_count: int = 2000) -> Dict[str, Any]:
    url = f"{BASE}/query"
    params = {
        "where": where,
        "outFields": out_fields,
        "f": "json",
        "returnGeometry": True,
        "orderByFields": "EditDate DESC",
        "resultOffset": result_offset,
        "resultRecordCount": result_record_count,
    }
    r = requests.get(url, params=params, timeout=60)
    r.raise_for_status()
    return r.json()


def pick_field(attrs: Dict[str, Any], candidates: List[str]) -> Optional[Any]:
    for c in candidates:
        if c in attrs and attrs[c] not in (None, ""):
            return attrs[c]
    return None


def ts_to_dt(ts_ms: Optional[int]) -> Optional[datetime]:
    try:
        if ts_ms is None:
            return None
        return datetime.fromtimestamp(int(ts_ms) / 1000, tz=timezone.utc)
    except Exception:
        return None


def compute_priority(category: str, description: str) -> int:
    cat = (category or "").lower()
    desc = (description or "").lower()
    score = 10
    if any(k in cat or k in desc for k in ["drain", "ditch", "flood", "blocked"]):
        score += 30
    if any(k in cat or k in desc for k in ["pothole", "road", "street damage", "asphalt"]):
        score += 20
    if any(k in cat or k in desc for k in ["grass", "overgrown", "weeds", "nuisance"]):
        score += 5
    if any(k in desc for k in ["injury", "electrical", "fire", "collapse", "hazard"]):
        score += 20
    return max(0, min(score, 100))


def compute_sla_due(created_at: Optional[datetime], category: str, priority: int) -> Optional[datetime]:
    if not created_at:
        return None
    cat = (category or "").lower()
    # Base days by category
    days = 10
    if any(k in cat for k in ["pothole", "road", "street"]):
        days = 3
    if any(k in cat for k in ["drain", "ditch", "flood"]):
        days = 2
    if any(k in cat for k in ["nuisance", "grass", "weeds"]):
        days = 10
    # Priority adjustment: high priority shortens due
    if priority >= 60:
        days = max(1, days - 1)
    return created_at + timedelta(days=days)


def to_feature_geojson(attrs: Dict[str, Any], geom: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    # Convert ESRI geometry to GeoJSON. Assume points for 311; fallback to None.
    geometry: Optional[Dict[str, Any]] = None
    if geom and isinstance(geom, dict):
        if "x" in geom and "y" in geom:
            geometry = {"type": "Point", "coordinates": [geom["x"], geom["y"]]}
        # For non-point types, could map rings/paths here if needed.

    created_at = ts_to_dt(pick_field(attrs, ["CreationDate", "CreateDate", "CreatedDate"]))
    updated_at = ts_to_dt(pick_field(attrs, ["EditDate", "LastEditDate", "UpdatedDate"]))
    status = pick_field(attrs, ["Status", "status", "CurrentStatus"]) or "Unknown"
    category = pick_field(attrs, [
        "Category",
        "ServiceType",
        "RequestType",
        "Request_Type",
        "Type",
        "Subtype",
    ]) or "Unspecified"
    description = str(pick_field(attrs, ["Description", "ShortDesc", "RequestDescription"]) or "").strip()

    priority = compute_priority(str(category), description)
    sla_due_dt = compute_sla_due(created_at, str(category), priority)

    props = {
        "object_id": pick_field(attrs, ["OBJECTID", "ObjectID", "objectid"]),
        "created_at": created_at.isoformat() if created_at else None,
        "updated_at": updated_at.isoformat() if updated_at else None,
        "status": status,
        "category": category,
        "description_redacted": description[:500],
        "priority_score": priority,
        "sla_due_at": sla_due_dt.isoformat() if sla_due_dt else None,
        "source_layer": "Received_311_Service_Request",
        "triage_version": "v0.1-rule",
    }

    return {"type": "Feature", "geometry": geometry, "properties": props}


def ingest() -> None:
    last_sync_ms = load_last_sync_ms()
    where = f"EditDate>={last_sync_ms}"

    features: List[Dict[str, Any]] = []
    offset = 0
    page = 0
    while True:
        page += 1
        data = arcgis_query(where=where, result_offset=offset)
        feats = data.get("features", [])
        for f in feats:
            attrs = f.get("attributes", {})
            geom = f.get("geometry")
            features.append(to_feature_geojson(attrs, geom))
        if not feats or len(feats) < 2000:
            break
        offset += len(feats)

    # Merge with existing store to maintain full history within the demo
    existing: Dict[str, Dict[str, Any]] = {}
    if LIST_FILE.exists():
        try:
            existing_list = json.loads(LIST_FILE.read_text())
            for e in existing_list:
                oid = str(e.get("properties", {}).get("object_id"))
                if oid:
                    existing[oid] = e
        except Exception:
            pass

    for feat in features:
        oid = str(feat.get("properties", {}).get("object_id"))
        if oid:
            existing[oid] = feat

    merged_list = list(existing.values())

    # Persist as list and GeoJSON FeatureCollection
    LIST_FILE.write_text(json.dumps(merged_list, indent=2))
    fc = {"type": "FeatureCollection", "features": merged_list}
    GEOJSON_FILE.write_text(json.dumps(fc))

    # Update last sync time to now
    save_last_sync_ms(int(now_utc().timestamp() * 1000))
    print(f"Synced {len(features)} updates; total stored: {len(merged_list)}")


if __name__ == "__main__":
    ingest()
