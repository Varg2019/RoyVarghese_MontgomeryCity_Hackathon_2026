from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.db import init_tables, get_con, ROOT
from backend.api.routes import router as api_router
from backend.services.ingest import ingest_csv


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


def _bootstrap_if_empty() -> None:
    if not _env_flag("AUTO_BOOTSTRAP_ON_EMPTY", True):
        return
    con = get_con()
    try:
        total = con.execute("select count(*) from tickets").fetchone()[0]
    finally:
        con.close()
    if int(total or 0) > 0:
        return

    csv_path = _find_bootstrap_csv()
    if not csv_path:
        print("[startup] tickets table empty, but no CSV found under data/. Skipping auto-bootstrap.")
        return
    try:
        summary = ingest_csv(csv_path)
        print(f"[startup] auto-bootstrap complete from {csv_path.name}: rows={summary.get('total_rows', 0)}")
    except Exception as e:
        # Keep API online even if bootstrap fails.
        print(f"[startup] auto-bootstrap failed for {csv_path}: {e}")


def create_app() -> FastAPI:
    app = FastAPI(title="Montgomery Civic Service Triage & Transparency API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def _startup():
        init_tables()
        _bootstrap_if_empty()

    app.include_router(api_router, prefix="/api")
    return app


app = create_app()
