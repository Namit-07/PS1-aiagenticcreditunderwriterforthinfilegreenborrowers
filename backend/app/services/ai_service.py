"""Client for the AI Service (Team B), with a mock mode for Team A development.

The main backend communicates with the AI service exclusively over HTTP (see the
shared API contract). The LLM / LangGraph agent logic lives in the AI service and is
NEVER implemented here.

``MOCK_AI_MODE=true`` returns canned, contract-shaped responses so the UI can be
developed without Team B running. Tests may set ``ASGI_APP`` to call an in-process
ASGI app instead of the network.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import httpx

from app.config import get_settings

settings = get_settings()

RISK_PROFILES = ("conservative", "default", "aggressive")
NODES = ["classification", "extraction", "confidence_validation", "reconciliation", "deterministic_compute",
         "xgboost_risk", "risk_reasoning", "decision_policy", "explanation", "audit"]

# Test hook: an ASGI app to call instead of AI_SERVICE_URL (httpx.ASGITransport).
ASGI_APP: Any | None = None


class AIServiceError(RuntimeError):
    """Raised when the AI service call fails."""

    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


def _client() -> httpx.AsyncClient:
    if ASGI_APP is not None:
        return httpx.AsyncClient(transport=httpx.ASGITransport(app=ASGI_APP), base_url="http://ai-service",
                                 timeout=settings.AI_SERVICE_TIMEOUT)
    return httpx.AsyncClient(base_url=settings.AI_SERVICE_URL.rstrip("/"), timeout=settings.AI_SERVICE_TIMEOUT)


async def _request(method: str, path: str, **kwargs: Any) -> Any:
    try:
        async with _client() as client:
            resp = await client.request(method, path, **kwargs)
    except httpx.HTTPError as exc:
        raise AIServiceError(f"AI service unreachable: {exc}", status_code=503) from exc
    if resp.status_code >= 400:
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        raise AIServiceError(f"AI service error {resp.status_code}: {detail}", status_code=resp.status_code)
    return resp.json()


# --------------------------------------------------------------------------- #
# Mock mode (contract-shaped, deterministic)
# --------------------------------------------------------------------------- #
_MOCK_RUNS: dict[str, dict[str, Any]] = {}


def _mock_view(run_id: str, application_id: str, status: str = "completed") -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    fin = {"emi": 3075.6, "foir": 0.1424, "ltv": 0.75, "existing_obligations": 2500.0, "verified_income": 39150.0,
           "income_stability": 0.96, "income_volatility": 0.04, "loan_to_income": 0.19, "emi_to_income": 0.0786,
           "down_payment": 30000.0, "calculation_inputs": {"loan_amount": 90000, "vehicle_price": 120000,
           "annual_rate": 14.0, "tenure_months": 36, "existing_monthly_obligations": 2500,
           "monthly_incomes": [38500, 41000, 36200, 39800, 37900, 40100]}, "formula_version": "v1",
           "monthly_income": 39150.0, "total_monthly_obligations": 2500.0, "monthly_emi": 3075.6}
    return {
        "run_id": run_id, "application_id": application_id, "status": status,
        "decision": "approved" if status == "completed" else None,
        "confidence": 0.88 if status == "completed" else None, "reasons": [],
        "financials": fin if status == "completed" else None,
        "risk": {"risk_score": 0.21, "risk_band": "LOW", "model_version": "xgb-v1", "model_backend": "mock"},
        "risk_reasoning": {"risk_level": "LOW", "strengths": ["FOIR 14% is comfortably serviceable"], "risks": [],
                           "uncertainties": [], "reasoning": ["mock"], "evidence_refs": []},
        "evidence": [], "reconciliation": {"items": [], "income_mismatch_percentage": 0.0},
        "confidence_summary": {"per_field": {}, "overall": 0.9}, "low_confidence": [], "human_reviews": [],
        "review_questions": [], "policy": {"profile": "default", "version": "1.0", "config": {}},
        "nodes": [{"name": n, "status": "ok", "duration_ms": 1.0} for n in NODES],
        "memo": None, "created_at": now, "updated_at": now, "_mock": True,
    }


# --------------------------------------------------------------------------- #
# REST contract
# --------------------------------------------------------------------------- #
async def submit_underwrite(application_data: dict[str, Any], policy_profile: str | None = None) -> dict[str, Any]:
    """POST /underwrite on the AI service (202 -> {run_id, status})."""
    if settings.MOCK_AI_MODE:
        run_id = str(uuid.uuid4())
        _MOCK_RUNS[run_id] = _mock_view(run_id, str(application_data.get("id", "")))
        return {"run_id": run_id, "application_id": application_data.get("id"), "status": "running", "_mock": True}
    payload = dict(application_data)
    if policy_profile:
        payload["policy_profile"] = policy_profile
    return await _request("POST", "/underwrite", json=payload)


async def get_run(run_id: str) -> dict[str, Any]:
    """GET /underwrite/{run_id} on the AI service."""
    if settings.MOCK_AI_MODE:
        if run_id not in _MOCK_RUNS:
            raise AIServiceError("run not found", status_code=404)
        return _MOCK_RUNS[run_id]
    return await _request("GET", f"/underwrite/{run_id}")


async def resume_run(run_id: str, resume_payload: dict[str, Any]) -> dict[str, Any]:
    """POST /underwrite/{run_id}/resume (human-in-the-loop input)."""
    if settings.MOCK_AI_MODE:
        view = await get_run(run_id)
        view["status"], view["decision"] = "completed", "approved"
        return view
    return await _request("POST", f"/underwrite/{run_id}/resume", json=resume_payload)


async def get_trace(run_id: str) -> dict[str, Any]:
    """GET /underwrite/{run_id}/trace on the AI service."""
    if settings.MOCK_AI_MODE:
        view = await get_run(run_id)
        return {"run_id": run_id, "status": view["status"], "nodes": view["nodes"], "steps": [], "_mock": True}
    return await _request("GET", f"/underwrite/{run_id}/trace")


async def replay_run(run_id: str) -> dict[str, Any]:
    """GET /underwrite/{run_id}/replay on the AI service."""
    if settings.MOCK_AI_MODE:
        view = await get_run(run_id)
        return {"run_id": run_id, "deterministic": True, "diffs": [], "original": {}, "replayed": {},
                "policy": view["policy"], "replayed_at": datetime.now(timezone.utc).isoformat(), "_mock": True}
    return await _request("GET", f"/underwrite/{run_id}/replay")


async def run_what_if(run_id: str, scenario: dict[str, Any]) -> dict[str, Any]:
    """POST /underwrite/{run_id}/what-if on the AI service."""
    if settings.MOCK_AI_MODE:
        view = await get_run(run_id)
        return {"run_id": run_id, "what_if_id": str(uuid.uuid4()), "immutable": True, "scenario": {
            "overrides": scenario.get("overrides", {}), "financials": view["financials"], "risk": view["risk"],
            "decision": {"decision": "approved", "confidence": 0.88, "reasons": []}},
            "base": {"financials": view["financials"], "decision": {"decision": "approved", "confidence": 0.88,
                                                                     "reasons": []}},
            "min_change_for_approval": None, "_mock": True}
    return await _request("POST", f"/underwrite/{run_id}/what-if", json=scenario)


async def list_runs(limit: int = 100, application_id: str | None = None) -> list[dict[str, Any]]:
    if settings.MOCK_AI_MODE:
        return [{"run_id": r, "application_id": v["application_id"], "status": v["status"],
                 "decision": v["decision"], "created_at": v["created_at"]} for r, v in _MOCK_RUNS.items()]
    params: dict[str, Any] = {"limit": limit}
    if application_id:
        params["application_id"] = application_id
    return await _request("GET", "/underwrite", params=params)


async def get_policies() -> dict[str, Any]:
    if settings.MOCK_AI_MODE:
        return {"default": {"version": "1.0", "limits": {"foir_max": 0.5, "ltv_max": 0.8, "min_age": 21}}}
    return await _request("GET", "/policies")


async def get_risk_metrics(threshold: float = 0.5, n: int = 800) -> dict[str, Any]:
    """Proxy to AI-service GET /risk/metrics (model evaluation scores + confusion matrix).

    Provides a stable canned payload in MOCK_AI_MODE so the dashboard works without
    the real AI service.
    """
    if settings.MOCK_AI_MODE:
        return {
            "metric": "binary classification of risky vs clean (score >= threshold)",
            "positive_class": "ELEVATED_RISK", "threshold": 0.5, "n_samples": 800,
            "prevalence": 0.33, "backend": "fallback", "model_version": "xgb-v1",
            "confusion_matrix": {"tn": 516, "fp": 18, "fn": 20, "tp": 246,
                                 "matrix": [[516, 18], [20, 246]]},
            "accuracy": 0.9525, "precision": 0.9318, "recall_sensitivity": 0.9248,
            "specificity": 0.9663, "npv": 0.9627, "fpr": 0.0337, "f1_score": 0.9283,
            "youden_index": 0.8911, "matthews_cc": 0.8928, "roc_auc": 0.9924,
            "roc_points": [{"threshold": 1.0, "tpr": 0.0, "fpr": 0.0},
                           {"threshold": 0.5, "tpr": 0.9248, "fpr": 0.0337},
                           {"threshold": 0.0, "tpr": 1.0, "fpr": 1.0}],
            "note": "Synthetic-only evaluation; not a production credit model.", "_mock": True,
        }
    return await _request("GET", "/risk/metrics", params={"threshold": threshold, "n": n})


async def health() -> dict[str, Any]:
    if settings.MOCK_AI_MODE:
        return {"status": "ok", "service": "ai-service", "mock": True}
    return await _request("GET", "/health")
