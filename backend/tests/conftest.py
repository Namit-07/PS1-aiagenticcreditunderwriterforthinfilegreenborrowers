"""Backend test bootstrap (Team A).

* isolated SQLite DB + upload dir
* a REAL AI service started as a subprocess (uvicorn) on a free port so the
  backend ↔ AI-service contract is exercised end-to-end over HTTP.
  If it cannot start (missing deps) the integration tests are skipped and the
  mock-mode tests still run.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
ROOT = BACKEND_DIR.parent
AI_DIR = ROOT / "ai-service"
CASES_DIR = ROOT / "test-cases"

_tmp = Path(tempfile.mkdtemp(prefix="acu-backend-tests-"))
os.environ["DATABASE_URL"] = "sqlite:///" + (_tmp / "backend_test.db").as_posix()
os.environ["UPLOAD_DIR"] = str(_tmp / "uploads")
os.environ["MOCK_AI_MODE"] = "false"
os.environ["SECRET_KEY"] = "test-secret"
sys.path.insert(0, str(BACKEND_DIR))


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def ai_service_url():
    """Boot the real AI service (Team B) for the session; yields its base URL or None."""
    port = _free_port()
    env = {**os.environ, "DATABASE_URL": "sqlite:///" + (_tmp / "ai_test.db").as_posix(), "MOCK_AI_MODE": "true",
           "PYTHONUNBUFFERED": "1"}
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port), "--log-level", "warning"],
                            cwd=str(AI_DIR), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = f"http://127.0.0.1:{port}"
    ready = False
    for _ in range(80):
        if proc.poll() is not None:
            break
        try:
            with urllib.request.urlopen(f"{url}/health", timeout=1) as r:
                if r.status == 200:
                    ready = True
                    break
        except Exception:
            time.sleep(0.25)
    if not ready:
        proc.terminate()
        yield None
        return
    yield url
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture(scope="session")
def client(ai_service_url):
    from fastapi.testclient import TestClient

    from app.main import app
    from app.services import ai_service

    if ai_service_url:
        ai_service.settings.AI_SERVICE_URL = ai_service_url
        ai_service.settings.MOCK_AI_MODE = False
    else:
        ai_service.settings.MOCK_AI_MODE = True
    with TestClient(app) as c:
        c.ai_live = bool(ai_service_url)  # type: ignore[attr-defined]
        yield c


def load_case(name: str) -> dict:
    return json.loads((CASES_DIR / f"{name}.json").read_text(encoding="utf-8"))


def create_case_application(client, name: str) -> tuple[str, dict]:
    """Create the application + upload its documents from a scenario fixture."""
    case = load_case(name)
    app = case["application"]
    body = {"product": app["product"], "borrower": app["borrower"], "loan_request": app["loan_request"]}
    r = client.post("/applications", json=body)
    assert r.status_code == 201, r.text
    app_id = r.json()["id"]
    for d in app["documents"]:
        files = {"file": (d["filename"], d["text"].encode("utf-8"), "text/plain")}
        data = {"category": d["kind"]}
        if d.get("ocr_confidence") is not None:
            # emulate a low-quality scan: the backend cannot know OCR quality for .txt, so we
            # pass it through the AI payload via the document category suffix-free path below
            data["ocr_confidence"] = str(d["ocr_confidence"])
        r = client.post(f"/applications/{app_id}/documents", files=files, data=data)
        assert r.status_code == 201, r.text
    return app_id, case
