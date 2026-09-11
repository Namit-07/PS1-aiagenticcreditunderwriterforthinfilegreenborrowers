"""Underwriting run routes — Team A.

GET  /underwriting/{run_id}
POST /underwriting/{run_id}/resume
GET  /underwriting/{run_id}/trace
GET  /underwriting/{run_id}/replay
POST /underwriting/{run_id}/what-if

(Starting an underwrite lives under the applications router:
POST /applications/{id}/underwrite.)
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.underwriting import ResumePayload, WhatIfRequest
from app.services import credit_memo_service, underwriting_service, what_if_service
from app.services.auth_service import current_user

router = APIRouter()


@router.get("/{run_id}/memo.pdf")
async def get_memo_pdf(run_id: str, db: Session = Depends(get_db)) -> Response:
    """The auto-generated credit memo PDF for a run (rendered on completion, cached on disk)."""
    pdf = await credit_memo_service.memo_pdf_for_run(db, run_id)
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="credit-memo-{run_id}.pdf"'})


@router.get("/{run_id}")
async def get_run(run_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Current state of an underwriting run (synced from the AI service, mirrored locally)."""
    return await underwriting_service.get_run(db, run_id)


@router.post("/{run_id}/resume")
async def resume_run(run_id: str, payload: ResumePayload, db: Session = Depends(get_db),
                     user: dict | None = Depends(current_user)) -> dict[str, Any]:
    """Resume a paused run with reviewer actions (accept / correct / reject per field)."""
    body = payload.model_dump(exclude_none=True)
    body.setdefault("reviewer", (user or {}).get("email") or "reviewer")
    return await underwriting_service.resume_run(db, run_id, body, actor=body["reviewer"])


@router.get("/{run_id}/trace")
async def get_trace(run_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Decision trace (AI-service audit events + node statuses + backend events)."""
    return await underwriting_service.get_trace(db, run_id)


@router.get("/{run_id}/replay")
async def replay_run(run_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Deterministic replay of the run with a diff against the recorded outcome."""
    return await underwriting_service.replay_run(db, run_id)


@router.post("/{run_id}/what-if")
async def run_what_if(run_id: str, scenario: WhatIfRequest, db: Session = Depends(get_db),
                      user: dict | None = Depends(current_user)) -> dict[str, Any]:
    """Run a what-if scenario for an underwriting run (base run stays immutable)."""
    return await what_if_service.run_what_if(db, run_id, scenario.model_dump(), actor=(user or {}).get("email"))
