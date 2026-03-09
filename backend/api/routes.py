from __future__ import annotations

from pathlib import Path
import json
from typing import Optional, Dict, Any

from fastapi import APIRouter, Query, Body

from backend.db import get_con, ROOT
from backend.services.ingest import ingest_csv
from backend.services.routing import recommend_department
from backend.services.eta import eta_for_ticket
from backend.services.clusters import detect_clusters
from backend.services.templates import render_update


router = APIRouter()


@router.get("/meta/distincts")
def get_distincts(field: str = Query(..., pattern="^(Request_Type|Department|Origin|District|Status)$")):
    con = get_con()
    rows = con.execute(f"select distinct {field} from tickets where {field} is not null and {field} <> '' order by 1").fetchall()
    return {"field": field, "values": [r[0] for r in rows]}


@router.post("/admin/ingest")
def api_ingest(csv_filename: str = Body(embed=True)):
    csv_path = ROOT / "data" / csv_filename
    try:
        summary = ingest_csv(csv_path)
        return {"ok": True, "summary": summary}
    except Exception as e:
        return {"ok": False, "error": str(e), "csv_path": str(csv_path)}


@router.get("/tickets/{request_id}")
def get_ticket(request_id: str):
    try:
        con = get_con()
        row = con.execute(
            """
            select Request_ID, Status, Request_Type, Department, Origin, District, created_at, create_month
            from tickets where Request_ID = ? limit 1
            """,
            [request_id],
        ).fetchone()
        if not row:
            return {"error": "not_found"}
        rec = {
            "Request_ID": row[0],
            "Status": row[1],
            "Request_Type": row[2],
            "Department": row[3],
            "Origin": row[4],
            "District": row[5],
            "created_at": row[6].isoformat() if row[6] else None,
            "create_month": int(row[7]) if row[7] is not None else None,
        }
        eta = eta_for_ticket(rec["Request_Type"], rec["Department"])
        route = recommend_department(rec)
        message_en = render_update(rec, eta, lang="en")
        message_es = render_update(rec, eta, lang="es")
        return {"ticket": rec, "eta": eta, "routing_recommendation": route, "message_en": message_en, "message_es": message_es}
    except Exception as e:
        return {"error": "lookup_failed", "detail": str(e), "request_id": request_id}


@router.get("/tickets")
def list_tickets(
    status: Optional[str] = Query(default=None),
    department: Optional[str] = Query(default=None),
    request_type: Optional[str] = Query(default=None),
    district: Optional[str] = Query(default=None),
    origin: Optional[str] = Query(default=None),
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=10000),
    offset: int = Query(default=0, ge=0),
):
    con = get_con()
    where = []
    params = []
    if status:
        where.append("Status = ?"); params.append(status)
    if department:
        where.append("Department = ?"); params.append(department)
    if request_type:
        where.append("Request_Type = ?"); params.append(request_type)
    if district:
        where.append("District = ?"); params.append(district)
    if origin:
        where.append("Origin = ?"); params.append(origin)
    if date_from:
        where.append("created_at >= ?"); params.append(date_from)
    if date_to:
        where.append("created_at <= ?"); params.append(date_to)
    sql = "select Request_ID, Status, Request_Type, Department, Origin, District, created_at, create_month from tickets"
    if where:
        sql += " where " + " and ".join(where)
    sql += " order by created_at desc limit ? offset ?"
    params.extend([limit, offset])

    rows = con.execute(sql, params).fetchall()
    out = []
    for r in rows:
        rec = {
            "Request_ID": r[0],
            "Status": r[1],
            "Request_Type": r[2],
            "Department": r[3],
            "Origin": r[4],
            "District": r[5],
            "created_at": r[6].isoformat() if r[6] else None,
            "create_month": int(r[7]) if r[7] is not None else None,
        }
        out.append(rec)
    return {"items": out, "count": len(out)}


