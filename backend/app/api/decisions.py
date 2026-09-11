"""Decision routes — Team A.

GET  /applications/{id}/credit-memo            (JSON; ?format=pdf for the PDF export)
POST /applications/{id}/decision               (reviewer finalize / override)
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.decision import FinalizeDecisionRequest
from app.services import credit_memo_service, underwriting_service
from app.services.auth_service import current_user

router = APIRouter()


@router.get("/applications/{application_id}/credit-memo")
async def get_credit_memo(application_id: str, format: str = Query("json", pattern="^(json|pdf)$"),
                          db: Session = Depends(get_db)):
    """Credit memo for the application's latest run — JSON by default, PDF with ?format=pdf."""
    if format == "pdf":
        pdf = await credit_memo_service.build_credit_memo(db, application_id)
        return Response(content=pdf, media_type="application/pdf",
                        headers={"Content-Disposition": f'inline; filename="credit-memo-{application_id}.pdf"'})
    return await credit_memo_service.get_memo_data(db, application_id)


@router.post("/applications/{application_id}/decision")
async def finalize_decision(application_id: str, payload: FinalizeDecisionRequest, db: Session = Depends(get_db),
                            user: dict | None = Depends(current_user)) -> dict[str, Any]:
    """Human reviewer finalizes/overrides the decision on the latest run.

    If the run is paused it is resumed with the override; if it is completed the
    override is recorded as an append-only backend decision and mirrored onto the run.
    """
    run = underwriting_service.latest_run_for_application(db, application_id)
    if not run:
        raise HTTPException(status_code=404, detail="no underwriting run for this application")
    reviewer = payload.reviewer or (user or {}).get("email") or "reviewer"
    view = await underwriting_service.sync_run(db, run.id)
    if view.get("status") == "awaiting_human":
        body = {"reviewer": reviewer, "reviews": [{"field": f["field"], "action": "accept", "note": payload.notes}
                                                  for f in view.get("low_confidence", [])],
                "decision_override": {"decision": payload.decision, "note": payload.notes}}
        return await underwriting_service.resume_run(db, run.id, body, actor=reviewer)
    from app.models import AuditEvent, Decision
    from app.models._base import dumps

    original = view.get("decision")
    db.add(Decision(run_id=run.id, decision=payload.decision, confidence=view.get("confidence"),
                    reasons_json=dumps(view.get("reasons") or []), decided_by=reviewer, is_override=1, note=payload.notes))
    db.add(AuditEvent(run_id=run.id, sequence=underwriting_service._next_seq(db, run.id), step="DECISION_FINALIZED",
                      actor=reviewer, payload_json=dumps({"from": original, "to": payload.decision,
                                                          "note": payload.notes})))
    # Persist the override into the mirrored state so later syncs (see _mirror) keep it.
    view["human_override"] = {"from": original, "to": payload.decision, "reviewer": reviewer, "note": payload.notes}
    view["decision"] = payload.decision
    run.decision = payload.decision
    run.state_json = dumps(view)
    db.commit()
    from app.services import application_service

    application_service.set_status(db, application_id, payload.decision, latest_decision=payload.decision)
    return view
