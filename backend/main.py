from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.db import init_tables
from backend.api.routes import router as api_router


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

    app.include_router(api_router, prefix="/api")
    return app


app = create_app()
