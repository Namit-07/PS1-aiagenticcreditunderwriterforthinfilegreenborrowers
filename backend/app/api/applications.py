"""Credit application routes — Team A.

POST /applications
GET  /applications
GET  /applications/{id}
POST /applications/{id}/underwrite
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.application import ApplicationCreate, ApplicationOut, UnderwriteRequest
from app.services import application_service, underwriting_service
from app.services.auth_service import current_user

router = APIRouter()


@router.post("", response_model=ApplicationOut, status_code=201)
async def create_application(payload: ApplicationCreate, db: Session = Depends(get_db),
                             user: dict | None = Depends(current_user)):
    """Create a new credit application."""
    return application_service.create_application(db, payload.model_dump(), created_by=(user or {}).get("email"))


@router.get("", response_model=list[ApplicationOut])
async def list_applications(limit: int = 25, offset: int = 0, status: str | None = None,
                            db: Session = Depends(get_db)):
    """List applications (paginated, newest first)."""
    return application_service.list_applications(db, limit=min(limit, 200), offset=offset, status=status)


@router.get("/{application_id}", response_model=ApplicationOut)
async def get_application(application_id: str, db: Session = Depends(get_db)):
    """Fetch a single application by id."""
    app = application_service.get_application_dict(db, application_id)
    if not app:
        raise HTTPException(status_code=404, detail="application not found")
    return app


@router.post("/{application_id}/underwrite", status_code=202)
async def start_underwrite(application_id: str, payload: UnderwriteRequest | None = None,
                           db: Session = Depends(get_db), user: dict | None = Depends(current_user)) -> dict[str, Any]:
    """Kick off an underwriting run for an application (proxied to the AI service)."""
    profile = payload.policy_profile if payload else None
    return await underwriting_service.start_underwrite(db, application_id, profile, started_by=(user or {}).get("email"))


@router.get("/{application_id}/runs")
async def list_application_runs(application_id: str, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    """All underwriting runs for an application (newest first)."""
    from app.models import UnderwritingRun

    rows = (db.query(UnderwritingRun).filter(UnderwritingRun.application_id == application_id)
            .order_by(UnderwritingRun.created_at.desc()).all())
    return [r.summary() for r in rows]
