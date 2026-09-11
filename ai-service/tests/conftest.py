"""Test bootstrap: isolated SQLite DB + deterministic (mock) AI mode.

Environment must be set BEFORE ``app.db.store`` is imported because the engine is
created at import time.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

SERVICE_DIR = Path(__file__).resolve().parent.parent
ROOT = SERVICE_DIR.parent
CASES_DIR = ROOT / "test-cases"

_tmp = tempfile.mkdtemp(prefix="acu-ai-tests-")
os.environ["DATABASE_URL"] = "sqlite:///" + (Path(_tmp) / "ai_service_test.db").as_posix()
os.environ["MOCK_AI_MODE"] = "true"
os.environ.setdefault("POLICY_PATH", str(SERVICE_DIR / "policies"))
sys.path.insert(0, str(SERVICE_DIR))


def load_case(name: str) -> dict:
    return json.loads((CASES_DIR / f"{name}.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def cases() -> dict[str, dict]:
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in CASES_DIR.glob("*.json")}


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c
