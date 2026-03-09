from __future__ import annotations

from typing import Dict, Any, List, Optional
from datetime import timedelta

import numpy as np

from backend.db import get_con


EARTH_RADIUS_M = 6371000.0


def _fetch_points(days: int, request_type: Optional[str]) -> List[Dict[str, Any]]:
    con = get_con()
    params = [days]
    where = ["Latitude is not null", "Longitude is not null", "not (abs(Latitude) < 1e-6 and abs(Longitude) < 1e-6)"]
    where.append("created_at >= now() - INTERVAL '? days'")
    # Using parameterized interval is tricky; compute cutoff in Python for clarity
    cutoff_sql = "select * from tickets where 1=0"  # placeholder
    cutoff = None
    # compute cutoff timestamp now - days
    # We'll avoid parameterized INTERVAL and compare directly
    row = con.execute("select now()::timestamp").fetchone()
    now_ts = row[0]
    # DuckDB returns python datetime already
    cutoff = now_ts - timedelta(days=days)

    if request_type:
        rs = con.execute(
            """
            select Request_ID, Request_Type, Status, Department, created_at, age_hours, Latitude, Longitude
            from tickets
            where Request_Type = ?
              and created_at >= ?
              and Latitude is not null and Longitude is not null
              and not (abs(Latitude) < 1e-6 and abs(Longitude) < 1e-6)
            """,
            [request_type, cutoff],
        ).fetchall()
    else:
        rs = con.execute(
            """
            select Request_ID, Request_Type, Status, Department, created_at, age_hours, Latitude, Longitude
            from tickets
            where created_at >= ?
              and Latitude is not null and Longitude is not null
              and not (abs(Latitude) < 1e-6 and abs(Longitude) < 1e-6)
            """,
            [cutoff],
        ).fetchall()

    out = []
    for r in rs:
        out.append({
            "Request_ID": r[0],
            "Request_Type": r[1],
            "Status": r[2],
            "Department": r[3],
            "created_at": r[4],
            "age_hours": float(r[5]) if r[5] is not None else None,
            "lat": float(r[6]),
            "lon": float(r[7]),
        })
    return out


def detect_clusters(days: int = 30, request_type: Optional[str] = None, eps_meters: int = 200, min_samples: int = 5) -> Dict[str, Any]:
    """FR-CLUST-01..04: Run a lightweight DBSCAN-like clustering (no sklearn) over lat/lon.

    Implementation notes:
    - Compute pairwise haversine distances (O(n^2)) for the filtered set.
    - Identify core points with >= min_samples neighbors (within eps).
    - Build clusters by connecting edges where at least one endpoint is a core point; take connected components.
    - Ignore noise (points not connected to any core).
    """
    pts = _fetch_points(days, request_type)
    if not pts:
        return {"clusters": [], "count": 0}

    coords = np.array([[p["lat"], p["lon"]] for p in pts], dtype=float)
    R = EARTH_RADIUS_M
    # pairwise haversine distances
    lat = np.radians(coords[:, 0])
    lon = np.radians(coords[:, 1])
    sin_lat = np.sin(lat)
    cos_lat = np.cos(lat)
    # Compute pairwise using broadcasting
    dlat = lat[:, None] - lat[None, :]
    dlon = lon[:, None] - lon[None, :]
    a = np.sin(dlat / 2.0) ** 2 + cos_lat[:, None] * cos_lat[None, :] * np.sin(dlon / 2.0) ** 2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    dist = R * c  # meters

    n = dist.shape[0]
    within = dist <= float(eps_meters)
    # Core points: at least min_samples (including itself)
    neighbor_counts = within.sum(axis=1)
    is_core = neighbor_counts >= int(min_samples)

    # Build adjacency considering edges where either endpoint is core
    adjacency = within & (is_core[:, None] | is_core[None, :])
    # Remove self loops for clarity (not needed for connectivity)
    np.fill_diagonal(adjacency, False)

    visited = np.zeros(n, dtype=bool)
    labels = -np.ones(n, dtype=int)
    cid = 0
    for i in range(n):
        if visited[i]:
            continue
        if not is_core[i]:
            visited[i] = True
            continue
        # BFS/DFS from core i
        stack = [i]
        visited[i] = True
        labels[i] = cid
        while stack:
            u = stack.pop()
            nbrs = np.where(adjacency[u])[0]
            for v in nbrs:
                if not visited[v]:
                    visited[v] = True
                    labels[v] = cid
                    # DBSCAN adds border points too; continue traversal from any point
                    stack.append(v)
        cid += 1

    clusters: Dict[int, Dict[str, Any]] = {}
    for idx, label in enumerate(labels):
        if label == -1:
            continue  # noise
        c = clusters.setdefault(int(label), {"cluster_id": int(label), "points": []})
        c["points"].append(pts[idx])

    out_list: List[Dict[str, Any]] = []
    for cid, c in clusters.items():
        ps = c["points"]
        lats = [p["lat"] for p in ps]
        lons = [p["lon"] for p in ps]
        centroid_lat = float(np.mean(lats))
        centroid_lon = float(np.mean(lons))
        count = len(ps)
        open_count = sum(1 for p in ps if str(p["Status"]).lower().startswith("open") or "in progress" in str(p["Status"]).lower())
        ages = [p["age_hours"] for p in ps if p["age_hours"] is not None]
        avg_age = float(np.mean(ages)) if ages else None
        # Primary request type in cluster
        rt_counts: Dict[str, int] = {}
        for p in ps:
            rt = p["Request_Type"] or ""
            rt_counts[rt] = rt_counts.get(rt, 0) + 1
        primary_rt = max(rt_counts.items(), key=lambda x: x[1])[0] if rt_counts else None
        action = None
        if primary_rt:
            action = f"High concentration of {primary_rt} reports—consider targeted field sweep."
        out_list.append({
            "cluster_id": int(cid),
            "count": count,
            "open_count": int(open_count),
            "avg_age_hours": avg_age,
            "centroid_lat": centroid_lat,
            "centroid_lon": centroid_lon,
            "primary_request_type": primary_rt,
            "recommended_action": action,
        })

    out_list.sort(key=lambda x: x["count"], reverse=True)
    return {"clusters": out_list, "count": len(out_list)}
