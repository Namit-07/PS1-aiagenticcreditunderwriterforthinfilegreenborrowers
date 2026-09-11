"""Dashboard stats route — Team A.

GET /dashboard/stats
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services import dashboard_service

router = APIRouter()


@router.get("/stats")
async def dashboard_stats(db: Session = Depends(get_db)) -> dict[str, Any]:
    """Aggregate KPIs for the frontend dashboard."""
    return dashboard_service.stats(db)
