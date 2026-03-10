from __future__ import annotations

import os
import threading
from pathlib import Path

from backend.db import ROOT, get_con
from backend.services.ingest import ingest_csv

_lock = threading.Lock()


def _env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _find_bootstrap_csv() -> Path | None:
    data_dir = ROOT / "data"
    preferred_name = os.getenv("AUTO_BOOTSTRAP_CSV", "requests_extract_20000.csv")
    preferred = data_dir / preferred_name
    if preferred.exists():
        return preferred
    csv_files = sorted(data_dir.glob("*.csv"))
    return csv_files[0] if csv_files else None


def ensure_data_loaded() -> bool:
    """Ensure tickets table has data; ingest bootstrap CSV if empty.

    Returns True when tickets have data (existing or successfully bootstrapped),
    otherwise False.
    """
    if not _env_flag("AUTO_BOOTSTRAP_ON_EMPTY", True):
        return True

    con = get_con()
    try:
        total = int(con.execute("select count(*) from tickets").fetchone()[0] or 0)
    finally:
        con.close()
    if total > 0:
        return True

    with _lock:
        con = get_con()
        try:
            total = int(con.execute("select count(*) from tickets").fetchone()[0] or 0)
        finally:
            con.close()
        if total > 0:
            return True

        csv_path = _find_bootstrap_csv()
        if not csv_path:
            print("[bootstrap] tickets empty and no CSV found under data/.")
            return False
        try:
            summary = ingest_csv(csv_path)
            print(f"[bootstrap] loaded {summary.get('total_rows', 0)} rows from {csv_path.name}")
            return int(summary.get("total_rows", 0) or 0) > 0
        except Exception as e:
            print(f"[bootstrap] failed to ingest {csv_path}: {e}")
            return False
