import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api import admin, auth, borrowers, dashboard, loans, market, notifications, paper, settings as settings_api
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db import SessionLocal, get_db
from app.services.bootstrap import bootstrap_admin

configure_logging()
settings = get_settings()
log = logging.getLogger("xvortex")


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        with SessionLocal() as db:
            bootstrap_admin(db, settings)
    except Exception:
        log.exception("startup bootstrap failed")
    yield


app = FastAPI(
    title="XVORTEX API",
    lifespan=lifespan,
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None,
    openapi_url=None if settings.is_production else "/openapi.json",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "X-CSRF-Token"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Frame-Options"] = "DENY"
    if request.url.path.startswith("/api"):
        response.headers["Cache-Control"] = "no-store"
    if settings.is_production:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(dashboard.router)
app.include_router(borrowers.router)
app.include_router(loans.router)
app.include_router(market.router)
app.include_router(paper.router)
app.include_router(settings_api.router)
app.include_router(notifications.router)


@app.get("/healthz", include_in_schema=False)
async def healthz() -> dict[str, str]:
    """Liveness: the process is up. Used by Render's health check.
    Async on purpose: it runs on the event loop, so it still answers when every worker thread
    is busy (for example queued behind password hashing)."""
    return {"status": "ok"}


@app.get("/readyz", include_in_schema=False)
def readyz(db: Session = Depends(get_db)) -> dict[str, str]:
    """Readiness: the database is reachable."""
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(status_code=503, detail="database unavailable")
    return {"status": "ready"}
