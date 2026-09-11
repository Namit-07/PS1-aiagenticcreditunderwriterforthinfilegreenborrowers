"""Persistence for the AI-service engine (Team B).

SQLAlchemy models backing the underwriting run state, extracted fields, human reviews,
audit events, financial metrics, risk scores, decisions, reconciliations, what-if runs,
policy versions and credit memos.

Values are stored as JSON text so the same schema works on SQLite and Postgres.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_id() -> str:
    import uuid

    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class UnderwritingRun(Base):
    __tablename__ = "ai_underwriting_runs"

    run_id: Mapped[str] = mapped_column(String, primary_key=True, default=default_id)
    application_id: Mapped[str | None] = mapped_column(String, index=True)
    status: Mapped[str] = mapped_column(String, default="created")
    policy_profile: Mapped[str | None] = mapped_column(String)
    policy_version: Mapped[str | None] = mapped_column(String)
    policy_config: Mapped[str | None] = mapped_column(Text)
    decision: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[str] = mapped_column(String, default=_utcnow)
    updated_at: Mapped[str] = mapped_column(String, default=_utcnow, onupdate=_utcnow)


class WorkflowState(Base):
    __tablename__ = "ai_workflow_state"

    run_id: Mapped[str] = mapped_column(String, ForeignKey("ai_underwriting_runs.run_id"), primary_key=True)
    state_json: Mapped[str] = mapped_column(Text)


class ExtractedField(Base):
    __tablename__ = "ai_extracted_fields"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=default_id)
    run_id: Mapped[str] = mapped_column(String, ForeignKey("ai_underwriting_runs.run_id"), index=True)
    field: Mapped[str] = mapped_column(String)
    value_json: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    source_document: Mapped[str | None] = mapped_column(String)
    page: Mapped[int | None] = mapped_column(Integer)
    evidence: Mapped[str | None] = mapped_column(Text)
    review_status: Mapped[str] = mapped_column(String, default="auto")


class HumanReview(Base):
    __tablename__ = "ai_human_reviews"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=default_id)
    run_id: Mapped[str] = mapped_column(String, ForeignKey("ai_underwriting_runs.run_id"), index=True)
    field: Mapped[str] = mapped_column(String)
    original_value_json: Mapped[str | None] = mapped_column(Text)
    corrected_value_json: Mapped[str | None] = mapped_column(Text)
    action: Mapped[str] = mapped_column(String)
    reviewer: Mapped[str | None] = mapped_column(String)
    note: Mapped[str | None] = mapped_column(Text)
    timestamp: Mapped[str] = mapped_column(String, default=_utcnow)


class AuditEvent(Base):
    __tablename__ = "ai_audit_events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=default_id)
    run_id: Mapped[str] = mapped_column(String, ForeignKey("ai_underwriting_runs.run_id"), index=True)
    sequence: Mapped[int] = mapped_column(Integer, default=0)
    agent: Mapped[str] = mapped_column(String)
    event_type: Mapped[str] = mapped_column(String)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    timestamp: Mapped[str] = mapped_column(String, default=_utcnow)


class FinancialMetric(Base):
    __tablename__ = "ai_financial_metrics"

    run_id: Mapped[str] = mapped_column(String, ForeignKey("ai_underwriting_runs.run_id"), primary_key=True)
    metrics_json: Mapped[str] = mapped_column(Text)


class RiskScore(Base):
    __tablename__ = "ai_risk_scores"

    run_id: Mapped[str] = mapped_column(String, ForeignKey("ai_underwriting_runs.run_id"), primary_key=True)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    risk_band: Mapped[str | None] = mapped_column(String)
    model_version: Mapped[str | None] = mapped_column(String)
    model_backend: Mapped[str | None] = mapped_column(String)
    features_json: Mapped[str | None] = mapped_column(Text)


class DecisionRow(Base):
    __tablename__ = "ai_decisions"

    run_id: Mapped[str] = mapped_column(String, ForeignKey("ai_underwriting_runs.run_id"), primary_key=True)
    decision: Mapped[str] = mapped_column(String)
    reasons_json: Mapped[str] = mapped_column(Text, default="[]")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)


class ReconciliationRow(Base):
    __tablename__ = "ai_reconciliations"

    run_id: Mapped[str] = mapped_column(String, ForeignKey("ai_underwriting_runs.run_id"), primary_key=True)
    items_json: Mapped[str] = mapped_column(Text, default="[]")
    income_mismatch_percentage: Mapped[float | None] = mapped_column(Float)


class WhatIfRun(Base):
    __tablename__ = "ai_what_if_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=default_id)
    base_run_id: Mapped[str] = mapped_column(String, ForeignKey("ai_underwriting_runs.run_id"), index=True)
    scenario_json: Mapped[str] = mapped_column(Text)
    result_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String, default=_utcnow)


class PolicyVersion(Base):
    __tablename__ = "ai_policy_versions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=default_id)
    name: Mapped[str] = mapped_column(String, index=True)
    version: Mapped[str] = mapped_column(String)
    config_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String, default=_utcnow)


class CreditMemo(Base):
    __tablename__ = "ai_credit_memos"

    run_id: Mapped[str] = mapped_column(String, ForeignKey("ai_underwriting_runs.run_id"), primary_key=True)
    memo_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String, default=_utcnow)