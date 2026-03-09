import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import requests

BASE = "https://gis.montgomeryal.gov/server/rest/services/HostedDatasets/Received_311_Service_Request/FeatureServer/0/query"

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Fields requested by the user
FIELD_LIST = [
    "Request_ID",
    "Create_Date",
    "Close_Date",
    "Status",
    "Request_Type",
    "Department",
    "Origin",
    "District",
    "Latitude",
    "Longitude",
]


def fetch_page(offset: int, page_size: int = 2000) -> Dict[str, Any]:
    params = {
        "where": "1=1",
        "outFields": ",".join(FIELD_LIST),
        "returnGeometry": False,
        "orderByFields": "Create_Date DESC",
        "resultOffset": offset,
        "resultRecordCount": page_size,
        "f": "json",
    }
    r = requests.get(BASE, params=params, timeout=60)
    r.raise_for_status()
    return r.json()


def to_iso(ts_ms: Any) -> str | None:
    try:
        if ts_ms is None:
            return None
        return datetime.fromtimestamp(int(ts_ms) / 1000, tz=timezone.utc).isoformat()
    except Exception:
        return None


def export(max_rows: int = 20000) -> tuple[Path, Path, int]:
    rows: List[Dict[str, Any]] = []
    offset = 0
    page_size = 2000

    while len(rows) < max_rows:
        data = fetch_page(offset, page_size)
        feats = data.get("features", [])
        if not feats:
            break
        for f in feats:
            a = f.get("attributes", {})
            row = {
                # keep exact field names requested
                "Request_ID": a.get("Request_ID"),
                "Create_Date": a.get("Create_Date"),
                "Close_Date": a.get("Close_Date"),
                "Status": a.get("Status"),
                "Request_Type": a.get("Request_Type"),
                "Department": a.get("Department"),
                "Origin": a.get("Origin"),
                "District": a.get("District"),
                "Latitude": a.get("Latitude"),
                "Longitude": a.get("Longitude"),
                # helpful ISO timestamps
                "Create_Date_ISO": to_iso(a.get("Create_Date")),
                "Close_Date_ISO": to_iso(a.get("Close_Date")),
            }
            rows.append(row)
            if len(rows) >= max_rows:
                break
        if len(feats) < page_size:
            break
        offset += len(feats)

    # Filenames include count for clarity
    csv_path = DATA_DIR / f"requests_extract_{len(rows)}.csv"
    json_path = DATA_DIR / f"requests_extract_{len(rows)}.json"

    # Write CSV
    fieldnames = FIELD_LIST + ["Create_Date_ISO", "Close_Date_ISO"]
    with csv_path.open("w", newline="", encoding="utf-8") as fp:
        w = csv.DictWriter(fp, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    # Write JSON
    json_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return csv_path, json_path, len(rows)


def main():
    # Export a larger sample by default (50k)
    csv_path, json_path, n = export(max_rows=50000)
    print(f"Wrote {n} rows to {csv_path} and {json_path}")


if __name__ == "__main__":
    main()
