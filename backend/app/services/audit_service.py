"""Audit trail recording and replay (Team A) — thin wrappers over the run mirror."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditEvent
from app.models._base import dumps
from app.services import underwriting_service


def record_event(db: Session, run_id: str, step: str, actor: str, payload: dict[str, Any]) -> None:
    """Persist an immutable backend-side audit event for a run."""
    db.add(AuditEvent(run_id=run_id, sequence=underwriting_service._next_seq(db, run_id), step=step, actor=actor,
                      payload_json=dumps(payload)))
    db.commit()


async def get_trace(db: Session, run_id: str) -> dict[str, Any]:
    """Return the ordered decision trace for a run (AI trace + backend events)."""
    return await underwriting_service.get_trace(db, run_id)


async def replay_run(db: Session, run_id: str) -> dict[str, Any]:
    """Reconstruct a run deterministically and diff it against the recorded outcome."""
    return await underwriting_service.replay_run(db, run_id)


def list_runs(db: Session, limit: int = 100, status: str | None = None) -> list[dict[str, Any]]:
    return underwriting_service.list_runs(db, limit=limit, status=status)
