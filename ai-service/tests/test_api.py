"""REST contract tests for the AI service (Team B) — consumed by the backend (Team A)."""

from tests.conftest import load_case


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["service"] == "ai-service"
    assert r.json()["risk_backend"] in ("fallback", "xgboost")


def test_policies_endpoint(client):
    r = client.get("/policies")
    assert set(r.json()) >= {"default", "conservative", "aggressive"}


def test_underwrite_lifecycle_over_http(client):
    case = load_case("clean_approval")
    r = client.post("/underwrite", json={**case["application"], "policy_profile": "default"})
    assert r.status_code == 202
    run_id = r.json()["run_id"]
    # TestClient runs background tasks before returning, so the run is done
    v = client.get(f"/underwrite/{run_id}").json()
    assert v["status"] == "completed" and v["decision"] == "approved"
    assert {"run_id", "status", "decision", "confidence", "reasons", "financials"} <= set(v)
    t = client.get(f"/underwrite/{run_id}/trace").json()
    assert t["steps"] and len(t["nodes"]) == 10
    rp = client.get(f"/underwrite/{run_id}/replay").json()
    assert rp["deterministic"] is True
    w = client.post(f"/underwrite/{run_id}/what-if", json={"overrides": {"tenure_months": 12}}).json()
    assert w["immutable"] and w["scenario"]["financials"]["emi"] > v["financials"]["emi"]
    runs = client.get("/underwrite", params={"application_id": case["application"]["id"]}).json()
    assert any(x["run_id"] == run_id for x in runs)


def test_sync_mode_and_resume_over_http(client):
    case = load_case("low_confidence")
    r = client.post("/underwrite", json={"application": case["application"], "sync": True})
    assert r.status_code == 202
    v = r.json()
    assert v["status"] == "awaiting_human"
    rr = client.post(f"/underwrite/{v['run_id']}/resume", json=case["resume"])
    assert rr.status_code == 200 and rr.json()["status"] == "completed"
    assert rr.json()["decision"] == "approved"


def test_404s(client):
    assert client.get("/underwrite/nope").status_code == 404
    assert client.get("/underwrite/nope/trace").status_code == 404
    assert client.post("/underwrite/nope/resume", json={}).status_code == 404
    assert client.post("/underwrite/nope/what-if", json={}).status_code == 404
