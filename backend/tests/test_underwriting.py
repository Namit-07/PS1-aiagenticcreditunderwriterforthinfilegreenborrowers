"""Underwriting endpoint tests (Team A) — end-to-end over HTTP against the real AI service."""

import pytest

from tests.conftest import create_case_application, load_case


def _needs_ai(client):
    if not getattr(client, "ai_live", False):
        pytest.skip("AI service could not be started for integration tests")


def _start(client, name, profile=None):
    app_id, case = create_case_application(client, name)
    body = {"policy_profile": profile} if profile else {}
    r = client.post(f"/applications/{app_id}/underwrite", json=body)
    assert r.status_code == 202, r.text
    return app_id, r.json()["run_id"], case


@pytest.mark.parametrize("name,decision", [("clean_approval", "approved"), ("high_foir", "declined"),
                                           ("income_mismatch", "referred"), ("missing_document", "referred")])
def test_start_underwrite_and_get_run(client, name, decision):
    _needs_ai(client)
    app_id, run_id, case = _start(client, name)
    view = client.get(f"/underwriting/{run_id}").json()
    assert view["status"] == "completed" and view["decision"] == decision, view.get("reasons")
    assert view["stale"] is False and len(view["nodes"]) == 10
    for code in case["expected"].get("reason_codes_include", []):
        assert code in {r["code"] for r in view["reasons"]}
    app = client.get(f"/applications/{app_id}").json()
    assert app["status"] == decision and app["latest_run_id"] == run_id and app["latest_decision"] == decision
    runs = client.get(f"/applications/{app_id}/runs").json()
    assert runs[0]["run_id"] == run_id and runs[0]["decision"] == decision


def test_trace_replay_what_if_and_memo(client):
    _needs_ai(client)
    app_id, run_id, case = _start(client, "what_if_approval")
    trace = client.get(f"/underwriting/{run_id}/trace").json()
    assert trace["steps"] and trace["backend_steps"][0]["event_type"] == "RUN_REQUESTED"
    assert client.get(f"/audit/runs/{run_id}").json()["run_id"] == run_id
    rep = client.get(f"/underwriting/{run_id}/replay").json()
    assert rep["deterministic"] is True
    wi = client.post(f"/underwriting/{run_id}/what-if", json=case["what_if"]).json()
    assert wi["immutable"] and wi["scenario"]["decision"]["decision"] == "approved"
    assert wi["base"]["decision"]["decision"] == "declined"
    assert client.get(f"/underwriting/{run_id}").json()["decision"] == "declined"
    hist = client.get(f"/underwriting/{run_id}/what-ifs").json()
    assert len(hist) == 1 and hist[0]["what_if_id"] == wi["what_if_id"]
    memo = client.get(f"/applications/{app_id}/credit-memo").json()
    assert memo["sections"]["decision"]["decision"] == "declined" and memo["sections"]["calculated_values"]["foir"] > 0.5
    pdf = client.get(f"/applications/{app_id}/credit-memo", params={"format": "pdf"})
    assert pdf.status_code == 200 and pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF-1.4") and b"HIGH_FOIR" in pdf.content
    assert any(r["run_id"] == run_id for r in client.get("/audit/runs").json())


def test_human_review_pause_resume_over_http(client):
    _needs_ai(client)
    app_id, run_id, case = _start(client, "low_confidence")
    view = client.get(f"/underwriting/{run_id}").json()
    assert view["status"] == "awaiting_human" and view["decision"] == "human_review"
    assert client.get(f"/applications/{app_id}").json()["status"] == "awaiting_human"
    queue = client.get("/audit/runs", params={"status": "awaiting_human"}).json()
    assert any(r["run_id"] == run_id for r in queue)
    tok = client.post("/auth/login", json={"email": "ana.reviewer@example.com", "password": "pw"}).json()["access_token"]
    partial = client.post(f"/underwriting/{run_id}/resume", json={"reviews": case["resume"]["reviews"][:1]},
                          headers={"Authorization": f"Bearer {tok}"}).json()
    assert partial["status"] == "awaiting_human" and partial["pending_fields"]
    done = client.post(f"/underwriting/{run_id}/resume", json={"reviews": case["resume"]["reviews"][1:]},
                       headers={"Authorization": f"Bearer {tok}"}).json()
    assert done["status"] == "completed" and done["decision"] == "approved"
    assert done["human_reviews"][0]["reviewer"] == "ana.reviewer@example.com"
    assert client.get(f"/applications/{app_id}").json()["status"] == "approved"
    trace = client.get(f"/underwriting/{run_id}/trace").json()
    assert any(s["event_type"] == "HUMAN_REVIEW_SUBMITTED" for s in trace["backend_steps"])


def test_policy_profile_passthrough(client):
    _needs_ai(client)
    _, run_id, _ = _start(client, "low_age", profile="aggressive")
    view = client.get(f"/underwriting/{run_id}").json()
    assert view["policy"]["profile"] == "aggressive" and view["decision"] == "approved"


def test_finalize_decision_override(client):
    _needs_ai(client)
    app_id, run_id, _ = _start(client, "clean_approval")
    r = client.post(f"/applications/{app_id}/decision", json={"decision": "referred", "notes": "second look", "reviewer": "lead"})
    assert r.status_code == 200 and r.json()["decision"] == "referred"
    assert client.get(f"/applications/{app_id}").json()["status"] == "referred"


def test_underwrite_unknown_application_and_run(client):
    assert client.post("/applications/nope/underwrite", json={}).status_code == 404
    assert client.get("/underwriting/nope").status_code == 404
    assert client.get("/underwriting/nope/trace").status_code == 404
