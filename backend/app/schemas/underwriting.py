"""Pydantic schemas for underwriting runs (Team A)."""

from typing import Any, Literal

from pydantic import BaseModel


class UnderwriteStartRequest(BaseModel):
    policy_profile: str | None = None


class UnderwritingRunOut(BaseModel):
    run_id: str
    application_id: str | None = None
    status: str
    decision: str | None = None
    confidence: float | None = None
    payload: dict[str, Any] = {}


class FieldReview(BaseModel):
    field: str
    action: Literal["accept", "correct", "reject"]
    corrected_value: Any | None = None
    note: str | None = None


class DecisionOverride(BaseModel):
    decision: Literal["approved", "declined", "referred"]
    note: str | None = None


class ResumePayload(BaseModel):
    reviewer: str | None = None
    reviews: list[FieldReview] = []
    decision_override: DecisionOverride | None = None


class WhatIfRequest(BaseModel):
    overrides: dict[str, float | int | None] = {}
    policy_profile: str | None = None
    find_min_change: bool = False
