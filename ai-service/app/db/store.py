"""Store: repository over SQLAlchemy models for the AI-service engine (Team B)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.db import models as m

settings = get_settings()


def _j(value: Any) -> str:
    return json.dumps(value, default=str, sort_keys=True)


def _un(_title: str, js: str | None) -> dict[str, Any]:
    if not js:
        return {}
    try:
        val = json.loads(js)
        return val if isinstance(val, dict) else {"value": val}
    except Exception:
        return {}


def _un_list(js: str | None) -> list[Any]:
    if not js:
        return []
    try:
        val = json.loads(js)
        return val if isinstance(val, list) else []
    except Exception:
        return []


def _make_engine(url: str):
    if url.startswith("sqlite"):
        if ":memory:" not in url:
            db_path = url.replace("sqlite:///", "").split("?")[0]
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        return create_engine(url, connect_args={"check_same_thread": False})
    return create_engine(url, pool_pre_ping=True)


engine = _make_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


class Store:
    """Persistence facade for underwriting runs."""

    def __init__(self, session: Session | None = None) -> None:
        self._session = session
        self._own_session = session is None

    def _s(self) -> Session:
        if self._session is None:
            self._session = SessionLocal()
        return self._session

    def close(self) -> None:
        if self._own_session and self._session is not None:
            self._session.close()

    # ---- runs / state ----
    def create_run(
        self, application_id: str, status: str = "created", run_id: str | None = None
    ) -> m.UnderwritingRun:
        run = m.UnderwritingRun(application_id=application_id, status=status)
        if run_id:
            run.run_id = run_id
        self._s().add(run)
        self._s().commit()
        return run

    def update_run_status(self, run_id: str, status: str, decision: str | None = None) -> None:
        run = self._s().get(m.UnderwritingRun, run_id)
        if run:
            run.status = status
            if decision is not None:
                run.decision = decision
            self._s().commit()

    def bind_policy(self, run_id: str, policy: dict[str, Any]) -> None:
        meta = {"name": policy.get("profile", "default"), "version": policy.get("version", "1.0")}
        run = self._s().get(m.UnderwritingRun, run_id)
        if run:
            run.policy_profile = meta["name"]
            run.policy_version = meta["version"]
            run.policy_config = _j(policy)
            self._s().commit()

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        run = self._s().get(m.UnderwritingRun, run_id)
        if not run:
            return None
        return {
            "run_id": run.run_id,
            "application_id": run.application_id,
            "status": run.status,
            "policy_profile": run.policy_profile,
            "policy_version": run.policy_version,
            "decision": run.decision,
            "policy_config": _un(run.run_id, run.policy_config),
            "created_at": run.created_at,
            "updated_at": run.updated_at,
        }

    def save_state(self, run_id: str, state: dict[str, Any]) -> None:
        obj = self._s().get(m.WorkflowState, run_id)
        if obj:
            obj.state_json = _j(state)
        else:
            self._s().add(m.WorkflowState(run_id=run_id, state_json=_j(state)))
        self._s().commit()

    def get_state(self, run_id: str) -> dict[str, Any]:
        obj = self._s().get(m.WorkflowState, run_id)
        return _un(run_id, obj.state_json) if obj else {}

    # ---- extracted fields ----
    def save_extracted_fields(self, run_id: str, fields: list[dict[str, Any]]) -> None:
        self._s().query(m.ExtractedField).filter(m.ExtractedField.run_id == run_id).delete()
        for f in fields:
            self._s().add(
                m.ExtractedField(
                    run_id=run_id,
                    field=f.get("field", ""),
                    value_json=_j({"value": f.get("value")}),
                    confidence=float(f.get("confidence", 0.0)),
                    source_document=f.get("source_document"),
                    page=f.get("page"),
                    evidence=f.get("evidence"),
                    review_status=f.get("review_status", "auto"),
                )
            )
        self._s().commit()

    def get_extracted_fields(self, run_id: str) -> list[dict[str, Any]]:
        rows = (
            self._s()
            .query(m.ExtractedField)
            .filter(m.ExtractedField.run_id == run_id)
            .order_by(m.ExtractedField.id)
            .all()
        )
        out = []
        for r in rows:
            d = _un(r.run_id, r.value_json)
            out.append(
                {
                    "id": r.id,
                    "field": r.field,
                    "value": d.get("value"),
                    "confidence": r.confidence,
                    "source_document": r.source_document,
                    "page": r.page,
                    "evidence": r.evidence,
                    "review_status": r.review_status,
                }
            )
        return out

    def update_field_review_status(self, run_id: str, field: str, status: str) -> None:
        self._s().query(m.ExtractedField).filter(
            m.ExtractedField.run_id == run_id, m.ExtractedField.field == field
        ).update({m.ExtractedField.review_status: status})
        self._s().commit()

    # ---- human review ----
    def add_human_review(
        self,
        run_id: str,
        field: str,
        original_value: Any,
        corrected_value: Any,
        action: str,
        reviewer: str | None = None,
        note: str | None = None,
    ) -> m.HumanReview:
        obj = m.HumanReview(
            run_id=run_id,
            field=field,
            original_value_json=_j({"value": original_value}),
            corrected_value_json=_j({"value": corrected_value}),
            action=action,
            reviewer=reviewer,
            note=note,
        )
        self._s().add(obj)
        self._s().commit()
        return obj

    def get_human_reviews(self, run_id: str) -> list[dict[str, Any]]:
        rows = (
            self._s().query(m.HumanReview)
            .filter(m.HumanReview.run_id == run_id)
            .order_by(m.HumanReview.timestamp)
            .all()
        )
        out: list[dict[str, Any]] = []
        for r in rows:
            out.append(
                {
                    "id": r.id,
                    "field": r.field,
                    "original_value": _un(r.run_id, r.original_value_json).get("value"),
                    "corrected_value": _un(r.run_id, r.corrected_value_json).get("value"),
                    "action": r.action,
                    "reviewer": r.reviewer,
                    "note": r.note,
                    "timestamp": r.timestamp,
                }
            )
        return out

    def update_field_value(
        self,
        run_id: str,
        field: str,
        value: Any,
        confidence: float | None = None,
        review_status: str | None = None,
    ) -> None:
        rows = (
            self._s().query(m.ExtractedField)
            .filter(m.ExtractedField.run_id == run_id, m.ExtractedField.field == field)
            .all()
        )
        for r in rows:
            r.value_json = _j({"value": value})
            if confidence is not None:
                r.confidence = float(confidence)
            if review_status is not None:
                r.review_status = review_status
        self._s().commit()

    # ---- audit ----
    def add_audit_event(
        self, run_id: str, sequence: int, agent: str, event_type: str, payload: dict[str, Any]
    ) -> m.AuditEvent:
        obj = m.AuditEvent(
            run_id=run_id, sequence=sequence, agent=agent,
            event_type=event_type, payload_json=_j(payload),
        )
        self._s().add(obj)
        self._s().commit()
        return obj

    def get_audit_events(self, run_id: str) -> list[dict[str, Any]]:
        rows = (
            self._s().query(m.AuditEvent)
            .filter(m.AuditEvent.run_id == run_id)
            .order_by(m.AuditEvent.sequence)
            .all()
        )
        return [
            {
                "id": r.id,
                "sequence": r.sequence,
                "agent": r.agent,
                "event_type": r.event_type,
                "payload": _un(r.run_id, r.payload_json),
                "timestamp": r.timestamp,
            }
            for r in rows
        ]

    def next_sequence(self, run_id: str) -> int:
        seqs = [e["sequence"] for e in self.get_audit_events(run_id)]
        return (max(seqs) + 1) if seqs else 0

    # ---- financials / risk / decision / reconciliation ----
    def save_financials(self, run_id: str, metrics: dict[str, Any]) -> None:
        obj = self._s().get(m.FinancialMetric, run_id)
        if obj:
            obj.metrics_json = _j(metrics)
        else:
            self._s().add(m.FinancialMetric(run_id=run_id, metrics_json=_j(metrics)))
        self._s().commit()

    def get_financials(self, run_id: str) -> dict[str, Any]:
        obj = self._s().get(m.FinancialMetric, run_id)
        return _un(run_id, obj.metrics_json) if obj else {}

    def save_risk(self, run_id: str, risk: dict[str, Any]) -> None:
        obj = self._s().get(m.RiskScore, run_id)
        if obj:
            obj.risk_score = float(risk["risk_score"])
            obj.risk_band = risk.get("risk_band")
            obj.model_version = risk.get("model_version")
            obj.model_backend = risk.get("model_backend")
            obj.features_json = _j(risk.get("features", {}))
        else:
            self._s().add(
                m.RiskScore(
                    run_id=run_id,
                    risk_score=float(risk["risk_score"]),
                    risk_band=risk.get("risk_band"),
                    model_version=risk.get("model_version"),
                    model_backend=risk.get("model_backend"),
                    features_json=_j(risk.get("features", {})),
                )
            )
        self._s().commit()

    def get_risk(self, run_id: str) -> dict[str, Any]:
        obj = self._s().get(m.RiskScore, run_id)
        if not obj:
            return {}
        return {
            "risk_score": obj.risk_score,
            "risk_band": obj.risk_band,
            "model_version": obj.model_version,
            "model_backend": obj.model_backend,
            "features": _un(run_id, obj.features_json),
        }

    def save_decision(self, run_id: str, decision: str, reasons: list[dict[str, Any]], confidence: float) -> None:
        obj = self._s().get(m.DecisionRow, run_id)
        if obj:
            obj.decision = decision
            obj.reasons_json = _j(reasons)
            obj.confidence = float(confidence)
        else:
            self._s().add(
                m.DecisionRow(run_id=run_id, decision=decision, reasons_json=_j(reasons), confidence=float(confidence))
            )
        self._s().commit()

    def get_decision(self, run_id: str) -> dict[str, Any]:
        obj = self._s().get(m.DecisionRow, run_id)
        if not obj:
            return {}
        return {
            "decision": obj.decision,
            "reasons": _un_list(obj.reasons_json),
            "confidence": obj.confidence,
        }

    def save_reconciliation(self, run_id: str, data: dict[str, Any]) -> None:
        obj = self._s().get(m.ReconciliationRow, run_id)
        if obj:
            obj.items_json = _j(data.get("items", []))
            obj.income_mismatch_percentage = data.get("income_mismatch_percentage")
        else:
            self._s().add(
                m.ReconciliationRow(
                    run_id=run_id,
                    items_json=_j(data.get("items", [])),
                    income_mismatch_percentage=data.get("income_mismatch_percentage"),
                )
            )
        self._s().commit()

    def get_reconciliation(self, run_id: str) -> dict[str, Any]:
        obj = self._s().get(m.ReconciliationRow, run_id)
        if not obj:
            return {"items": [], "income_mismatch_percentage": None}
        return {
            "items": _un_list(obj.items_json),
            "income_mismatch_percentage": obj.income_mismatch_percentage,
        }

    # ---- what-if / replay ----
    def save_what_if(self, base_run_id: str, scenario: dict[str, Any], result: dict[str, Any]) -> m.WhatIfRun:
        obj = m.WhatIfRun(
            base_run_id=base_run_id, scenario_json=_j(scenario), result_json=_j(result)
        )
        self._s().add(obj)
        self._s().commit()
        return obj

    def get_what_ifs(self, run_id: str) -> list[dict[str, Any]]:
        rows = self._s().query(m.WhatIfRun).filter(m.WhatIfRun.base_run_id == run_id).all()
        return [
            {
                "id": r.id,
                "scenario": _un(run_id, r.scenario_json),
                "result": _un(run_id, r.result_json),
                "created_at": r.created_at,
            }
            for r in rows
        ]

    # ---- policy / credit memo ----
    def save_policy(self, policy: dict[str, Any]) -> m.PolicyVersion:
        meta = {"name": policy.get("profile", "default"), "version": policy.get("version", "1.0")}
        obj = m.PolicyVersion(name=meta["name"], version=meta["version"], config_json=_j(policy))
        self._s().add(obj)
        self._s().commit()
        return obj

    def get_policies(self) -> list[dict[str, Any]]:
        rows = self._s().query(m.PolicyVersion).order_by(m.PolicyVersion.created_at).all()
        out: list[dict[str, Any]] = []
        for r in rows:
            out.append(
                {
                    "name": r.name,
                    "version": r.version,
                    "config": _un(r.id or "", r.config_json),
                    "created_at": r.created_at,
                }
            )
        return out

    def save_credit_memo(self, run_id: str, memo: dict[str, Any]) -> None:
        obj = self._s().get(m.CreditMemo, run_id)
        if obj:
            obj.memo_json = _j(memo)
        else:
            self._s().add(m.CreditMemo(run_id=run_id, memo_json=_j(memo)))
        self._s().commit()

    def get_credit_memo(self, run_id: str) -> dict[str, Any]:
        obj = self._s().get(m.CreditMemo, run_id)
        return _un(run_id, obj.memo_json) if obj else {}

    # ---- listing ----
    def list_runs(self, limit: int = 100, application_id: str | None = None) -> list[dict[str, Any]]:
        q = self._s().query(m.UnderwritingRun)
        if application_id:
            q = q.filter(m.UnderwritingRun.application_id == application_id)
        rows = q.order_by(m.UnderwritingRun.created_at.desc()).limit(limit).all()
        return [
            {
                "run_id": r.run_id,
                "application_id": r.application_id,
                "status": r.status,
                "decision": r.decision,
                "created_at": r.created_at,
            }
            for r in rows
        ]


def init_schema() -> None:
    """Create all tables (idempotent). Use Alembic for real migrations in prod."""
    m.Base.metadata.create_all(bind=engine)


def get_store() -> Store:
    return Store()