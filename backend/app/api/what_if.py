"""What-if history route — Team A.

GET /underwriting/{run_id}/what-ifs   (the POST lives in api/underwriting.py)
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services import what_if_service

router = APIRouter()


@router.get("/underwriting/{run_id}/what-ifs")
async def list_what_ifs(run_id: str, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    """Previously evaluated scenarios for a run (each is immutable)."""
    return what_if_service.list_what_ifs(db, run_id)