@router.get("/ops/kpis")
def get_kpis():
    con = get_con()
    total = con.execute("select count(*) from tickets").fetchone()[0]
    open_ct = con.execute("select count(*) from tickets where not (Status ilike '%closed%')").fetchone()[0]
    mttc = con.execute(
        "select avg(resolution_hours)/24.0 from tickets where Status ilike '%closed%' and resolution_hours is not null"
    ).fetchone()[0]
    return {
        "total": int(total or 0),
        "open": int(open_ct or 0),
        "mean_time_to_close_days": float(mttc or 0.0),
    }


@router.get("/ops/misroutes")
def get_misroutes(status: str = Query(default="All"), min_conf: float = Query(default=0.8)):
    con = get_con()
    where = []
    if status in ("Open", "In Progress"):
        where.append("Status = 'Open' or Status = 'In Progress'")
    sql = "select Request_ID, Status, Request_Type, Department, Origin, District, created_at, create_month from tickets"
    if where:
        sql += " where " + " and ".join(f"({w})" for w in where)
    sql += " order by created_at desc limit 1000"
    rows = con.execute(sql).fetchall()
    items = []
    for r in rows:
        rec = {
            "Request_ID": r[0],
            "Status": r[1],
            "Request_Type": r[2],
            "Department": r[3],
            "Origin": r[4],
            "District": r[5],
            "created_at": r[6].isoformat() if r[6] else None,
            "create_month": int(r[7]) if r[7] is not None else None,
        }
        route = recommend_department({**rec, "threshold": min_conf})
        if route.get("possible_misroute"):
            items.append({"ticket": rec, "recommendation": route})
    return {"items": items, "count": len(items)}


@router.post("/ai/predict-eta")
def post_predict_eta(payload: Dict[str, Any] = Body(...)):
    return eta_for_ticket(payload.get("Request_Type"), payload.get("Department"))


@router.post("/ai/recommend-department")
def post_recommend_department(payload: Dict[str, Any] = Body(...)):
    return recommend_department(payload)


@router.get("/ops/clusters")
def get_clusters(days: int = Query(default=30), request_type: Optional[str] = Query(default=None), eps: int = Query(default=200), min_samples: int = Query(default=5)):
    return detect_clusters(days=days, request_type=request_type, eps_meters=eps, min_samples=min_samples)


@router.get("/ops/events")
def get_events(limit: int = Query(default=100)):
    con = get_con()
    rows = con.execute(
        "select request_id, event_type, payload, created_at from demo_events order by created_at desc limit ?",
        [limit],
    ).fetchall()
    return {
        "items": [
            {
                "request_id": r[0],
                "event_type": r[1],
                "payload": r[2],
                "created_at": r[3].isoformat() if r[3] else None,
            }
            for r in rows
        ]
    }


@router.get("/admin/sla")
def get_sla():
    con = get_con()
    rows = con.execute("select scope, key, target_days, effective_date, notes from sla_config order by scope, key").fetchall()
    return {"items": [{"scope": r[0], "key": r[1], "target_days": float(r[2]) if r[2] is not None else None, "effective_date": str(r[3]) if r[3] else None, "notes": r[4]} for r in rows]}


@router.post("/admin/sla")
def post_sla(item: Dict[str, Any] = Body(...)):
    con = get_con()
    con.execute(
        """
        insert into sla_config(scope, key, target_days, effective_date, notes)
        values(?, ?, ?, ?, ?)
        """,
        [item.get("scope"), item.get("key"), item.get("target_days"), item.get("effective_date"), item.get("notes")],
    )
    return {"ok": True}


@router.post("/subscribe")
def post_subscribe(email: str = Body(...), request_id: str = Body(...)):
    con = get_con()
    con.execute("insert into subscriptions(email, request_id) values(?, ?)", [email, request_id])
    return {"ok": True}


@router.post("/demo/simulate-status-change")
def simulate_status_change(request_id: str = Body(...), new_status: str = Body(...)):
    con = get_con()
    con.execute("update tickets set Status = ? where Request_ID = ?", [new_status, request_id])
    payload = json.dumps({"new_status": new_status})
    con.execute("insert into demo_events(request_id, event_type, payload) values(?, 'status_change', cast(? as JSON))", [request_id, payload])
    return {"ok": True}
