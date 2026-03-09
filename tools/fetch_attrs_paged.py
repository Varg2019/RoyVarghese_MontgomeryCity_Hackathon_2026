import json
from pathlib import Path
from typing import Any, Dict, List

import requests

BASE = "https://gis.montgomeryal.gov/server/rest/services/HostedDatasets/Received_311_Service_Request/FeatureServer/0/query"

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE = DATA_DIR / "sample_attrs.json"


def fetch_page(offset: int, record_count: int = 2000) -> Dict[str, Any]:
    params = {
        "where": "1=1",
        "outFields": "Department,Request_Type,Status,Origin,Create_Date,Close_Date,Year",
        "returnGeometry": False,
        "orderByFields": "Create_Date DESC",
        "resultOffset": offset,
        "resultRecordCount": record_count,
        "f": "json",
    }
    r = requests.get(BASE, params=params, timeout=60)
    r.raise_for_status()
    return r.json()


def main(max_pages: int = 10):
    features: List[Dict[str, Any]] = []
    fields: List[Dict[str, Any]] = []
    offset = 0
    for i in range(max_pages):
        data = fetch_page(offset)
        if i == 0:
            fields = data.get("fields", [])
        page_feats = data.get("features", [])
        if not page_feats:
            break
        features.extend(page_feats)
        if len(page_feats) < 2000:
            break
        offset += len(page_feats)

    OUT_FILE.write_text(json.dumps({
        "fields": fields,
        "features": features,
    }), encoding="utf-8")
    print(f"Wrote {len(features)} features to {OUT_FILE}")


if __name__ == "__main__":
    main()
