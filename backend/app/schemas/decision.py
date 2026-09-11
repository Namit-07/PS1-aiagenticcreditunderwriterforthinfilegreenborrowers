"""Pydantic schemas for decisions (Team A)."""

from typing import Any, Literal

from pydantic import BaseModel


class DecisionOut(BaseModel):
    run_id: str
    decision: str
    confidence: float | None = None
    reasons: list[Any] = []


class FinalizeDecisionRequest(BaseModel):
    decision: Literal["approved", "declined", "referred"]
    notes: str | None = None
    reviewer: str | None = None
