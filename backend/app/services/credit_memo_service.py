"""Credit memo assembly + PDF delivery (Team A).

The memo content comes from the AI service's explanation agent (facts vs calculated
vs AI reasoning vs policy vs human overrides, plus the narrative and the automatic
path-to-approval). PDFs are generated automatically when a run completes (see
``underwriting_service._mirror``) and cached on disk; the routes below serve the
cached file and only render on demand when it is missing.
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import CreditMemo, UnderwritingRun
from app.models._base import loads
from app.services import underwriting_service
from app.services.memo_pdf import memo_lines, memo_to_pdf, pdf_path, read_memo_pdf, render_pdf, write_memo_pdf

__all__ = ["get_memo_data", "build_credit_memo", "memo_pdf_for_run", "memo_lines", "memo_to_pdf", "render_pdf"]


def _decorate(memo: dict[str, Any], run: UnderwritingRun, view: dict[str, Any] | None) -> dict[str, Any]:
    memo.setdefault("run_id", run.id)
    memo.setdefault("application_id", run.application_id)
    if view is not None:
        memo["decision_summary"] = {"decision": view.get("decision"), "confidence": view.get("confidence"),
                                    "status": view.get("status")}
        if view.get("approval_path") and not (memo.get("sections") or {}).get("approval_path"):
            memo.setdefault("sections", {})["approval_path"] = view["approval_path"]
    memo["pdf_ready"] = pdf_path(run.id).is_file()
    memo["pdf_url"] = f"/underwriting/{run.id}/memo.pdf"
    return memo


async def get_memo_data(db: Session, application_id: str) -> dict[str, Any]:
    """Gather the memo for the application's latest run (syncing from the AI service)."""
    run = underwriting_service.latest_run_for_application(db, application_id)
    if not run:
        raise HTTPException(status_code=404, detail="no underwriting run for this application")
    view = await underwriting_service.sync_run(db, run.id)
    memo = view.get("memo")
    if not memo:
        row = db.query(CreditMemo).filter(CreditMemo.run_id == run.id).first()
        memo = loads(row.memo_json) if row else None
    if not memo:
        raise HTTPException(status_code=409, detail=f"memo not available yet (run status: {view.get('status')})")
    return _decorate(memo, run, view)


async def build_credit_memo(db: Session, application_id: str) -> bytes:
    """PDF for the application's latest run — cached file first, else render and cache."""
    run = underwriting_service.latest_run_for_application(db, application_id)
    if not run:
        raise HTTPException(status_code=404, detail="no underwriting run for this application")
    return await memo_pdf_for_run(db, run.id)


async def memo_pdf_for_run(db: Session, run_id: str) -> bytes:
    """Serve the auto-generated PDF for a run; render it on demand if it is missing."""
    cached = read_memo_pdf(run_id)
    if cached:
        return cached
    run = db.get(UnderwritingRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    view = await underwriting_service.sync_run(db, run_id)
    memo = view.get("memo")
    if not memo:
        row = db.query(CreditMemo).filter(CreditMemo.run_id == run_id).first()
        memo = loads(row.memo_json) if row else None
    if not memo:
        raise HTTPException(status_code=409, detail=f"memo not available yet (run status: {view.get('status')})")
    memo = _decorate(memo, run, view)
    write_memo_pdf(run_id, memo)
    return memo_to_pdf(memo)
