"""Underwriting run state (Team B)."""

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

_LIST_KEYS = ("documents", "evidence", "human_reviews", "low_confidence", "trace", "review_questions")
_DICT_KEYS = ("confidence", "reconciliation", "risk", "risk_reasoning", "policy", "application")
_OPT_KEYS = ("financials", "decision", "memo", "approval_path", "explanation", "error", "completed_at")


@dataclass
class UnderwritingState:
    """Mutable state for one underwriting run (persisted as JSON after every node)."""

    run_id: str = field(default_factory=lambda: str(uuid4()))
    application_id: str | None = None
    status: str = "running"
    application: dict[str, Any] = field(default_factory=dict)
    documents: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    confidence: dict[str, Any] = field(default_factory=dict)
    reconciliation: dict[str, Any] = field(default_factory=dict)
    financials: dict[str, Any] | None = None
    risk: dict[str, Any] = field(default_factory=dict)
    risk_reasoning: dict[str, Any] = field(default_factory=dict)
    policy: dict[str, Any] = field(default_factory=dict)
    decision: dict[str, Any] | None = None
    memo: dict[str, Any] | None = None
    approval_path: dict[str, Any] | None = None
    explanation: dict[str, Any] | None = None
    human_reviews: list[dict[str, Any]] = field(default_factory=list)
    low_confidence: list[dict[str, Any]] = field(default_factory=list)
    review_questions: list[str] = field(default_factory=list)
    trace: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None
    completed_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "run_id": self.run_id,
            "application_id": self.application_id,
            "status": self.status,
        }
        for key in _LIST_KEYS + _DICT_KEYS + _OPT_KEYS:
            out[key] = getattr(self, key)
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UnderwritingState":
        obj = cls(
            run_id=str(data.get("run_id") or str(uuid4())),
            application_id=data.get("application_id"),
            status=str(data.get("status") or "running"),
        )
        for key in _LIST_KEYS:
            if isinstance(data.get(key), list):
                setattr(obj, key, data[key])
        for key in _DICT_KEYS:
            if isinstance(data.get(key), dict):
                setattr(obj, key, data[key])
        for key in _OPT_KEYS:
            if key in data:
                setattr(obj, key, data[key])
        return obj
