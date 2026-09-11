"""Application + document endpoint tests (Team A) — no AI service needed."""

from tests.conftest import load_case


def _body(name="clean_approval"):
    app = load_case(name)["application"]
    return {"product": app["product"], "borrower": app["borrower"], "loan_request": app["loan_request"]}


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["service"] == "backend"


def test_login_and_me(client):
    r = client.post("/auth/login", json={"email": "Reviewer@Example.com", "password": "x"})
    assert r.status_code == 200
    tok = r.json()["access_token"]
    assert r.json()["user"]["role"] == "reviewer"
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {tok}"})
    assert me.status_code == 200 and me.json()["email"] == "reviewer@example.com"
    assert client.get("/auth/me").status_code == 401
    assert client.post("/auth/login", json={"email": "", "password": ""}).status_code == 401


def test_create_get_list_application(client):
    r = client.post("/applications", json=_body())
    assert r.status_code == 201
    app = r.json()
    assert app["status"] == "documents_pending" and app["borrower"]["full_name"] == "Ravi Kumar"
    assert app["loan_request"]["vehicle_price"] == 120000
    g = client.get(f"/applications/{app['id']}")
    assert g.status_code == 200 and g.json()["id"] == app["id"] and g.json()["documents_count"] == 0
    lst = client.get("/applications").json()
    assert any(a["id"] == app["id"] for a in lst)
    assert client.get("/applications/nope").status_code == 404


def test_application_validation(client):
    bad = _body()
    bad["product"]["amount"] = -1
    assert client.post("/applications", json=bad).status_code == 422


def test_document_upload_validation_and_delete(client):
    app_id = client.post("/applications", json=_body()).json()["id"]
    ok = client.post(f"/applications/{app_id}/documents",
                     files={"file": ("bank_statement.txt", b"Average monthly income: Rs 38,900", "text/plain")})
    assert ok.status_code == 201
    doc = ok.json()
    assert doc["category"] == "bank_statement" and doc["size_bytes"] > 0 and "38,900" in doc["text_preview"]
    bad_type = client.post(f"/applications/{app_id}/documents", files={"file": ("x.exe", b"MZ", "application/octet-stream")})
    assert bad_type.status_code == 415
    too_big = client.post(f"/applications/{app_id}/documents", files={"file": ("big.txt", b"a" * (10 * 1024 * 1024 + 1), "text/plain")})
    assert too_big.status_code == 413
    bad_cat = client.post(f"/applications/{app_id}/documents", files={"file": ("a.txt", b"x", "text/plain")}, data={"category": "weird"})
    assert bad_cat.status_code == 422
    assert client.post("/applications/nope/documents", files={"file": ("a.txt", b"x", "text/plain")}).status_code == 404
    lst = client.get(f"/applications/{app_id}/documents").json()
    assert len(lst) == 1
    assert client.delete(f"/documents/{doc['id']}").status_code == 204
    assert client.get(f"/applications/{app_id}/documents").json() == []
    assert client.delete(f"/documents/{doc['id']}").status_code == 404


def test_dashboard_stats_shape(client):
    s = client.get("/dashboard/stats").json()
    for k in ("total_applications", "pending_review", "approved", "declined", "referred", "approval_rate",
              "runs_total", "runs_awaiting_human", "decisions_by_day", "recent_runs"):
        assert k in s
