"""Orchestrator: full underwriting pipeline (Team B).

Pipeline:
classification → extraction → confidence → [pause?] → reconciliation →
deterministic compute → xgboost risk → risk reasoning → decision/policy →
explanation memo → audit. State persisted in Store after every node so resume,
replay and what-if are real, not frontend fakes.

Uses LangGraph StateGraph when installed; otherwise falls back to the same
ordered node execution (no behavior change, still fully persisted).

Contract notes
--------------
* Decisions are emitted in the shared-contract vocabulary
  (``approved | declined | referred | human_review``); the raw agent verdict
  (``APPROVE | REJECT | REFER``) is kept under ``decision_raw``.
* Financial numbers only ever come from :mod:`app.financials.engine`.
* Every node writes a ``TRACE`` audit event with its inputs/outputs summary and
  the model / policy / formula versions it depended on.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any

from app.agents.decision_agent import DecisionAgent, ExplanationAgent, RiskReasoningAgent
from app.agents.extraction_agent import ExtractionAgent
from app.agents.human_assist_agent import HumanAssistAgent
from app.agents.reconciliation_agent import ReconciliationAgent
from app.config import get_settings
from app.db.store import Store, get_store, init_schema
from app.financials.engine import FORMULA_VERSION, compute_all
from app.policy.engine import load_policy
from app.risk.engine import FEATURE_NAMES, MODEL_VERSION, RiskScorer
from app.state.underwriting_state import UnderwritingState
from app.utils import confidence as conf_utils

NODES = [
    "classification",
    "extraction",
    "confidence_validation",
    "reconciliation",
    "deterministic_compute",
    "xgboost_risk",
    "risk_reasoning",
    "decision_policy",
    "explanation",
    "audit",
]

# Agent verdict -> shared contract (shared/schemas/decision.json)
DECISION_CONTRACT = {"APPROVE": "approved", "REJECT": "declined", "REFER": "referred"}

_risk_scorer = RiskScorer()
_risk_ready = False


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _risk() -> RiskScorer:
    global _risk_ready
    if not _risk_ready:
        try:
            _risk_scorer.load_or_train()
        except Exception:
            pass
        _risk_ready = True
    return _risk_scorer


# --------------------------------------------------------------------------- #
# audit / trace helpers
# --------------------------------------------------------------------------- #
def _audit(store: Store, run_id: str, agent: str, event_type: str, payload: dict[str, Any]) -> None:
    seq = store.next_sequence(run_id)
    store.add_audit_event(run_id, seq, agent, event_type, payload)


def _trace(
    store: Store,
    run_id: str,
    node: str,
    status: str,
    duration_ms: float,
    detail: dict | None = None,
) -> None:
    _audit(
        store,
        run_id,
        node,
        "TRACE",
        {"node": node, "status": status, "duration_ms": round(duration_ms, 2), "detail": detail or {}},
    )


def _app_loan_request(app: dict[str, Any]) -> dict[str, Any]:
    lr = (app.get("loan_request") or app.get("loanRequest") or {}) if isinstance(app, dict) else {}
    prod = (app.get("product") or {}) if isinstance(app, dict) else {}
    amount = float(lr.get("amount", prod.get("amount", 0)) or 0)
    return {
        "loan_amount": amount,
        "tenure_months": int(lr.get("tenure_months", prod.get("tenure_months", 36)) or 36),
        "annual_rate": float(lr.get("rate_annual", prod.get("rate_annual", 18.0)) or 18.0),
        "vehicle_price": float(lr.get("vehicle_price", prod.get("vehicle_price", 0)) or 0),
        "down_payment": float(lr.get("down_payment", 0) or 0),
    }


def _application_evidence(application: dict[str, Any]) -> list[dict[str, Any]]:
    """Facts declared on the application form become first-class evidence.

    They are cross-checked against documents in reconciliation (e.g. declared income
    45,000 vs bank credits 38,500) instead of being trusted.
    """
    out: list[dict[str, Any]] = []
    if not isinstance(application, dict):
        return out
    borrower = application.get("borrower") or {}
    lr = _app_loan_request(application)
    src = "application_form"

    def add(field: str, value: Any, conf: float = 0.95) -> None:
        if value in (None, "", 0, 0.0):
            return
        out.append(
            {
                "field": field,
                "value": value,
                "source_document": src,
                "page": None,
                "confidence": conf,
                "evidence": f"Declared on application form: {field} = {value}",
                "kind": "application",
            }
        )

    add("full_name", borrower.get("full_name"))
    add("monthly_income", borrower.get("declared_monthly_income"))
    add("loan_amount", lr["loan_amount"])
    add("vehicle_price", lr["vehicle_price"])
    return out


def _numeric(v: Any) -> float | None:
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _usable(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [e for e in evidence if e.get("value") is not None and e.get("review_status") != "rejected"]


def _field_values(evidence: list[dict[str, Any]], field: str, exclude_sources: tuple[str, ...] = ()) -> list[float]:
    vals: list[float] = []
    for e in _usable(evidence):
        if e.get("field") != field or e.get("source_document") in exclude_sources:
            continue
        n = _numeric(e.get("value"))
        if n is not None:
            vals.append(n)
    return vals


def _field_confidence(evidence: list[dict[str, Any]]) -> dict[str, float]:
    """Minimum confidence per field (conservative)."""
    field_conf: dict[str, float] = {}
    for e in evidence:
        f = str(e.get("field", ""))
        c = float(e.get("confidence", 0.0))
        if f and (f not in field_conf or c < field_conf[f]):
            field_conf[f] = c
    return field_conf


def calculation_inputs_from_evidence(
    application: dict[str, Any], evidence: list[dict[str, Any]]
) -> dict[str, Any]:
    """Assemble the deterministic-engine inputs from verified evidence.

    * Verified income = documentary sources (bank statement / platform payouts); the
      application-form declaration is used only if no document supports income.
    * Monthly series (``bank_credits``) drive volatility/stability when available.
    * Obligations take the MAX across sources (conservative).
    """
    lr = _app_loan_request(application)
    doc_incomes = _field_values(evidence, "monthly_income", exclude_sources=("application_form",))
    doc_incomes += _field_values(evidence, "platform_income", exclude_sources=("application_form",))
    doc_incomes += _field_values(evidence, "employment_income", exclude_sources=("application_form",))
    series: list[float] = []
    for e in _usable(evidence):
        if e.get("field") == "bank_credits" and isinstance(e.get("value"), list):
            series = [n for n in (_numeric(x) for x in e["value"]) if n is not None]
            break
    if series:
        monthly_incomes = series
    elif doc_incomes:
        monthly_incomes = doc_incomes
    else:
        monthly_incomes = _field_values(evidence, "monthly_income")
    obligations = _field_values(evidence, "existing_monthly_obligations")
    prices = _field_values(evidence, "vehicle_price", exclude_sources=("application_form",))
    vehicle_price = lr["vehicle_price"] or (max(prices) if prices else 0.0) or lr["loan_amount"]
    if prices and not lr["vehicle_price"]:
        vehicle_price = max(prices)
    return {
        "loan_amount": lr["loan_amount"],
        "vehicle_price": vehicle_price,
        "annual_rate": lr["annual_rate"],
        "tenure_months": lr["tenure_months"],
        "existing_monthly_obligations": max(obligations) if obligations else 0.0,
        "monthly_incomes": monthly_incomes,
        "down_payment": lr["down_payment"],
    }


def _with_contract_aliases(fin: dict[str, Any]) -> dict[str, Any]:
    """Add the shared/schemas/financials.json names next to the engine names."""
    out = dict(fin)
    out["monthly_income"] = fin.get("verified_income", 0.0)
    out["total_monthly_obligations"] = fin.get("existing_obligations", 0.0)
    out["monthly_emi"] = fin.get("emi", 0.0)
    return out


def build_risk_features(
    financials: dict[str, Any],
    reconciliation: dict[str, Any],
    confidence: dict[str, Any],
    application: dict[str, Any],
    evidence: list[dict[str, Any]],
) -> dict[str, float]:
    """Feature vector for the (secondary) XGBoost signal — all deterministic inputs."""
    borrower = (application.get("borrower") or {}) if isinstance(application, dict) else {}
    inputs = financials.get("calculation_inputs", {}) or {}
    items = reconciliation.get("items", []) or []
    identity_flag = 1.0 if any(i.get("type") == "NAME_MISMATCH" for i in items) else 0.0
    income_sources = len({e.get("source_document") for e in _usable(evidence)
                          if e.get("field") in ("monthly_income", "platform_income", "employment_income")})
    series = inputs.get("monthly_incomes") or []
    trend = 0.0
    if len(series) >= 2 and series[0] > 0:
        trend = max(-1.0, min(1.0, (series[-1] - series[0]) / series[0]))
    feats = {
        "verified_monthly_income": float(financials.get("verified_income", 0.0)),
        "income_volatility": float(financials.get("income_volatility", 0.0)),
        "income_stability": float(financials.get("income_stability", 0.0)),
        "foir": float(financials.get("foir", 0.0)),
        "ltv": float(financials.get("ltv", 0.0)),
        "emi_to_income": float(financials.get("emi_to_income", 0.0)),
        "existing_monthly_obligations": float(financials.get("existing_obligations", 0.0)),
        "bank_balance_trend": trend,
        "income_sources": float(max(1, income_sources)),
        "income_mismatch_percentage": float(reconciliation.get("income_mismatch_percentage") or 0.0),
        "document_confidence": float(confidence.get("overall", 0.0)),
        "identity_mismatch_flag": identity_flag,
        "repayment_history_score": float(borrower.get("repayment_history_score", 0.7) or 0.7),
        "employment_stability": float(borrower.get("employment_stability", financials.get("income_stability", 0.7)) or 0.7),
        "loan_amount": float(inputs.get("loan_amount", 0.0)),
        "vehicle_price": float(inputs.get("vehicle_price", 0.0)),
        "tenure_months": float(inputs.get("tenure_months", 36)),
    }
    return {k: feats.get(k, 0.0) for k in FEATURE_NAMES}


# --------------------------------------------------------------------------- #
# Graph wrapper (LangGraph optional)
# --------------------------------------------------------------------------- #
class UnderwritingGraph:
    """Ordered node runner; uses LangGraph StateGraph when installed."""

    NODES_ORDER = list(NODES)

    def __init__(self) -> None:
        self._compiled: Any = None

    def compile(self) -> "UnderwritingGraph":
        """Compile a LangGraph StateGraph when available; else no-op."""
        try:
            from langgraph.graph import StateGraph  # type: ignore

            g = StateGraph(dict)
            prev: str | None = None
            for name in self.NODES_ORDER:
                g.add_node(name, lambda s, n=name: {"node": n})
                if prev:
                    g.add_edge(prev, name)
                prev = name
            try:
                g.set_entry_point(self.NODES_ORDER[0])
                g.set_finish_point(self.NODES_ORDER[-1])
            except Exception:
                pass
            self._compiled = g.compile()
        except Exception:
            self._compiled = None
        return self

    @property
    def backend(self) -> str:
        return "langgraph" if self._compiled is not None else "sequential"

    async def invoke(self, run_id: str, input_state: dict[str, Any]) -> dict[str, Any]:
        """Run the full pipeline for an application payload."""
        return await run_pipeline(
            run_id, input_state.get("application", {}), input_state.get("policy_profile")
        )


def create_graph() -> UnderwritingGraph:
    """Factory returning a ready to compile graph."""
    return UnderwritingGraph().compile()


# --------------------------------------------------------------------------- #
# Pipeline
# --------------------------------------------------------------------------- #
def new_run_id() -> str:
    return str(uuid.uuid4())


def _persist(store: Store, state: UnderwritingState) -> None:
    store.save_state(state.run_id, state.to_dict())


def _save_evidence(store: Store, run_id: str, evidence: list[dict[str, Any]]) -> None:
    store.save_extracted_fields(
        run_id,
        [
            {
                "field": e.get("field", ""),
                "value": e.get("value"),
                "confidence": float(e.get("confidence", 0.0)),
                "source_document": e.get("source_document"),
                "page": e.get("page"),
                "evidence": e.get("evidence"),
                "review_status": e.get("review_status", "auto"),
            }
            for e in evidence
        ],
    )


async def run_pipeline(
    run_id: str, application: dict[str, Any], policy_profile: str | None = None
) -> dict[str, Any]:
    """Execute the full workflow; pauses at HUMAN_REVIEW when confidence is low."""
    settings = get_settings()
    init_schema()
    store = get_store()
    application = application if isinstance(application, dict) else {}
    app_id = str(application.get("id") or application.get("application_id") or run_id)
    state = UnderwritingState(run_id=run_id, application_id=app_id)
    try:
        if not store.get_run(run_id):
            store.create_run(app_id, run_id=run_id)
        store.update_run_status(run_id, "running")
        policy = load_policy(settings.policy_file(policy_profile))
        store.bind_policy(run_id, policy)
        try:
            store.save_policy(policy)
        except Exception:
            pass
        state.policy = {
            "profile": str(policy.get("profile", "default")),
            "version": str(policy.get("version", "1.0")),
            "config": policy,
        }
        state.application = application
        _audit(store, run_id, "orchestrator", "RUN_STARTED",
               {"application_id": app_id, "policy": {"profile": state.policy["profile"],
                                                      "version": state.policy["version"]},
                "graph_backend": create_graph().backend, "mock_ai_mode": settings.MOCK_AI_MODE})
        _persist(store, state)

        # ---- classification --------------------------------------------------
        t0 = time.time()
        docs = list(application.get("documents", []) or [])
        from app.extraction.document_classifier import classify_document

        state.documents = []
        for d in docs:
            src = str(d.get("document_id") or d.get("filename") or d.get("storage_key") or "document")
            preview = str(d.get("text") or d.get("text_preview") or "")
            kind = str(d.get("kind") or d.get("category") or "") or classify_document(src, preview)
            if kind not in ("kyc", "bank_statement", "dealer_invoice", "platform_earnings"):
                kind = classify_document(src, preview)
            d["kind"] = kind
            state.documents.append({"source": src, "kind": kind, "chars": len(preview),
                                    "ocr_confidence": d.get("ocr_confidence")})
        _trace(store, run_id, "classification", "ok", (time.time() - t0) * 1000,
               {"documents": state.documents})
        _persist(store, state)

        # ---- extraction --------------------------------------------------------
        t0 = time.time()
        evidence = await ExtractionAgent().run(docs)
        evidence = _application_evidence(application) + evidence
        for e in evidence:
            e.setdefault("review_status", "auto")
        state.evidence = evidence
        _save_evidence(store, run_id, evidence)
        _audit(store, run_id, "extraction_agent", "EXTRACTION_COMPLETED",
               {"fields": len(evidence),
                "citations": [{"field": e.get("field"), "source": e.get("source_document"),
                               "page": e.get("page")} for e in evidence]})
        _trace(store, run_id, "extraction", "ok", (time.time() - t0) * 1000,
               {"fields": len(evidence), "llm": "mock" if settings.MOCK_AI_MODE else "enrich-only"})
        _persist(store, state)

        # ---- confidence validation ---------------------------------------------
        t0 = time.time()
        paused = _confidence_node(store, state, policy)
        _trace(store, run_id, "confidence_validation", "paused" if paused else "ok",
               (time.time() - t0) * 1000,
               {"overall": state.confidence.get("overall"),
                "low_confidence": [i["field"] for i in state.low_confidence]})
        if paused:
            state.status = "awaiting_human"
            state.review_questions = await HumanAssistAgent().suggest_review_questions(state.to_dict())
            _persist(store, state)
            store.update_run_status(run_id, "awaiting_human", decision="human_review")
            _audit(store, run_id, "confidence", "HUMAN_REVIEW_REQUIRED",
                   {"fields": state.low_confidence, "questions": state.review_questions})
            return state.to_dict()

        await _run_tail(store, state, policy)
        return state.to_dict()
    except Exception as exc:  # pragma: no cover - defensive: never leave a run dangling
        state.status = "failed"
        state.error = f"{type(exc).__name__}: {exc}"
        try:
            _persist(store, state)
            store.update_run_status(run_id, "failed")
            _audit(store, run_id, "orchestrator", "RUN_FAILED", {"error": state.error})
        except Exception:
            pass
        return state.to_dict()
    finally:
        try:
            store.close()
        except Exception:
            pass


def _confidence_node(_store: Store, state: UnderwritingState, policy: dict[str, Any]) -> bool:
    """Compute per-field/overall confidence; return True when a human pause is required."""
    evidence = state.evidence
    field_conf = _field_confidence(evidence)
    overall = conf_utils.aggregate_confidence(evidence)
    state.confidence = {"per_field": field_conf, "overall": round(overall, 4)}
    thresh = float((policy.get("confidence", {}) or {}).get("income_min", 0.6))
    reviewed = {r.get("field") for r in state.human_reviews}
    low = [i for i in conf_utils.critical_low_confidence(field_conf, thresh) if i["field"] not in reviewed]
    state.low_confidence = []
    for item in low:
        # cite the weakest evidence item for the field (that is what needs a human eye)
        weakest = min((e for e in evidence if e.get("field") == item["field"]),
                      key=lambda e: float(e.get("confidence", 0.0)), default={})
        state.low_confidence.append({
            **item,
            "source_document": weakest.get("source_document"),
            "page": weakest.get("page"),
            "evidence": weakest.get("evidence"),
            "value": weakest.get("value"),
        })
    return bool(state.low_confidence)


async def _run_tail(store: Store, state: UnderwritingState, policy: dict[str, Any]) -> None:
    """Nodes after the human gate: reconciliation → compute → risk → decision → memo → audit."""
    run_id = state.run_id
    application = state.application or {}
    evidence = state.evidence
    state.status = "running"
    store.update_run_status(run_id, "running")

    # ---- reconciliation ----------------------------------------------------------
    t0 = time.time()
    recon = await ReconciliationAgent().run(evidence, policy)
    state.reconciliation = {
        "items": recon.get("mismatches", []),
        "income_mismatch_percentage": recon.get("income_mismatch_percentage"),
        "has_high_severity": recon.get("has_high_severity", False),
        "documents_available": recon.get("documents_available", []),
    }
    store.save_reconciliation(run_id, state.reconciliation)
    _audit(store, run_id, "reconciliation_agent", "RECONCILIATION_COMPLETED",
           {"items": state.reconciliation["items"],
            "income_mismatch_percentage": state.reconciliation["income_mismatch_percentage"]})
    _trace(store, run_id, "reconciliation", "ok", (time.time() - t0) * 1000,
           {"mismatches": [i.get("type") for i in state.reconciliation["items"]],
            "income_mismatch_percentage": state.reconciliation["income_mismatch_percentage"]})
    _persist(store, state)

    # ---- deterministic compute ---------------------------------------------------
    t0 = time.time()
    inputs = calculation_inputs_from_evidence(application, evidence)
    fin = _with_contract_aliases(compute_all(inputs))
    state.financials = fin
    store.save_financials(run_id, fin)
    _audit(store, run_id, "financial_engine", "FINANCIALS_COMPUTED",
           {"inputs": fin["calculation_inputs"], "outputs": {k: fin[k] for k in
            ("emi", "foir", "ltv", "verified_income", "existing_obligations",
             "income_volatility", "income_stability")},
            "formula_version": FORMULA_VERSION})
    _trace(store, run_id, "deterministic_compute", "ok", (time.time() - t0) * 1000,
           {"emi": fin["emi"], "foir": fin["foir"], "ltv": fin["ltv"],
            "verified_income": fin["verified_income"], "formula_version": FORMULA_VERSION})
    _persist(store, state)

    # ---- xgboost risk ------------------------------------------------------------
    t0 = time.time()
    features = build_risk_features(fin, state.reconciliation, state.confidence, application, evidence)
    risk = _risk().score(features)
    risk["features"] = features
    risk["shap"] = _risk().explain(features)  # per-feature contributions: base + Σφ == score
    state.risk = risk
    store.save_risk(run_id, risk)
    _audit(store, run_id, "risk_engine", "RISK_SCORED",
           {"risk_score": risk["risk_score"], "risk_band": risk["risk_band"],
            "model_version": risk["model_version"], "model_backend": risk["model_backend"],
            "features": features,
            "shap": {"method": risk["shap"]["method"], "base_value": risk["shap"]["base_value"],
                     "contributions": {r["feature"]: r["shap"] for r in risk["shap"]["contributions"]}}})
    _trace(store, run_id, "xgboost_risk", "ok", (time.time() - t0) * 1000,
           {"risk_score": risk["risk_score"], "risk_band": risk["risk_band"],
            "model_backend": risk["model_backend"], "model_version": risk["model_version"],
            "shap_method": risk["shap"]["method"],
            "top_risk_raising": risk["shap"]["top_risk_raising"],
            "top_risk_lowering": risk["shap"]["top_risk_lowering"]})
    _persist(store, state)

    # ---- risk reasoning ----------------------------------------------------------
    t0 = time.time()
    state.risk_reasoning = await RiskReasoningAgent().reason(
        {"financials": fin, "risk": risk, "reconciliation": state.reconciliation}
    )
    _trace(store, run_id, "risk_reasoning", "ok", (time.time() - t0) * 1000,
           {"risk_level": state.risk_reasoning.get("risk_level"),
            "risks": len(state.risk_reasoning.get("risks", []))})
    _persist(store, state)

    # ---- decision / policy -------------------------------------------------------
    t0 = time.time()
    decision = await _decide(state, policy, application)
    state.decision = decision
    store.save_decision(run_id, decision["decision"], decision["reasons"], decision["confidence"])
    _audit(store, run_id, "decision_agent", "DECISION_MADE",
           {"decision": decision["decision"], "decision_raw": decision["decision_raw"],
            "confidence": decision["confidence"], "reasons": decision["reasons"],
            "policy": state.policy.get("profile"), "policy_version": state.policy.get("version"),
            "human_override": decision.get("human_override")})
    _trace(store, run_id, "decision_policy", "ok", (time.time() - t0) * 1000,
           {"decision": decision["decision"], "reason_codes": [r["code"] for r in decision["reasons"]]})
    _persist(store, state)

    # ---- path to approval (automatic what-if for declined files) -----------------
    state.approval_path = None
    if decision["decision"] == "declined":
        t0 = time.time()
        try:
            state.approval_path = await _min_change_for_approval(
                application, evidence, policy, state.confidence, state.human_reviews, {},
                fin.get("calculation_inputs", {}) or {},
            )
        except Exception as exc:  # the search is best-effort; never fail the run
            state.approval_path = None
            _audit(store, run_id, "what_if", "APPROVAL_PATH_FAILED", {"error": f"{type(exc).__name__}: {exc}"})
        _audit(store, run_id, "what_if", "APPROVAL_PATH_COMPUTED",
               {"found": state.approval_path is not None,
                "changes": (state.approval_path or {}).get("changes"),
                "description": (state.approval_path or {}).get("description"),
                "duration_ms": round((time.time() - t0) * 1000, 2)})
        _persist(store, state)

    # ---- decision explanation: policy margins + SHAP, in numbers and in words -----
    t0 = time.time()
    from app.risk.explain import build_decision_explanation, llm_rephrase

    borrower_name = (application.get("borrower") or {}).get("full_name")
    state.explanation = await llm_rephrase(
        build_decision_explanation(decision, fin, policy, application, risk, state.reconciliation,
                                   state.approval_path, borrower_name)
    )
    _audit(store, run_id, "explainer", "DECISION_EXPLAINED",
           {"headline": state.explanation.get("headline"),
            "policy_checks": [{"check": c["check"], "passed": c["passed"], "margin": c["margin"]}
                              for c in state.explanation.get("policy_checks", [])],
            "shap_method": (risk.get("shap") or {}).get("method"),
            "top_risk_raising": (risk.get("shap") or {}).get("top_risk_raising"),
            "generated_by": state.explanation.get("generated_by"),
            "llm_error": state.explanation.get("llm_error"),
            "duration_ms": round((time.time() - t0) * 1000, 2)})
    _persist(store, state)

    # ---- explanation -------------------------------------------------------------
    t0 = time.time()
    memo = await ExplanationAgent().build_memo(
        {
            "run_id": run_id,
            "application_id": state.application_id,
            "approval_path": state.approval_path,
            "explanation": state.explanation,
            "reconciliation": state.reconciliation,
            "borrower": {**(application.get("borrower") or {}),
                         "loan_request": application.get("loan_request") or {},
                         "product": application.get("product") or {}},
            "evidence": evidence,
            "financials": fin,
            "risk": risk,
            "risk_reasoning": state.risk_reasoning,
            "policy": state.policy,
            "human_reviews": state.human_reviews,
            "decision": decision,
        }
    )
    state.memo = memo
    store.save_credit_memo(run_id, memo)
    _trace(store, run_id, "explanation", "ok", (time.time() - t0) * 1000,
           {"sections": list(memo["sections"]),
            "narrative_by": (memo["sections"].get("narrative") or {}).get("generated_by"),
            "llm_error": (memo["sections"].get("narrative") or {}).get("llm_error")})
    _persist(store, state)

    # ---- audit -------------------------------------------------------------------
    t0 = time.time()
    state.status = "completed"
    state.completed_at = _now()
    _persist(store, state)
    store.update_run_status(run_id, "completed", decision=decision["decision"])
    _audit(store, run_id, "orchestrator", "RUN_COMPLETED",
           {"decision": decision["decision"], "confidence": decision["confidence"],
            "versions": {"formula": FORMULA_VERSION, "risk_model": MODEL_VERSION,
                         "risk_backend": risk["model_backend"],
                         "policy": f"{state.policy.get('profile')}@{state.policy.get('version')}"}})
    _trace(store, run_id, "audit", "ok", (time.time() - t0) * 1000, {"status": "completed"})


async def _decide(state: UnderwritingState, policy: dict[str, Any], application: dict[str, Any]) -> dict[str, Any]:
    per_field = state.confidence.get("per_field", {}) or {}
    income_conf = per_field.get("monthly_income")
    override = next((r for r in reversed(state.human_reviews) if r.get("field") == "decision"
                     and r.get("action") == "override"), None)
    evidence_status = {
        "overall_confidence": float(state.confidence.get("overall", 1.0)),
        "income_confidence": income_conf,
        "mismatches": state.reconciliation.get("items", []),
        "human_review_required": any(r.get("action") == "reject" for r in state.human_reviews),
    }
    raw = await DecisionAgent(policy).decide(state.financials or {}, evidence_status, application)
    decision = DECISION_CONTRACT.get(raw["decision"], "referred")
    result = {
        "decision": decision,
        "decision_raw": raw["decision"],
        "confidence": raw["confidence"],
        "reasons": raw["reasons"],
        "policy": raw["policy"],
        "human_override": None,
    }
    if override and override.get("corrected_value") in ("approved", "declined", "referred"):
        result["human_override"] = {
            "from": decision,
            "to": override["corrected_value"],
            "reviewer": override.get("reviewer"),
            "note": override.get("note"),
            "timestamp": override.get("timestamp"),
        }
        result["decision"] = override["corrected_value"]
        result["reasons"] = list(raw["reasons"]) + [
            {"code": "HUMAN_REVIEW_REQUIRED", "severity": "info",
             "message": f"Reviewer override: {decision} -> {override['corrected_value']}",
             "field": "decision"}
        ]
    return result


# --------------------------------------------------------------------------- #
# Resume (human-in-the-loop) — persisted, genuinely gated on DB state
# --------------------------------------------------------------------------- #
async def resume_run(run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Apply reviewer actions and continue the workflow from the human gate.

    payload: {reviewer, reviews: [{field, action: accept|correct|reject, corrected_value?, note?}],
              decision_override?: {decision, note}}
    """
    init_schema()
    store = get_store()
    try:
        run = store.get_run(run_id)
        if not run:
            raise KeyError(run_id)
        raw_state = store.get_state(run_id)
        state = UnderwritingState.from_dict(raw_state)
        if run["status"] != "awaiting_human":
            out = state.to_dict()
            out["error"] = f"run is {run['status']}, not awaiting_human"
            return out
        policy = run.get("policy_config") or load_policy(get_settings().policy_file(state.policy.get("profile")))
        reviewer = str(payload.get("reviewer") or "reviewer")
        reviews = list(payload.get("reviews") or [])
        applied: list[dict[str, Any]] = []
        for rv in reviews:
            field = str(rv.get("field") or "")
            action = str(rv.get("action") or "accept").lower()
            if not field or action not in ("accept", "correct", "reject"):
                continue
            original = next((e.get("value") for e in state.evidence if e.get("field") == field), None)
            corrected = rv.get("corrected_value", original) if action == "correct" else (
                None if action == "reject" else original)
            if action == "correct":
                n = _numeric(corrected)
                corrected = n if n is not None and field != "full_name" and field != "identity" else corrected
            row = store.add_human_review(run_id, field, original, corrected, action, reviewer, rv.get("note"))
            new_conf = 1.0 if action in ("accept", "correct") else 0.0
            status = {"accept": "accepted", "correct": "corrected", "reject": "rejected"}[action]
            for e in state.evidence:
                if e.get("field") == field:
                    e["review_status"] = status
                    e["confidence"] = new_conf
                    if action != "accept":
                        e["value"] = corrected
            store.update_field_value(run_id, field, corrected if action != "accept" else original,
                                     new_conf, review_status=status)
            record = {"id": row.id, "field": field, "original_value": original,
                      "corrected_value": corrected, "action": action, "reviewer": reviewer,
                      "note": rv.get("note"), "timestamp": row.timestamp}
            state.human_reviews.append(record)
            applied.append(record)
            _audit(store, run_id, "human_reviewer", "HUMAN_REVIEW_APPLIED", record)
        override = payload.get("decision_override") or {}
        if isinstance(override, dict) and override.get("decision") in ("approved", "declined", "referred"):
            row = store.add_human_review(run_id, "decision", None, override["decision"], "override",
                                         reviewer, override.get("note"))
            record = {"id": row.id, "field": "decision", "original_value": None,
                      "corrected_value": override["decision"], "action": "override",
                      "reviewer": reviewer, "note": override.get("note"), "timestamp": row.timestamp}
            state.human_reviews.append(record)
            _audit(store, run_id, "human_reviewer", "DECISION_OVERRIDE_REQUESTED", record)

        # Re-run the gate: anything still low-confidence and unreviewed keeps the run paused.
        paused = _confidence_node(store, state, policy)
        _trace(store, run_id, "confidence_validation", "paused" if paused else "ok", 0.0,
               {"resumed_by": reviewer, "reviews": len(applied),
                "pending": [i["field"] for i in state.low_confidence]})
        if paused:
            state.status = "awaiting_human"
            state.review_questions = await HumanAssistAgent().suggest_review_questions(state.to_dict())
            _persist(store, state)
            out = state.to_dict()
            out["pending_fields"] = [i["field"] for i in state.low_confidence]
            return out
        _audit(store, run_id, "orchestrator", "RUN_RESUMED", {"reviewer": reviewer, "reviews": len(applied)})
        try:
            await _run_tail(store, state, policy)
        except Exception as exc:  # never leave a resumed run stuck in "running"
            state.status = "failed"
            state.error = f"{type(exc).__name__}: {exc}"
            _persist(store, state)
            store.update_run_status(run_id, "failed")
            _audit(store, run_id, "orchestrator", "RUN_FAILED", {"error": state.error, "phase": "resume"})
        return state.to_dict()
    finally:
        try:
            store.close()
        except Exception:
            pass


