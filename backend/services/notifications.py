from __future__ import annotations

from typing import List, Dict, Any

from backend.db import get_con


def recent_events(limit: int = 100) -> List[Dict[str, Any]]:
    con = get_con()
    rows = con.execute(
        "select request_id, event_type, payload, created_at from demo_events order by created_at desc limit ?",
        [limit],
    ).fetchall()
    return [
        {
            "request_id": r[0],
            "event_type": r[1],
            "payload": r[2],
            "created_at": r[3].isoformat() if r[3] else None,
        }
        for r in rows
    ]
