"""Extraction + confidence tests — Team B (deterministic, no LLM)."""

import asyncio

from app.agents.extraction_agent import ExtractionAgent
from app.extraction.document_classifier import classify_document, expected_fields
from app.extraction.pdf_parser import _field_from_text
from app.utils import confidence as cu

BANK = ("BANK STATEMENT - Demo Bank\nAccount holder name: Ravi Kumar\n"
        "Monthly credits (last 6 months): Rs 38,500 ; Rs 41,000 ; Rs 36,200\n"
        "Average monthly income (credits): Rs 38,900\nExisting EMI obligations: Rs 2,500\n")


def test_classify_document():
    assert classify_document("bank_statement.txt", "") == "bank_statement"
    assert classify_document("x.pdf", "Dealer invoice on-road price chassis") == "dealer_invoice"
    assert classify_document("x.pdf", "GigApp payout earnings") == "platform_earnings"
    assert classify_document("kyc.txt", "") == "kyc"
    assert "monthly_income" in expected_fields("bank_statement")


def test_label_anchored_extraction():
    inc = _field_from_text("monthly_income", BANK, "bank.txt")
    assert inc["value"] == 38900.0 and inc["confidence"] >= 0.9
    credits = _field_from_text("bank_credits", BANK, "bank.txt")
    assert credits["value"] == [38500.0, 41000.0, 36200.0]
    obl = _field_from_text("existing_monthly_obligations", BANK, "bank.txt")
    assert obl["value"] == 2500.0
    name = _field_from_text("full_name", BANK, "bank.txt")
    assert name["value"] == "Ravi Kumar"
    ident = _field_from_text("identity", "Aadhaar No: XXXX-XXXX-4321", "kyc.txt")
    assert ident["value"].startswith("XXXX-XXXX-4321")
    assert _field_from_text("monthly_income", "nothing here", "x") is None


def test_damaged_text_gets_low_confidence():
    item = _field_from_text("monthly_income", "Average monthly income: Rs 3?,900 [low quality scan]", "b.txt")
    assert item["confidence"] <= 0.40


def test_extraction_agent_never_invents_and_scales_by_ocr_quality():
    docs = [
        {"document_id": "bank.txt", "kind": "bank_statement", "text": BANK, "ocr_confidence": 0.5},
        {"document_id": "blank.pdf", "kind": "kyc", "text": ""},
    ]
    out = asyncio.run(ExtractionAgent().run(docs))
    inc = next(e for e in out if e["field"] == "monthly_income" and e["source_document"] == "bank.txt")
    assert inc["confidence"] <= 0.5  # 0.92 * 0.5
    blank = [e for e in out if e["source_document"] == "blank.pdf"]
    assert blank and blank[0]["value"] is None and blank[0]["confidence"] == 0.0
    for e in out:
        assert {"field", "value", "confidence", "source_document", "page", "evidence"} <= set(e)


def test_confidence_gates():
    assert cu.classify(0.9) == "high" and cu.classify(0.7) == "medium" and cu.classify(0.2) == "low"
    low = cu.critical_low_confidence({"monthly_income": 0.3, "address": 0.1, "loan_amount": 0.9}, 0.6)
    assert [i["field"] for i in low] == ["monthly_income"]  # address is not critical
    assert cu.aggregate_confidence([{"confidence": 1.0}, {"confidence": 0.5}]) == 0.75
