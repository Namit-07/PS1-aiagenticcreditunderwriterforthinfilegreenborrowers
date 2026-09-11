"""Dashboard KPIs (Team A) — served from the mirrored tables, no AI call needed."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Application, UnderwritingRun


def stats(db: Session) -> dict[str, Any]:
    total = db.query(func.count(Application.id)).scalar() or 0
    by_status = dict(db.query(Application.status, func.count(Application.id)).group_by(Application.status).all())
    approved = by_status.get("approved", 0)
    declined = by_status.get("declined", 0)
    referred = by_status.get("referred", 0)
    decided = approved + declined + referred
    runs = db.query(UnderwritingRun).order_by(UnderwritingRun.created_at.desc()).all()
    awaiting = sum(1 for r in runs if r.status == "awaiting_human")
    durations = []
    for r in runs:
        if r.completed_at and r.created_at:
            try:
                delta_ms = (datetime.fromisoformat(r.completed_at) - datetime.fromisoformat(r.created_at)).total_seconds() * 1000
            except (ValueError, TypeError):
                continue
            # The AI service can finish a fast run before this row's own created_at is
            # committed, so a tiny negative delta is possible; clamp rather than show it.
            durations.append(max(0.0, delta_ms))
    by_day: dict[str, dict[str, int]] = defaultdict(lambda: {"approved": 0, "declined": 0, "referred": 0})
    for r in runs:
        if r.decision in ("approved", "declined", "referred"):
            by_day[str(r.created_at)[:10]][r.decision] += 1
    return {
        "total_applications": total,
        "pending_review": by_status.get("awaiting_human", 0) + by_status.get("decision_pending", 0),
        "approved": approved,
        "declined": declined,
        "referred": referred,
        "approval_rate": round(approved / decided, 4) if decided else 0.0,
        "runs_total": len(runs),
        "runs_awaiting_human": awaiting,
        "avg_run_duration_ms": round(sum(durations) / len(durations), 1) if durations else None,
        "by_status": by_status,
        "decisions_by_day": [{"day": d, **c} for d, c in sorted(by_day.items())],
        "recent_runs": [r.summary() for r in runs[:10]],
    }
