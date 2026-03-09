from __future__ import annotations

from pathlib import Path
import csv
from datetime import datetime, timezone

import pytest

import backend.db as db
from backend.db import init_tables
from backend.services.ingest import ingest_csv
from backend.services.eta import eta_for_ticket
from backend.services.routing import recommend_department
from backend.services.clusters import detect_clusters


def write_csv(path: Path, rows: list[dict]):
    fieldnames = [
        "Request_ID","Create_Date","Close_Date","Status","Request_Type","Department","Origin","District","Latitude","Longitude"
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def setup_test_db(tmp_path: Path):
    # Point DB_PATH to a temp file DB
    db.DB_PATH = tmp_path / "test.duckdb"
    init_tables()


def test_epoch_conversion_and_resolution(tmp_path: Path):
    setup_test_db(tmp_path)
    # 2024-01-01T00:00:00Z -> epoch ms
    created = int(datetime(2024,1,1,0,0,0,tzinfo=timezone.utc).timestamp()*1000)
    closed = int(datetime(2024,1,3,0,0,0,tzinfo=timezone.utc).timestamp()*1000)
    csv_path = tmp_path / "ingest.csv"
    write_csv(csv_path, [{
        "Request_ID":"T1","Create_Date":created,"Close_Date":closed,"Status":"Closed","Request_Type":"TypeA","Department":"Dept1","Origin":"Web","District":"D1","Latitude":38.0,"Longitude":-77.0
    }])
    summary = ingest_csv(csv_path)
    assert summary["total_rows"] == 1
    con = db.get_con()
    row = con.execute("select created_at, closed_at, round(resolution_hours,1) from tickets where Request_ID='T1'").fetchone()
    assert row is not None
    assert row[0].isoformat().startswith("2024-01-01T00:00:00")
    assert row[1].isoformat().startswith("2024-01-03T00:00:00")
    assert float(row[2]) == pytest.approx(48.0, rel=0.01)


def test_eta_fallback_logic(tmp_path: Path):
    setup_test_db(tmp_path)
    base = int(datetime(2024,1,1,tzinfo=timezone.utc).timestamp()*1000)
    # Two closed of TypeA with 24h and 48h; p50=36h->1.5d ~ rounds to 2, p80 approx ~48h->2d
    rows = []
    def mk_row(i, cd_ms, hours, rtype, dept):
        return {"Request_ID":f"R{i}","Create_Date":cd_ms,"Close_Date":cd_ms+hours*3600*1000,
                "Status":"Closed","Request_Type":rtype,"Department":dept,
                "Origin":"Web","District":"D1","Latitude":38.0,"Longitude":-77.0}
    rows.append(mk_row(1, base, 24, "TypeA", "Dept1"))
    rows.append(mk_row(2, base, 48, "TypeA", "Dept1"))
    csv_path = tmp_path/"e.csv"; write_csv(csv_path, rows)
    ingest_csv(csv_path)
    eta = eta_for_ticket("TypeA", "Dept1")
    assert eta["eta_days_p50"] is not None and eta["eta_days_p80"] is not None
    # Now no group: fallback to global still returns values
    eta2 = eta_for_ticket(None, None)
    assert eta2["eta_days_p50"] is not None


def test_routing_output_schema_and_baseline(tmp_path: Path):
    setup_test_db(tmp_path)
    base = int(datetime(2024,1,1,tzinfo=timezone.utc).timestamp()*1000)
    rows = []
    # 3 of TypeB -> DeptX, 1 -> DeptY, expect DeptX baseline
    def mk(i, dept):
        return {"Request_ID":f"Q{i}","Create_Date":base,"Close_Date":base,"Status":"Closed","Request_Type":"TypeB",
                "Department":dept,"Origin":"Call","District":"D2","Latitude":0.1,"Longitude":0.1}
    rows += [mk(1,"DeptX"), mk(2,"DeptX"), mk(3,"DeptX"), mk(4,"DeptY")]
    p = tmp_path/"r.csv"; write_csv(p, rows); ingest_csv(p)
    rec = recommend_department({"Request_Type":"TypeB","Origin":"Call","District":"D2","create_month":1,"Department":"DeptY"})
    assert set(["recommended_department","confidence","top3","explanation","possible_misroute"]) <= set(rec.keys())
    assert rec["recommended_department"] == "DeptX"
    assert isinstance(rec["confidence"], float)


def test_dbscan_cluster_output_schema(tmp_path: Path):
    setup_test_db(tmp_path)
    base = int(datetime(2024,1,1,tzinfo=timezone.utc).timestamp()*1000)
    rows = []
    # 5 points around (38,-77) within ~50m
    coords = [(38.0000,-77.0000),(38.0003,-77.0002),(38.0002,-77.0001),(38.0001,-77.0000),(38.00025,-77.00015)]
    for i,(lat,lon) in enumerate(coords):
        rows.append({"Request_ID":f"C{i}","Create_Date":base,"Close_Date":base,"Status":"Open","Request_Type":"TypeC","Department":"DeptZ",
                     "Origin":"Web","District":"D1","Latitude":lat,"Longitude":lon})
    p = tmp_path/"c.csv"; write_csv(p, rows); ingest_csv(p)
    out = detect_clusters(days=3650, request_type="TypeC", eps_meters=100, min_samples=3)
    assert "clusters" in out
    if out["clusters"]:
        c = out["clusters"][0]
        for k in ["cluster_id","count","open_count","avg_age_hours","centroid_lat","centroid_lon","primary_request_type","recommended_action"]:
            assert k in c
