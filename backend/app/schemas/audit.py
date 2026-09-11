"""Pydantic schemas for audit (Team A)."""

from typing import Any

from pydantic import BaseModel


class AuditEventOut(BaseModel):
    id: str
    run_id: str
    sequence: int
    step: str
    actor: str
    timestamp: str
    payload: dict[str, Any] = {}


class TraceOut(BaseModel):
    run_id: str
    steps: list[AuditEventOut] = []