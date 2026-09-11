"""Decision schema (Team B) — mirrors shared/schemas/decision.json."""

from typing import Any

from pydantic import BaseModel, Field

from app.schemas.financials import Financials


class Reason(BaseModel):
    code: str
    severity: str = Field(pattern=r"info|warning|blocker")
    message: str | None = None
    field: str | None = None


class Decision(BaseModel):
    run_id: str
    status: str = Field(pattern=r"running|awaiting_human|completed|failed")
    decision: str = Field(pattern=r"approved|declined|referred|human_review")
    confidence: float = Field(ge=0.0, le=1.0)
    reasons: list[Reason] = []
    financials: Financials | None = None
    evidence_summary: list[Any] = []
    human_review_required: bool = False
    approved_amount_limit: float | None = None
    created_at: str | None = None