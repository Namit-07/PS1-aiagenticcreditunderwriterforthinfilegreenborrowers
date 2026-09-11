"""Underwriting orchestration on the backend (Team A).

Coordinates calls to the AI service and mirrors run state into the application
database (runs, evidence, decisions, financials, risk, reconciliation, human reviews,
memos, audit events). The actual AI agent logic lives in the AI service — never here.
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import (
    Application,
    AuditEvent,
    CreditMemo,
    Decision,
    Evidence,
    FinancialMetric,
    HumanReview,
    ReconciliationItem,
    ReplaySnapshot,
    RiskScore,
    UnderwritingRun,
    WhatIfRun,
)
from app.models._base import dumps, loads, utcnow
from app.services import ai_service, application_service

# AI run status -> application status
_APP_STATUS = {"created": "underwriting", "running": "underwriting", "awaiting_human": "awaiting_human",
               "failed": "decision_pending"}


def _raise(exc: ai_service.AIServiceError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=str(exc))


async def start_underwrite(db: Session, application_id: str, policy_profile: str | None = None,
                           started_by: str | None = None) -> dict[str, Any]:
    """Submit the application + document texts to the AI service and record the run."""
    payload = application_service.application_payload_for_ai(db, application_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="application not found")
    try:
        resp = await ai_service.submit_underwrite(payload, policy_profile)
    except ai_service.AIServiceError as exc:
        _raise(exc)
    run_id = str(resp["run_id"])
    run = UnderwritingRun(id=run_id, application_id=application_id, status=str(resp.get("status", "running")),
                          policy_profile=policy_profile, started_by=started_by)
    db.add(run)
    # The models carry FK columns but no ORM relationships, so SQLAlchemy cannot order
    # these inserts by dependency; flush the parent row first or Postgres rejects the child.
    db.flush()
    db.add(AuditEvent(run_id=run_id, sequence=0, step="RUN_REQUESTED", actor=started_by or "system",
                      payload_json=dumps({"policy_profile": policy_profile, "documents": len(payload["documents"])})))
    application_service.set_status(db, application_id, "underwriting", latest_run_id=run_id)
    db.commit()
    # first sync (in-process AI service completes synchronously; over the network it is a quick poll)
    try:
        await sync_run(db, run_id)
    except HTTPException:
        pass
    return {"run_id": run_id, "application_id": application_id, "status": db.get(UnderwritingRun, run_id).status}


def _mirror(db: Session, run: UnderwritingRun, view: dict[str, Any]) -> None:
    """Copy the AI-service view into the backend tables (idempotent)."""
    run.status = str(view.get("status") or run.status)
    # A reviewer override recorded by the backend on a completed run must outlive re-syncs
    # from the AI service (which only knows about overrides applied through resume).
    if run.status == "completed" and not view.get("human_override"):
        last_override = (db.query(Decision).filter(Decision.run_id == run.id, Decision.is_override == 1)
                         .order_by(Decision.created_at.desc()).first())
        if last_override and last_override.decided_by != "ai-service" and last_override.decision != view.get("decision"):
            view["human_override"] = {"from": view.get("decision"), "to": last_override.decision,
                                      "reviewer": last_override.decided_by, "note": last_override.note}
            view["decision"] = last_override.decision
    run.decision = view.get("decision")
    run.confidence = view.get("confidence")
    pol = view.get("policy") or {}
    run.policy_profile = pol.get("profile") or run.policy_profile
    run.policy_version = pol.get("version") or run.policy_version
    run.state_json = dumps(view)
    if run.status == "completed" and not run.completed_at:
        run.completed_at = view.get("completed_at") or utcnow()

    rid = run.id
    db.query(Evidence).filter(Evidence.run_id == rid).delete()
    for e in view.get("evidence") or []:
        db.add(Evidence(run_id=rid, document_ref=e.get("source_document"), field_name=str(e.get("field")),
                        value_json=dumps({"value": e.get("value")}), confidence=float(e.get("confidence") or 0.0),
                        page=e.get("page"), evidence_text=e.get("evidence"),
                        review_status=str(e.get("review_status") or "auto")))
    db.query(ReconciliationItem).filter(ReconciliationItem.run_id == rid).delete()
    for i in (view.get("reconciliation") or {}).get("items") or []:
        db.add(ReconciliationItem(run_id=rid, type=str(i.get("type")), severity=str(i.get("severity")),
                                  description=i.get("description"), payload_json=dumps(i)))
    db.query(HumanReview).filter(HumanReview.run_id == rid).delete()
    for h in view.get("human_reviews") or []:
        db.add(HumanReview(id=str(h.get("id")) if h.get("id") else None, run_id=rid, field=str(h.get("field")),
                           original_json=dumps({"value": h.get("original_value")}),
                           corrected_json=dumps({"value": h.get("corrected_value")}), action=str(h.get("action")),
                           reviewer=h.get("reviewer"), note=h.get("note"), timestamp=h.get("timestamp") or utcnow()))
    fin = view.get("financials")
    if fin:
        fm = db.get(FinancialMetric, rid) or FinancialMetric(run_id=rid)
        fm.monthly_income = fin.get("monthly_income", fin.get("verified_income"))
        fm.total_monthly_obligations = fin.get("total_monthly_obligations", fin.get("existing_obligations"))
        fm.monthly_emi = fin.get("monthly_emi", fin.get("emi"))
        fm.foir, fm.ltv = fin.get("foir"), fin.get("ltv")
        fm.formula_version = fin.get("formula_version")
        fm.metrics_json = dumps(fin)
        db.merge(fm)
    risk = view.get("risk")
    if risk:
        rs = db.get(RiskScore, rid) or RiskScore(run_id=rid)
        rs.risk_score, rs.risk_band = risk.get("risk_score"), risk.get("risk_band")
        rs.model_version, rs.model_backend = risk.get("model_version"), risk.get("model_backend")
        rs.features_json = dumps(risk.get("features") or {})
        db.merge(rs)
    if view.get("decision") and run.status == "completed":
        last = (db.query(Decision).filter(Decision.run_id == rid).order_by(Decision.created_at.desc()).first())
        override = view.get("human_override")
        if not last or last.decision != view["decision"] or bool(last.is_override) != bool(override):
            db.add(Decision(run_id=rid, decision=str(view["decision"]), confidence=view.get("confidence"),
                            reasons_json=dumps(view.get("reasons") or []),
                            decided_by=(override or {}).get("reviewer") or "ai-service",
                            is_override=1 if override else 0, note=(override or {}).get("note")))
    memo = view.get("memo")
    if memo:
        cm = db.query(CreditMemo).filter(CreditMemo.run_id == rid).first()
        if cm:
            cm.memo_json = dumps(memo)
        else:
            db.add(CreditMemo(run_id=rid, application_id=run.application_id, memo_json=dumps(memo)))

    # Automatic credit-memo PDF: rendered once, the first time a completed run is mirrored.
    view["memo_pdf_url"] = None
    if memo and run.status == "completed":
        from app.services import memo_pdf

        try:
            if not memo_pdf.has_pdf(rid):
                path = memo_pdf.write_memo_pdf(rid, {**memo, "run_id": rid, "application_id": run.application_id,
                                                     "sections": {**(memo.get("sections") or {}),
                                                                  "approval_path": (memo.get("sections") or {}).get("approval_path")
                                                                  or view.get("approval_path")}})
                db.add(AuditEvent(run_id=rid, sequence=_next_seq(db, rid), step="MEMO_PDF_GENERATED", actor="backend",
                                  payload_json=dumps({"path": path.name, "bytes": path.stat().st_size,
                                                      "narrative_by": ((memo.get("sections") or {}).get("narrative") or {}).get("generated_by")})))
            view["memo_pdf_url"] = f"/underwriting/{rid}/memo.pdf"
        except Exception:  # PDF generation must never break run mirroring
            view["memo_pdf_url"] = None

    app_status = _APP_STATUS.get(run.status, run.decision or "decision_pending")
    if run.status == "completed":
        app_status = run.decision if run.decision in ("approved", "declined", "referred") else "decision_pending"
    # Only the application's newest run may drive its status: viewing an older run must not
    # roll the application (and the dashboard) back to that run's outcome.
    app_row = db.get(Application, run.application_id)
    current_latest = db.get(UnderwritingRun, app_row.latest_run_id) if app_row and app_row.latest_run_id else None
    is_latest = (current_latest is None or current_latest.id == rid
                 or str(run.created_at or "") >= str(current_latest.created_at or ""))
    if is_latest:
        application_service.set_status(db, run.application_id, app_status, latest_run_id=rid,
                                       latest_decision=run.decision or ("human_review" if run.status == "awaiting_human" else None))
    db.commit()


def _view_from_mirror(run: UnderwritingRun, stale: bool = True) -> dict[str, Any]:
    view = run.state or {"run_id": run.id, "application_id": run.application_id, "status": run.status,
                         "decision": run.decision, "confidence": run.confidence, "reasons": [],
                         "financials": None, "evidence": [], "nodes": []}
    view["stale"] = stale
    from app.services import memo_pdf

    view["memo_pdf_url"] = f"/underwriting/{run.id}/memo.pdf" if memo_pdf.has_pdf(run.id) else None
    return view


async def sync_run(db: Session, run_id: str) -> dict[str, Any]:
    """Fetch the run from the AI service, mirror it, and return the contract view."""
    run = db.get(UnderwritingRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    try:
        view = await ai_service.get_run(run_id)
    except ai_service.AIServiceError as exc:
        if exc.status_code == 404:
            raise HTTPException(status_code=404, detail="run not found on AI service")
        return _view_from_mirror(run)  # AI service offline -> serve last mirrored state
    _mirror(db, run, view)
    view["stale"] = False
    return view


async def get_run(db: Session, run_id: str) -> dict[str, Any]:
    return await sync_run(db, run_id)


async def resume_run(db: Session, run_id: str, payload: dict[str, Any], actor: str | None = None) -> dict[str, Any]:
    run = db.get(UnderwritingRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    body = dict(payload)
    body.setdefault("reviewer", actor or "reviewer")
    try:
        view = await ai_service.resume_run(run_id, body)
    except ai_service.AIServiceError as exc:
        _raise(exc)
    db.add(AuditEvent(run_id=run_id, sequence=_next_seq(db, run_id), step="HUMAN_REVIEW_SUBMITTED",
                      actor=body["reviewer"], payload_json=dumps({"reviews": body.get("reviews", []),
                                                                  "decision_override": body.get("decision_override")})))
    _mirror(db, run, view)
    view["stale"] = False
    return view


def _next_seq(db: Session, run_id: str) -> int:
    last = db.query(AuditEvent).filter(AuditEvent.run_id == run_id).order_by(AuditEvent.sequence.desc()).first()
    return (last.sequence + 1) if last else 0


async def get_trace(db: Session, run_id: str) -> dict[str, Any]:
    run = db.get(UnderwritingRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    try:
        trace = await ai_service.get_trace(run_id)
    except ai_service.AIServiceError as exc:
        if exc.status_code == 404:
            raise HTTPException(status_code=404, detail="run not found on AI service")
        rows = db.query(AuditEvent).filter(AuditEvent.run_id == run_id).order_by(AuditEvent.sequence).all()
        return {"run_id": run_id, "status": run.status, "nodes": (run.state or {}).get("nodes", []), "stale": True,
                "steps": [{"sequence": r.sequence, "agent": r.actor, "event_type": r.step, "timestamp": r.timestamp,
                           "payload": loads(r.payload_json)} for r in rows]}
    # mirror AI steps (namespaced sequences so backend-originated events never collide)
    existing = {(r.step, r.sequence) for r in db.query(AuditEvent).filter(AuditEvent.run_id == run_id).all()}
    for s in trace.get("steps") or []:
        seq = 1000 + int(s.get("sequence", 0))
        if (str(s.get("event_type")), seq) in existing:
            continue
        db.add(AuditEvent(run_id=run_id, sequence=seq, step=str(s.get("event_type")), actor=str(s.get("agent")),
                          timestamp=str(s.get("timestamp") or utcnow()), payload_json=dumps(s.get("payload") or {})))
    db.commit()
    backend_steps = [
        {"sequence": r.sequence, "agent": r.actor, "event_type": r.step, "timestamp": r.timestamp,
         "payload": loads(r.payload_json), "origin": "backend"}
        for r in db.query(AuditEvent).filter(AuditEvent.run_id == run_id, AuditEvent.sequence < 1000)
        .order_by(AuditEvent.sequence).all()
    ]
    trace["backend_steps"] = backend_steps
    trace["stale"] = False
    return trace


async def replay_run(db: Session, run_id: str) -> dict[str, Any]:
    run = db.get(UnderwritingRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    try:
        result = await ai_service.replay_run(run_id)
    except ai_service.AIServiceError as exc:
        _raise(exc)
    db.add(ReplaySnapshot(run_id=run_id, deterministic=1 if result.get("deterministic") else 0,
                          result_json=dumps(result)))
    db.add(AuditEvent(run_id=run_id, sequence=_next_seq(db, run_id), step="REPLAY_REQUESTED", actor="backend",
                      payload_json=dumps({"deterministic": result.get("deterministic")})))
    db.commit()
    return result


async def run_what_if(db: Session, run_id: str, scenario: dict[str, Any], actor: str | None = None) -> dict[str, Any]:
    run = db.get(UnderwritingRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    try:
        result = await ai_service.run_what_if(run_id, scenario)
    except ai_service.AIServiceError as exc:
        _raise(exc)
    db.add(WhatIfRun(id=result.get("what_if_id"), run_id=run_id, scenario_json=dumps(scenario),
                     result_json=dumps(result), requested_by=actor))
    db.add(AuditEvent(run_id=run_id, sequence=_next_seq(db, run_id), step="WHAT_IF_REQUESTED", actor=actor or "backend",
                      payload_json=dumps({"scenario": scenario,
                                          "decision": (result.get("scenario") or {}).get("decision", {}).get("decision")})))
    db.commit()
    return result


def list_what_ifs(db: Session, run_id: str) -> list[dict[str, Any]]:
    rows = db.query(WhatIfRun).filter(WhatIfRun.run_id == run_id).order_by(WhatIfRun.created_at).all()
    return [{"what_if_id": r.id, "run_id": r.run_id, "scenario": loads(r.scenario_json),
             "result": loads(r.result_json), "requested_by": r.requested_by, "created_at": r.created_at}
            for r in rows]


def list_runs(db: Session, limit: int = 100, status: str | None = None) -> list[dict[str, Any]]:
    q = db.query(UnderwritingRun)
    if status:
        q = q.filter(UnderwritingRun.status == status)
    return [r.summary() for r in q.order_by(UnderwritingRun.created_at.desc()).limit(limit).all()]


def latest_run_for_application(db: Session, application_id: str) -> UnderwritingRun | None:
    app = db.get(Application, application_id)
    if app and app.latest_run_id:
        run = db.get(UnderwritingRun, app.latest_run_id)
        if run:
            return run
    return (db.query(UnderwritingRun).filter(UnderwritingRun.application_id == application_id)
            .order_by(UnderwritingRun.created_at.desc()).first())
