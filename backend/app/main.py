"""FastAPI entrypoint for the AI Credit Underwriter backend (Team A)."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    applications,
    audit,
    auth,
    dashboard,
    decisions,
    documents,
    risk,
    underwriting,
    what_if,
)
from app.config import get_settings
from app.db.database import init_db

settings = get_settings()


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version="0.2.0",
    description="Main backend for the AI Agentic Credit Underwriter (Team A).",
    lifespan=_lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip().rstrip("/") for o in settings.CORS_ORIGINS if o.strip()],
    allow_origin_regex=(getattr(settings, "CORS_ORIGIN_REGEX", None) or None),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Route modules (each mounted under its resource path)
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(applications.router, prefix="/applications", tags=["applications"])
app.include_router(documents.router, prefix="/applications", tags=["documents"])
app.include_router(documents.delete_router, tags=["documents"])
app.include_router(underwriting.router, prefix="/underwriting", tags=["underwriting"])
app.include_router(decisions.router, tags=["decisions"])
app.include_router(audit.router, tags=["audit"])
app.include_router(what_if.router, tags=["what-if"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
app.include_router(risk.router, prefix="/risk", tags=["risk"])


@app.api_route("/", methods=["GET", "HEAD"], tags=["system"])
async def root() -> dict[str, Any]:
    """Landing page + platform health probe target (Render probes "/" with HEAD)."""
    return {
        "service": settings.APP_NAME,
        "ok": True,
        "docs": "/docs",
        "health": "/health",
        "policies": "/policies",
        "mock_ai_mode": settings.MOCK_AI_MODE,
        "note": "This is the backend API. Open the Next.js frontend for the dashboard UI.",
    }


@app.get("/health", tags=["system"])
async def health() -> dict[str, Any]:
    """Liveness probe (+ AI service reachability)."""
    from app.services import ai_service

    ai: dict[str, Any]
    try:
        ai = await ai_service.health()
    except Exception as exc:  # pragma: no cover
        ai = {"status": "unreachable", "error": str(exc)}
    return {"status": "ok", "service": "backend", "mock_ai_mode": settings.MOCK_AI_MODE,
            "ai_service_url": settings.AI_SERVICE_URL, "ai_service": ai,
            # surfaced so a CORS misconfiguration can be diagnosed from the browser
            "cors_origins": settings.CORS_ORIGINS,
            "cors_origin_regex": getattr(settings, "CORS_ORIGIN_REGEX", None)}


@app.get("/policies", tags=["system"])
async def policies() -> dict[str, Any]:
    """Policy profiles exposed by the AI service (for the settings / what-if screens)."""
    from app.services import ai_service

    try:
        return await ai_service.get_policies()
    except ai_service.AIServiceError as exc:
        return {"error": str(exc)}
