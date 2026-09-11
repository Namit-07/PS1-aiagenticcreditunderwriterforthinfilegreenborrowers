"""FastAPI entrypoint for the AI Service (Team B).

Exposes the underwriting REST contract consumed by the main backend (Team A):

    POST /underwrite                  -> 202 {run_id, status}
    GET  /underwrite/{run_id}         -> run state (shared decision contract)
    POST /underwrite/{run_id}/resume  -> apply human review, continue workflow
    GET  /underwrite/{run_id}/trace   -> audit trail + node statuses
    GET  /underwrite/{run_id}/replay  -> deterministic replay + diff
    POST /underwrite/{run_id}/what-if -> immutable scenario evaluation
    GET  /underwrite                  -> list runs (dashboard / review queue)

All state lives in the AI-service store (SQLite by default, Postgres via DATABASE_URL),
so a pause at HUMAN REVIEW survives restarts and is resumed from persisted state.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import APIRouter, BackgroundTasks, FastAPI, HTTPException, Query

from app.config import get_settings
from app.db.store import get_store, init_schema
from app.workflows import underwriting_graph as wf

settings = get_settings()


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    init_schema()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version="0.2.0",
    description="AI underwriting workflow service (document extraction, reconciliation, decision).",
    lifespan=_lifespan,
)

router = APIRouter(prefix="/underwrite", tags=["underwrite"])


def _application(payload: dict[str, Any]) -> dict[str, Any]:
    app_payload = payload.get("application") if isinstance(payload.get("application"), dict) else payload
    if not isinstance(app_payload, dict):
        raise HTTPException(status_code=422, detail="application payload must be an object")
    return app_payload


@router.post("", status_code=202)
async def start_run(payload: dict[str, Any], background: BackgroundTasks) -> dict[str, Any]:
    """Start an underwriting run for an application.

    Body: the application (shared/schemas/application.json) plus ``documents`` —
    ``[{document_id|filename, kind?, text?|pages?, ocr_confidence?}]`` — and optional
    ``policy_profile`` / ``sync``. Returns 202 immediately; poll ``GET /underwrite/{run_id}``.
    With ``sync: true`` the pipeline runs inline and the final state is returned.
    """
    application = _application(payload)
    policy_profile = payload.get("policy_profile") or application.get("policy_profile")
    run_id = wf.new_run_id()
    app_id = str(application.get("id") or application.get("application_id") or run_id)
    init_schema()
    store = get_store()
    try:
        store.create_run(app_id, status="created", run_id=run_id)
    finally:
        store.close()
    if payload.get("sync") or application.get("sync"):
        await wf.run_pipeline(run_id, application, policy_profile)
        return wf.run_view(run_id) or {"run_id": run_id, "status": "failed"}
    background.add_task(wf.run_pipeline, run_id, application, policy_profile)
    return {"run_id": run_id, "application_id": app_id, "status": "running",
            "policy_profile": policy_profile or settings.POLICY_PROFILE}


@router.get("")
async def list_runs(limit: int = Query(100, ge=1, le=500), application_id: str | None = None) -> list[dict[str, Any]]:
    """List runs (newest first) — feeds dashboards and the human-review queue."""
    store = get_store()
    try:
        return store.list_runs(limit=limit, application_id=application_id)
    finally:
        store.close()


@router.get("/{run_id}")
async def get_run(run_id: str) -> dict[str, Any]:
    """Return run state in the shared decision contract shape."""
    view = wf.run_view(run_id)
    if not view:
        raise HTTPException(status_code=404, detail="run not found")
    return view


@router.post("/{run_id}/resume")
async def resume_run(run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Resume a run with reviewer input (human-in-the-loop)."""
    try:
        result = await wf.resume_run(run_id, payload or {})
    except KeyError:
        raise HTTPException(status_code=404, detail="run not found")
    view = wf.run_view(run_id) or {}
    if result.get("pending_fields"):
        view["pending_fields"] = result["pending_fields"]
    if result.get("error"):
        view["error"] = result["error"]
    return view


@router.get("/{run_id}/trace")
async def get_trace(run_id: str) -> dict[str, Any]:
    """Return the decision trace (ordered audit events + node statuses)."""
    view = wf.trace_view(run_id)
    if not view:
        raise HTTPException(status_code=404, detail="run not found")
    return view


@router.get("/{run_id}/replay")
async def replay_run(run_id: str) -> dict[str, Any]:
    """Deterministically re-execute the run from stored evidence and diff the result."""
    try:
        return await wf.replay_run(run_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="run not found")


@router.post("/{run_id}/what-if")
async def run_what_if(run_id: str, scenario: dict[str, Any]) -> dict[str, Any]:
    """Evaluate a hypothetical scenario; the base run is never mutated."""
    try:
        return await wf.what_if(run_id, scenario or {})
    except KeyError:
        raise HTTPException(status_code=404, detail="run not found")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=422, detail=f"unknown policy profile: {exc}")


app.include_router(router)


@app.get("/", tags=["system"])
def root() -> dict[str, Any]:
    """Human-friendly landing so the deployed service base URL isn't a bare 404."""
    return {
        "service": settings.APP_NAME,
        "ok": True,
        "docs": "/docs",
        "health": "/health",
        "policies": "/policies",
        "risk_metrics": "/risk/metrics",
        "mock_ai_mode": settings.MOCK_AI_MODE,
        "note": "This is the AI-service API. Open the Next.js frontend for the dashboard UI.",
    }


@app.get("/health", tags=["system"])
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "service": "ai-service",
        "mock_ai_mode": settings.MOCK_AI_MODE,
        "policy_profile": settings.POLICY_PROFILE,
        "risk_backend": wf._risk().backend,
        "graph_backend": wf.create_graph().backend,
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model,
    }


@app.get("/risk/metrics", tags=["risk"])
def risk_metrics(
    threshold: float = Query(0.50, ge=0.0, le=1.0),
    n: int = Query(800, ge=100, le=5000),
) -> dict[str, Any]:
    """MLEval metrics (confusion matrix, accuracy, precision, recall/sensitivity,
    specificity, F1, AUC, ROC) for the XGBoost risk signal on synthetic data."""
    from app.risk.engine import get_risk_metrics

    return get_risk_metrics(threshold=threshold, n=n)


@app.get("/policies", tags=["system"])
def policies() -> dict[str, Any]:
    """Expose the loadable policy profiles (limits only) for UI display."""
    from pathlib import Path

    from app.policy.engine import load_policy

    out: dict[str, Any] = {}
    for p in sorted(Path(settings.POLICY_PATH).glob("*.yaml")):
        try:
            pol = load_policy(p)
            out[p.stem] = {"version": str(pol.get("version", "1.0")), "limits": pol.get("limits", {}),
                           "confidence": pol.get("confidence", {}), "flags": pol.get("flags", {})}
        except Exception:
            continue
    return out
