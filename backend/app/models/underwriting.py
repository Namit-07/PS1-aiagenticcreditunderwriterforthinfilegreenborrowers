"""Underwriting run ORM models (Team A).

The backend mirrors the AI-service run so dashboards, queues and memos can be served
from the application database even when the AI service is offline. The AI service
remains the source of truth for the workflow itself.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.models._base import loads, new_id, utcnow


class UnderwritingRun(Base):
    """A single underwriting run for an application (id == AI-service run_id)."""

    __tablename__ = "underwriting_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    application_id: Mapped[str] = mapped_column(String, ForeignKey("applications.id"), index=True)
    status: Mapped[str] = mapped_column(String, default="created", index=True)
    decision: Mapped[str | None] = mapped_column(String)
    confidence: Mapped[float | None] = mapped_column(Float)
    policy_profile: Mapped[str | None] = mapped_column(String)
    policy_version: Mapped[str | None] = mapped_column(String)
    state_json: Mapped[str | None] = mapped_column(Text)  # last mirrored AI-service view
    started_by: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[str] = mapped_column(String, default=utcnow)
    updated_at: Mapped[str] = mapped_column(String, default=utcnow, onupdate=utcnow)
    completed_at: Mapped[str | None] = mapped_column(String)

    @property
    def state(self) -> dict[str, Any]:
        return loads(self.state_json)

    def summary(self) -> dict[str, Any]:
        return {
            "run_id": self.id,
            "application_id": self.application_id,
            "status": self.status,
            "decision": self.decision,
            "confidence": self.confidence,
            "policy_profile": self.policy_profile,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
        }


class HumanReview(Base):
    __tablename__ = "human_reviews"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(String, ForeignKey("underwriting_runs.id"), index=True)
    field: Mapped[str] = mapped_column(String)
    original_json: Mapped[str | None] = mapped_column(Text)
    corrected_json: Mapped[str | None] = mapped_column(Text)
    action: Mapped[str] = mapped_column(String)
    reviewer: Mapped[str | None] = mapped_column(String)
    note: Mapped[str | None] = mapped_column(Text)
    timestamp: Mapped[str] = mapped_column(String, default=utcnow)


class WhatIfRun(Base):
    __tablename__ = "what_if_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(String, ForeignKey("underwriting_runs.id"), index=True)
    scenario_json: Mapped[str] = mapped_column(Text, default="{}")
    result_json: Mapped[str] = mapped_column(Text, default="{}")
    requested_by: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[str] = mapped_column(String, default=utcnow)


class CreditMemo(Base):
    __tablename__ = "credit_memos"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(String, ForeignKey("underwriting_runs.id"), index=True)
    application_id: Mapped[str] = mapped_column(String, index=True)
    memo_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[str] = mapped_column(String, default=utcnow)


class ReconciliationItem(Base):
    __tablename__ = "reconciliation_items"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(String, ForeignKey("underwriting_runs.id"), index=True)
    type: Mapped[str] = mapped_column(String)
    severity: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(Text)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")


class FinancialMetric(Base):
    __tablename__ = "financial_metrics"

    run_id: Mapped[str] = mapped_column(String, ForeignKey("underwriting_runs.id"), primary_key=True)
    monthly_income: Mapped[float | None] = mapped_column(Float)
    total_monthly_obligations: Mapped[float | None] = mapped_column(Float)
    monthly_emi: Mapped[float | None] = mapped_column(Float)
    foir: Mapped[float | None] = mapped_column(Float)
    ltv: Mapped[float | None] = mapped_column(Float)
    formula_version: Mapped[str | None] = mapped_column(String)
    metrics_json: Mapped[str] = mapped_column(Text, default="{}")


class RiskScore(Base):
    __tablename__ = "risk_scores"

    run_id: Mapped[str] = mapped_column(String, ForeignKey("underwriting_runs.id"), primary_key=True)
    risk_score: Mapped[float | None] = mapped_column(Float)
    risk_band: Mapped[str | None] = mapped_column(String)
    model_version: Mapped[str | None] = mapped_column(String)
    model_backend: Mapped[str | None] = mapped_column(String)
    features_json: Mapped[str] = mapped_column(Text, default="{}")


class ReplaySnapshot(Base):
    __tablename__ = "replay_snapshots"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(String, ForeignKey("underwriting_runs.id"), index=True)
    deterministic: Mapped[int] = mapped_column(Integer, default=1)
    result_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[str] = mapped_column(String, default=utcnow)
