"""AI-service client tests (Team A): mock mode shape + error mapping."""

import asyncio
import math
import re

import pytest

from app.services import ai_service
from app.services.credit_memo_service import memo_lines, render_pdf


def test_mock_underwrite_is_contract_shaped(monkeypatch):
    monkeypatch.setattr(ai_service.settings, "MOCK_AI_MODE", True)
    resp = asyncio.run(ai_service.submit_underwrite({"id": "APP-X"}))
    assert resp["_mock"] and resp["run_id"]
    view = asyncio.run(ai_service.get_run(resp["run_id"]))
    for k in ("run_id", "status", "decision", "confidence", "reasons", "financials", "nodes", "policy"):
        assert k in view
    assert view["financials"]["foir"] < 0.5 and len(view["nodes"]) == 10
    w = asyncio.run(ai_service.run_what_if(resp["run_id"], {"overrides": {"tenure_months": 48}}))
    assert w["immutable"] is True and w["scenario"]["overrides"]["tenure_months"] == 48
    with pytest.raises(ai_service.AIServiceError):
        asyncio.run(ai_service.get_run("missing"))


def test_unreachable_ai_service_maps_to_503(monkeypatch):
    monkeypatch.setattr(ai_service.settings, "MOCK_AI_MODE", False)
    monkeypatch.setattr(ai_service.settings, "AI_SERVICE_URL", "http://127.0.0.1:9")
    monkeypatch.setattr(ai_service.settings, "AI_SERVICE_TIMEOUT", 1.0)
    with pytest.raises(ai_service.AIServiceError) as exc:
        asyncio.run(ai_service.get_run("x"))
    assert exc.value.status_code == 503


def test_pdf_renderer_produces_valid_pdf():
    memo = {"title": "Credit Memo (test)", "run_id": "r", "application_id": "a", "generated_at": "now",
            "generated_by": "t", "sections": {"decision": {"decision": "approved", "confidence": 0.88, "reasons": []},
                                              "reason_codes": [], "borrower_summary": {"ref_id": "B1"},
                                              "extracted_facts": [], "calculated_values": {"foir": 0.14, "emi": 3075.6},
                                              "risk_signal": {}, "ai_reasoning": {}, "policy_rules": {},
                                              "human_overrides": []}}
    lines = memo_lines(memo)
    pdf = render_pdf(lines * 3)  # multi-page
    assert pdf.startswith(b"%PDF-1.4") and pdf.rstrip().endswith(b"%%EOF")
    m = re.search(rb"/Count (\d+)", pdf)
    assert m, "renderer must emit a /Count for the page tree"
    expected_pages = math.ceil((len(lines) * 3) / 60) or 1
    assert int(m.group(1)) == expected_pages
