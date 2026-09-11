"""What-if scenario orchestration (Team A)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.services import underwriting_service


async def run_what_if(db: Session, run_id: str, scenario: dict[str, Any], actor: str | None = None) -> dict[str, Any]:
    """Evaluate a hypothetical scenario without mutating the base run."""
    return await underwriting_service.run_what_if(db, run_id, scenario, actor=actor)


def list_what_ifs(db: Session, run_id: str) -> list[dict[str, Any]]:
    return underwriting_service.list_what_ifs(db, run_id)
