"""Audit routes (read-only trace + replay interface) — Team A."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services import audit_service

router = APIRouter()


@router.get("/audit/runs")
async def list_runs(limit: int = 100, status: str | None = None, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    """List audit-able underwriting runs (feeds the human-review queue when status=awaiting_human)."""
    return audit_service.list_runs(db, limit=min(limit, 500), status=status)


@router.get("/audit/runs/{run_id}")
async def get_audit_trail(run_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Full audit trail for a run."""
    return await audit_service.get_trace(db, run_id)


@router.get("/audit/runs/{run_id}/replay")
async def replay_run(run_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Replay / reconstruct an underwriting run and diff it against the stored outcome."""
    return await audit_service.replay_run(db, run_id)
