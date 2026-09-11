"""Application business logic (Team A)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import Application, Document

VALID_STATUSES = {"draft", "documents_pending", "underwriting", "awaiting_human", "decision_pending",
                  "approved", "declined", "referred", "cancelled"}


def create_application(db: Session, payload: dict[str, Any], created_by: str | None = None) -> dict[str, Any]:
    """Persist a new application (status starts at ``documents_pending``)."""
    app = Application.from_payload(payload, created_by=created_by)
    app.status = "documents_pending"
    db.add(app)
    db.commit()
    db.refresh(app)
    return app.to_dict()


def list_applications(db: Session, limit: int = 25, offset: int = 0, status: str | None = None) -> list[dict[str, Any]]:
    q = db.query(Application)
    if status:
        q = q.filter(Application.status == status)
    rows = q.order_by(Application.created_at.desc()).offset(offset).limit(limit).all()
    return [r.to_dict() for r in rows]


def get_application(db: Session, application_id: str) -> Application | None:
    return db.get(Application, application_id)


def get_application_dict(db: Session, application_id: str) -> dict[str, Any] | None:
    app = get_application(db, application_id)
    if not app:
        return None
    out = app.to_dict()
    out["documents_count"] = db.query(Document).filter(Document.application_id == application_id).count()
    return out


def set_status(db: Session, application_id: str, status: str, latest_run_id: str | None = None,
               latest_decision: str | None = None) -> None:
    app = get_application(db, application_id)
    if not app:
        return
    if status in VALID_STATUSES:
        app.status = status
    if latest_run_id is not None:
        app.latest_run_id = latest_run_id
    if latest_decision is not None:
        app.latest_decision = latest_decision
    db.commit()


def application_payload_for_ai(db: Session, application_id: str) -> dict[str, Any] | None:
    """Application + document texts in the AI-service ``POST /underwrite`` shape."""
    app = get_application(db, application_id)
    if not app:
        return None
    docs = db.query(Document).filter(Document.application_id == application_id).order_by(Document.uploaded_at).all()
    payload = app.to_dict()
    # Evidence citations use ``document_id`` as the source label, so send a human-readable
    # name (the file name) and only disambiguate with a short id when names collide.
    name_counts: dict[str, int] = {}
    for d in docs:
        name_counts[d.file_name] = name_counts.get(d.file_name, 0) + 1

    def _label(d: Document) -> str:
        return d.file_name if name_counts.get(d.file_name, 0) == 1 else f"{d.file_name} ({d.id[:8]})"

    payload["documents"] = [
        {
            "document_id": _label(d),
            "storage_document_id": d.id,
            "filename": d.file_name,
            "kind": d.category if d.category and d.category != "other" else None,
            "text": d.extracted_text or "",
            "ocr_confidence": float(d.ocr_confidence) if d.ocr_confidence else None,
        }
        for d in docs
    ]
    for d in payload["documents"]:
        if d["kind"] is None:
            d.pop("kind")
        if d["ocr_confidence"] is None:
            d.pop("ocr_confidence")
    return payload