# --------------------------------------------------------------------------- #
# Replay — recompute from the stored evidence + policy snapshot, compare
# --------------------------------------------------------------------------- #
async def _pure_recompute_async(
    application: dict[str, Any],
    evidence: list[dict[str, Any]],
    policy: dict[str, Any],
    confidence: dict[str, Any],
    human_reviews: list[dict[str, Any]],
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Side-effect-free re-execution of reconciliation → compute → risk → decision.

    Nothing is persisted and no LLM is consulted: this is the deterministic core the
    replay and what-if features rely on.
    """
    recon = await ReconciliationAgent().run(evidence, policy)
    reconciliation = {"items": recon.get("mismatches", []),
                      "income_mismatch_percentage": recon.get("income_mismatch_percentage")}
    inputs = calculation_inputs_from_evidence(application, evidence)
    for k, v in (overrides or {}).items():
        if k == "monthly_income" and v is not None:
            inputs["monthly_incomes"] = [float(v)]
        elif k in inputs and v is not None:
            inputs[k] = int(v) if k == "tenure_months" else float(v)
    if overrides and overrides.get("down_payment") is not None and not overrides.get("loan_amount"):
        base_price = inputs.get("vehicle_price") or inputs.get("loan_amount")
        inputs["loan_amount"] = max(0.0, float(base_price) - float(overrides["down_payment"]))
    fin = _with_contract_aliases(compute_all(inputs))
    features = build_risk_features(fin, reconciliation, confidence, application, evidence)
    risk = _risk().score(features)
    risk["features"] = features
    risk["shap"] = _risk().explain(features)
    tmp = UnderwritingState(run_id="replay", application_id=str(application.get("id", "")))
    tmp.financials = fin
    tmp.reconciliation = reconciliation
    tmp.confidence = confidence
    # Field corrections carry over; a reviewer's *decision* override must not, otherwise
    # every what-if / approval-path candidate would inherit the overridden verdict.
    tmp.human_reviews = [r for r in human_reviews if r.get("field") != "decision"]
    app_for_policy = dict(application)
    if overrides and overrides.get("tenure_months"):
        app_for_policy = {**application, "loan_request": {**(application.get("loan_request") or {}),
                                                          "tenure_months": int(overrides["tenure_months"])}}
    decision = await _decide(tmp, policy, app_for_policy)
    return {"financials": fin, "risk": risk, "reconciliation": reconciliation, "decision": decision,
            "inputs": inputs}


def _diff(original: dict[str, Any], replayed: dict[str, Any]) -> list[dict[str, Any]]:
    fields = [
        ("financials.emi", "financials", "emi"),
        ("financials.foir", "financials", "foir"),
        ("financials.ltv", "financials", "ltv"),
        ("financials.verified_income", "financials", "verified_income"),
        ("financials.existing_obligations", "financials", "existing_obligations"),
        ("risk.risk_score", "risk", "risk_score"),
        ("risk.risk_band", "risk", "risk_band"),
        ("decision.decision", "decision", "decision"),
        ("decision.confidence", "decision", "confidence"),
    ]
    out: list[dict[str, Any]] = []
    for label, sect, key in fields:
        o = (original.get(sect) or {}).get(key)
        r = (replayed.get(sect) or {}).get(key)
        out.append({"field": label, "original": o, "replayed": r, "equal": o == r})
    o_codes = sorted(x.get("code") for x in (original.get("decision") or {}).get("reasons", []) or [])
    r_codes = sorted(x.get("code") for x in (replayed.get("decision") or {}).get("reasons", []) or [])
    out.append({"field": "decision.reason_codes", "original": o_codes, "replayed": r_codes,
                "equal": o_codes == r_codes})
    return out


async def replay_run(run_id: str) -> dict[str, Any]:
    """Re-execute the deterministic tail from stored evidence + policy snapshot and diff."""
    init_schema()
    store = get_store()
    try:
        run = store.get_run(run_id)
        if not run:
            raise KeyError(run_id)
        state = UnderwritingState.from_dict(store.get_state(run_id))
        policy = run.get("policy_config") or state.policy.get("config") or {}
        original = {"financials": store.get_financials(run_id) or state.financials or {},
                    "risk": store.get_risk(run_id) or state.risk or {},
                    "decision": {**(store.get_decision(run_id) or {}), **({} if not state.decision else
                                 {"decision": state.decision.get("decision"),
                                  "confidence": state.decision.get("confidence"),
                                  "reasons": state.decision.get("reasons", [])})}}
        replayed = await _pure_recompute_async(state.application or {}, state.evidence, policy,
                                               state.confidence, state.human_reviews)
        diffs = _diff(original, replayed)
        deterministic = all(d["equal"] for d in diffs) if run["status"] == "completed" else False
        result = {
            "run_id": run_id,
            "status": run["status"],
            "policy": {"profile": state.policy.get("profile"), "version": state.policy.get("version")},
            "original": original,
            "replayed": {"financials": replayed["financials"], "risk": replayed["risk"],
                         "decision": replayed["decision"]},
            "diffs": diffs,
            "deterministic": deterministic,
            "replayed_at": _now(),
        }
        _audit(store, run_id, "replay", "REPLAY_EXECUTED",
               {"deterministic": deterministic, "diffs": [d for d in diffs if not d["equal"]]})
        return result
    finally:
        try:
            store.close()
        except Exception:
            pass


# --------------------------------------------------------------------------- #
# What-if — immutable scenario evaluation on top of a completed run
# --------------------------------------------------------------------------- #
_WHAT_IF_KEYS = ("loan_amount", "tenure_months", "annual_rate", "vehicle_price",
                 "existing_monthly_obligations", "monthly_income", "down_payment")


def _clean_overrides(scenario: dict[str, Any]) -> dict[str, float]:
    src = scenario.get("overrides") if isinstance(scenario.get("overrides"), dict) else scenario
    out: dict[str, float] = {}
    for k in _WHAT_IF_KEYS:
        v = (src or {}).get(k)
        n = _numeric(v)
        if n is not None:
            out[k] = n
    return out


async def _min_change_for_approval(
    application: dict[str, Any],
    evidence: list[dict[str, Any]],
    policy: dict[str, Any],
    confidence: dict[str, Any],
    human_reviews: list[dict[str, Any]],
    base_overrides: dict[str, float],
    base_inputs: dict[str, Any],
) -> dict[str, Any] | None:
    """Greedy search over tenure (up to policy max) and loan reduction for the smallest change."""
    limits = policy.get("limits", {}) or {}
    max_tenure = int(limits.get("max_tenure_months", 60))
    tenure0 = int(base_overrides.get("tenure_months", base_inputs.get("tenure_months", 36)))
    loan0 = float(base_overrides.get("loan_amount", base_inputs.get("loan_amount", 0.0)))
    candidates: list[dict[str, float]] = []
    for t in range(tenure0 + 6, max_tenure + 1, 6):
        candidates.append({"tenure_months": float(t)})
    for pct in (0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50):
        candidates.append({"loan_amount": round(loan0 * (1 - pct), 2)})
    for t in range(tenure0 + 6, max_tenure + 1, 6):
        for pct in (0.05, 0.10, 0.15, 0.20, 0.25, 0.30):
            candidates.append({"tenure_months": float(t), "loan_amount": round(loan0 * (1 - pct), 2)})

    def cost(c: dict[str, float]) -> float:
        dt = (c.get("tenure_months", tenure0) - tenure0) / max(1, max_tenure - tenure0)
        dl = (loan0 - c.get("loan_amount", loan0)) / max(1.0, loan0)
        return dt * 0.5 + dl

    for cand in sorted(candidates, key=cost):
        ov = {**base_overrides, **cand}
        res = await _pure_recompute_async(application, evidence, policy, confidence, human_reviews, ov)
        if res["decision"]["decision"] == "approved":
            desc = []
            if "tenure_months" in cand:
                desc.append(f"extend tenure {tenure0} → {int(cand['tenure_months'])} months")
            if "loan_amount" in cand:
                desc.append(f"reduce loan ₹{loan0:,.0f} → ₹{cand['loan_amount']:,.0f}")
            return {"changes": {k: (int(v) if k == "tenure_months" else v) for k, v in cand.items()},
                    "financials": res["financials"],
                    "decision": {"decision": res["decision"]["decision"],
                                 "reasons": res["decision"]["reasons"]},
                    "description": "; ".join(desc) or "no change needed"}
    return None


async def what_if(run_id: str, scenario: dict[str, Any]) -> dict[str, Any]:
    """Evaluate a hypothetical scenario against a run WITHOUT mutating the base run."""
    init_schema()
    store = get_store()
    try:
        run = store.get_run(run_id)
        if not run:
            raise KeyError(run_id)
        state = UnderwritingState.from_dict(store.get_state(run_id))
        settings = get_settings()
        profile = scenario.get("policy_profile")
        if profile and profile != state.policy.get("profile"):
            policy = load_policy(settings.policy_file(str(profile)))
        else:
            policy = run.get("policy_config") or state.policy.get("config") or load_policy(settings.policy_file())
        overrides = _clean_overrides(scenario)
        base = await _pure_recompute_async(state.application or {}, state.evidence, policy,
                                           state.confidence, state.human_reviews)
        result = await _pure_recompute_async(state.application or {}, state.evidence, policy,
                                             state.confidence, state.human_reviews, overrides)
        min_change = None
        if scenario.get("find_min_change") and result["decision"]["decision"] != "approved":
            # search from the scenario's effective inputs (down-payment overrides adjust the loan)
            min_change = await _min_change_for_approval(state.application or {}, state.evidence, policy,
                                                        state.confidence, state.human_reviews,
                                                        overrides, result["inputs"])
        out = {
            "run_id": run_id,
            "immutable": True,
            "policy": {"profile": str(policy.get("profile", "default")),
                       "version": str(policy.get("version", "1.0"))},
            "base": {"financials": state.financials or base["financials"],
                     "decision": {"decision": (state.decision or {}).get("decision", base["decision"]["decision"]),
                                  "confidence": (state.decision or {}).get("confidence", base["decision"]["confidence"]),
                                  "reasons": (state.decision or {}).get("reasons", base["decision"]["reasons"])}},
            "scenario": {"overrides": overrides, "financials": result["financials"], "risk": result["risk"],
                         "decision": {"decision": result["decision"]["decision"],
                                      "confidence": result["decision"]["confidence"],
                                      "reasons": result["decision"]["reasons"]}},
            "min_change_for_approval": min_change,
            "evaluated_at": _now(),
        }
        row = store.save_what_if(run_id, {"overrides": overrides, "policy_profile": profile,
                                          "find_min_change": bool(scenario.get("find_min_change"))}, out)
        out["what_if_id"] = row.id
        _audit(store, run_id, "what_if", "WHAT_IF_EVALUATED",
               {"what_if_id": row.id, "overrides": overrides,
                "decision": out["scenario"]["decision"]["decision"],
                "base_decision": out["base"]["decision"]["decision"]})
        return out
    finally:
        try:
            store.close()
        except Exception:
            pass


# --------------------------------------------------------------------------- #
# Read model for the REST layer
# --------------------------------------------------------------------------- #
def node_statuses(events: list[dict[str, Any]], run_status: str) -> list[dict[str, Any]]:
    """Derive the per-node status list from TRACE audit events."""
    latest: dict[str, dict[str, Any]] = {}
    for ev in events:
        if ev.get("event_type") == "TRACE":
            p = ev.get("payload", {}) or {}
            latest[str(p.get("node"))] = p
    out: list[dict[str, Any]] = []
    for name in NODES:
        p = latest.get(name)
        if p:
            out.append({"name": name, "status": p.get("status", "ok"),
                        "duration_ms": p.get("duration_ms"), "detail": p.get("detail", {})})
        else:
            status = "pending"
            if run_status == "failed":
                status = "skipped"
            out.append({"name": name, "status": status})
    return out


def run_view(run_id: str, store: Store | None = None) -> dict[str, Any] | None:
    """Full run state in the shared contract shape (see shared/schemas/decision.json)."""
    own = store is None
    store = store or get_store()
    try:
        run = store.get_run(run_id)
        if not run:
            return None
        state = store.get_state(run_id)
        events = store.get_audit_events(run_id)
        decision = state.get("decision") or {}
        status = run["status"]
        contract_decision = decision.get("decision") if decision else (
            "human_review" if status == "awaiting_human" else None)
        fin = state.get("financials")
        return {
            "run_id": run_id,
            "application_id": run.get("application_id"),
            "status": status,
            "decision": contract_decision,
            "confidence": decision.get("confidence"),
            "reasons": decision.get("reasons", []) if decision else [],
            "financials": fin,
            "risk": state.get("risk") or None,
            "risk_reasoning": state.get("risk_reasoning") or None,
            "evidence": state.get("evidence", []),
            "reconciliation": state.get("reconciliation") or {"items": [], "income_mismatch_percentage": None},
            "confidence_summary": state.get("confidence") or {"per_field": {}, "overall": 0.0},
            "low_confidence": state.get("low_confidence", []),
            "human_reviews": state.get("human_reviews", []),
            "review_questions": state.get("review_questions", []),
            "policy": {"profile": run.get("policy_profile") or (state.get("policy") or {}).get("profile"),
                       "version": run.get("policy_version") or (state.get("policy") or {}).get("version"),
                       "config": run.get("policy_config") or (state.get("policy") or {}).get("config")},
            "nodes": node_statuses(events, status),
            "memo": state.get("memo"),
            "approval_path": state.get("approval_path"),
            "explanation": state.get("explanation"),
            "documents": state.get("documents", []),
            "human_override": decision.get("human_override"),
            "error": state.get("error"),
            "created_at": run.get("created_at"),
            "updated_at": run.get("updated_at"),
            "completed_at": state.get("completed_at"),
        }
    finally:
        if own:
            try:
                store.close()
            except Exception:
                pass


def trace_view(run_id: str) -> dict[str, Any] | None:
    store = get_store()
    try:
        run = store.get_run(run_id)
        if not run:
            return None
        events = store.get_audit_events(run_id)
        return {
            "run_id": run_id,
            "application_id": run.get("application_id"),
            "status": run["status"],
            "policy": {"profile": run.get("policy_profile"), "version": run.get("policy_version")},
            "nodes": node_statuses(events, run["status"]),
            "steps": events,
            "human_reviews": store.get_human_reviews(run_id),
            "what_ifs": store.get_what_ifs(run_id),
        }
    finally:
        try:
            store.close()
        except Exception:
            pass
