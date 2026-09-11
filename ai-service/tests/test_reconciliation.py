"""Reconciliation + policy engine tests — Team B."""

import pytest

from app.policy import engine as pe
from app.reconciliation import engine as re_


def _src(value, source):
    return {"value": value, "source": source, "page": 1, "confidence": 0.9}


def test_income_mismatch_percentage_is_deterministic():
    items = [_src(45000, "application_form"), _src(38500, "bank_statement.txt")]
    pct = re_.income_mismatch_percentage(items)
    assert pct == pytest.approx((45000 - 38500) / 45000, abs=1e-4)
    assert re_.income_mismatch_percentage([_src(1, "a")]) is None


def test_reconcile_flags_income_name_and_missing_documents():
    facts = {
        "full_name": [_src("Ravi Kumar", "kyc.txt"), _src("Ravi Kumaar", "bank.txt")],
        "monthly_income": [_src(45000, "application_form"), _src(38500, "bank.txt")],
        "documents_available": ["kyc", "bank_statement"],
    }
    out = re_.reconcile(facts, {"mismatch": {}})
    types = {i["type"]: i for i in out["items"]}
    assert "NAME_MISMATCH" in types and types["NAME_MISMATCH"]["severity"] == "HIGH"
    assert "INCOME_MISMATCH" in types and types["INCOME_MISMATCH"]["severity"] == "MEDIUM"
    assert "MISSING_DOCUMENT" in types
    assert out["has_high_severity"] is True
    assert out["income_mismatch_percentage"] == pytest.approx(0.1444, abs=1e-3)


def test_reconcile_respects_policy_required_documents():
    facts = {"documents_available": ["kyc", "bank_statement", "dealer_invoice"]}
    out = re_.reconcile(facts, {"required_documents": ["kyc", "bank_statement", "dealer_invoice", "platform_earnings"]})
    assert [i["type"] for i in out["items"]] == ["MISSING_DOCUMENT"]
    out2 = re_.reconcile(facts, {"required_documents": ["kyc"]})
    assert out2["items"] == []


def test_severity_bands():
    assert re_._sev(0.20) == "HIGH"
    assert re_._sev(0.07) == "MEDIUM"
    assert re_._sev(0.01) == "LOW"


@pytest.mark.parametrize("profile,foir_max,ltv_max,min_age", [
    ("default", 0.50, 0.80, 21), ("conservative", 0.40, 0.70, 23), ("aggressive", 0.60, 0.90, 18)])
def test_policies_load_from_yaml(profile, foir_max, ltv_max, min_age):
    from app.config import get_settings

    pol = pe.load_policy(get_settings().policy_file(profile))
    assert pol["profile"] == profile
    assert pol["limits"]["foir_max"] == pytest.approx(foir_max)
    assert pol["limits"]["ltv_max"] == pytest.approx(ltv_max)
    assert pol["limits"]["min_age"] == min_age


def test_policy_violations():
    pol = pe.load_policy(__import__("app.config", fromlist=["get_settings"]).get_settings().policy_file("default"))
    v = pe.financial_violations({"foir": 0.55, "ltv": 0.95}, pol)
    assert {x["code"] for x in v} == {"HIGH_FOIR", "HIGH_LTV"}
    assert all(x["severity"] == "blocker" for x in v)
    assert pe.financial_violations({"foir": 0.3, "ltv": 0.7}, pol) == []
    assert [x["code"] for x in pe.application_violations({"borrower": {"age": 19}}, pol)] == ["LOW_AGE"]
    assert [x["code"] for x in pe.application_violations({"loan_request": {"tenure_months": 72}}, pol)] == ["MAX_TENURE_EXCEEDED"]
    assert [x["code"] for x in pe.confidence_violations({"overall": 0.4}, pol)] == ["LOW_OVERALL_CONFIDENCE"]
    assert [x["code"] for x in pe.income_violations({"verified_income": 0}, pol)] == ["NO_VERIFIED_INCOME"]
    assert pe.required_documents(pol) == ["kyc", "bank_statement", "dealer_invoice", "platform_earnings"]


def test_reason_codes_contract_covers_emitted_codes():
    """Every code the decision agent can emit must exist in shared/reason_codes.yaml."""
    from pathlib import Path

    from app.policy.engine import load_policy

    codes = load_policy(Path(__file__).resolve().parents[2] / "shared" / "reason_codes.yaml")["reason_codes"]
    for code in ("HIGH_FOIR", "HIGH_LTV", "LOW_AGE", "MAX_TENURE_EXCEEDED", "NO_VERIFIED_INCOME",
                 "LOW_OVERALL_CONFIDENCE", "LOW_INCOME_CONFIDENCE", "INCOME_MISMATCH", "NAME_MISMATCH",
                 "VEHICLE_PRICE_MISMATCH", "LOAN_VS_INVOICE", "MISSING_DOCUMENT", "HUMAN_REVIEW_REQUIRED"):
        assert code in codes, code
