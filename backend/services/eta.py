from __future__ import annotations

from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta
import numpy as np

from backend.db import get_con


def _quantiles_for(group_key: str, key_val: str) -> Tuple[Optional[float], Optional[float], int]:
    """Return p50, p80 in days and support_count for closed tickets filtered by group key.

    group_key must be one of 'Request_Type' or 'Department'.
    """
    con = get_con()
    # DuckDB compatibility: compute quantiles in Python to avoid version-specific SQL aggregate support.
    vals = [r[0] for r in con.execute(
        f"""
        select resolution_hours
        from tickets
        where Status ilike '%closed%'
          and resolution_hours is not null
          and {group_key} = ?
        order by resolution_hours
        """,
        [key_val],
    ).fetchall()]
    if not vals:
        return None, None, 0
    arr = np.array(vals, dtype=float) / 24.0
    return float(np.quantile(arr, 0.5)), float(np.quantile(arr, 0.8)), int(arr.size)


def _global_quantiles() -> Tuple[Optional[float], Optional[float], int]:
    con = get_con()
    vals = [r[0] for r in con.execute(
        """
        select resolution_hours
        from tickets
        where Status ilike '%closed%'
          and resolution_hours is not null
        order by resolution_hours
        """
    ).fetchall()]
    if not vals:
        return None, None, 0
    arr = np.array(vals, dtype=float) / 24.0
    return float(np.quantile(arr, 0.5)), float(np.quantile(arr, 0.8)), int(arr.size)


def eta_for_ticket(request_type: Optional[str], department: Optional[str]) -> Dict[str, Any]:
    """FR-ETA-01/02: return p50/p80 days and label with fallback chain.
    Order: by Request_Type -> Department -> Global.
    """
    used = "global"
    p50 = p80 = None
    n = 0
    if request_type:
        p50, p80, n = _quantiles_for("Request_Type", request_type)
        if n and p50 is not None and p80 is not None:
            used = "Request_Type"
    if (not n or p50 is None or p80 is None) and department:
        p502, p802, n2 = _quantiles_for("Department", department)
        if n2 and p502 is not None and p802 is not None:
            p50, p80, n = p502, p802, n2
            used = "Department"
    if (not n or p50 is None or p80 is None):
        p503, p803, n3 = _global_quantiles()
        p50 = p50 if p50 is not None else p503
        p80 = p80 if p80 is not None else p803
        n = max(n, n3)
        used = used or "global"

    label = None
    if p50 is not None and p80 is not None:
        low = max(0, round(p50))
        high = max(low, round(p80))
        label = f"{low}–{high} days"

    return {
        "eta_days_p50": p50,
        "eta_days_p80": p80,
        "eta_range_label": label,
        "support_count": n,
        "basis": used,
    }
