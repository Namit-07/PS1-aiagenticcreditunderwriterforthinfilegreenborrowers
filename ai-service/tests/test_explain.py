"""SHAP explanation layer tests (Team B).

The contract must hold for both backends: ``base_value + Σφ == score`` and the words
must name the true cause of the outcome (policy margins), with SHAP as context.
"""

import asyncio
import copy

import pytest

from app.risk.engine import FEATURE_NAMES, RiskScorer, _deterministic_risk
from app.risk.explain import baseline_features, build_decision_explanation, explain_risk, policy_checks
from app.workflows import underwriting_graph as wf
from tests.conftest import load_case

RISKY = {
    "verified_monthly_income": 21750.0, "income_volatility": 0.044, "income_stability": 0.956,
    "foir": 0.614, "ltv": 0.75, "emi_to_income": 0.338, "existing_monthly_obligations": 6000.0,
    "bank_balance_trend": -0.036, "income_sources": 3.0, "income_mismatch_percentage": 0.0,
    "document_confidence": 0.92, "identity_mismatch_flag": 0.0, "repayment_history_score": 0.7,
    "employment_stability": 0.956, "loan_amount": 150000.0, "vehicle_price": 200000.0, "tenure_months": 24.0,
}


def test_fallback_shap_is_exactly_additive():
    scorer = RiskScorer()  # fallback (no xgboost in the test environment) or xgboost — both must hold
    ex = explain_risk(RISKY, scorer.model)
    assert set(r["feature"] for r in ex["contributions"]) == set(FEATURE_NAMES)
    assert ex["additivity_error"] < 1e-6
    assert abs(ex["base_value"] + ex["sum_contributions"] - ex["score"]) < 5e-6  # rounded to 6 dp
    if scorer.model is None:
        assert ex["method"] == "additive_exact"
        assert abs(ex["score"] - _deterministic_risk(RISKY)) < 1e-6


def test_high_foir_raises_risk_and_is_top_driver():
    ex = explain_risk(RISKY, None)
    foir = next(r for r in ex["contributions"] if r["feature"] == "foir")
    assert foir["direction"] == "raises" and foir["shap"] > 0
    assert ex["top_risk_raising"][0] == "foir"
    # a borrower at the baseline has zero contributions everywhere
    base = explain_risk(baseline_features(), None)
    assert all(abs(r["shap"]) < 1e-9 for r in base["contributions"])
    assert abs(base["score"] - base["base_value"]) < 1e-9


def test_policy_checks_report_signed_margins():
    checks = policy_checks({"foir": 0.614, "ltv": 0.75, "verified_income": 21750},
                           {"limits": {"foir_max": 0.5, "ltv_max": 0.8, "min_age": 21}},
                           {"borrower": {"age": 26}})
    by = {c["code"]: c for c in checks}
    assert by["HIGH_FOIR"]["passed"] is False and by["HIGH_FOIR"]["margin"] == pytest.approx(-0.114)
    assert by["HIGH_LTV"]["passed"] is True and by["HIGH_LTV"]["margin"] == pytest.approx(0.05)
    assert by["LOW_AGE"]["passed"] is True and by["LOW_AGE"]["margin"] == 5
    assert "61.4%" in by["HIGH_FOIR"]["display"] and "50.0%" in by["HIGH_FOIR"]["display"]


def test_linguistic_answer_names_the_cause():
    risk = {"risk_score": 0.45, "risk_band": "MEDIUM", "shap": explain_risk(RISKY, None)}
    fin = {"foir": 0.614, "ltv": 0.75, "verified_income": 21750, "emi": 7344}
    policy = {"limits": {"foir_max": 0.5, "ltv_max": 0.8, "min_age": 21}}
    declined = build_decision_explanation(
        {"decision": "declined", "reasons": [{"code": "HIGH_FOIR", "severity": "blocker", "message": "x"}]},
        fin, policy, {"borrower": {"age": 26}}, risk, approval_path={"description": "extend tenure 24 → 42 months",
                                                                     "financials": {"foir": 0.491, "emi": 4687}},
        borrower_name="Arjun Mehta")
    assert declined["headline"].startswith("Arjun Mehta's loan is declined because")
    assert "FOIR 61.4% vs limit 50.0%" in declined["headline"]
    assert any("extend tenure 24 → 42 months" in s for s in declined["sentences"])
    assert any("pushes risk up" in s and "foir" in s.lower() for s in declined["sentences"])
    assert declined["generated_by"] == "template"

    approved = build_decision_explanation({"decision": "approved", "reasons": []},
                                          {"foir": 0.14, "ltv": 0.75, "verified_income": 39150}, policy,
                                          {"borrower": {"age": 29}}, risk, borrower_name="Ravi Kumar")
    assert "approved because every policy test passed" in approved["headline"]
    referred = build_decision_explanation({"decision": "referred", "reasons": [{"code": "INCOME_MISMATCH", "severity": "warning",
                                                                                "message": "Monthly income differs across documents by 13.6%"}]},
                                          fin, policy, {"borrower": {"age": 31}}, risk, borrower_name="Priya Sharma")
    assert "referred to a human underwriter because Monthly income differs" in referred["headline"]


def test_workflow_persists_shap_and_explanation():
    case = load_case("high_foir")
    run_id = wf.new_run_id()
    asyncio.run(wf.run_pipeline(run_id, copy.deepcopy(case["application"]), case.get("policy_profile")))
    view = wf.run_view(run_id)
    shap = view["risk"]["shap"]
    assert shap["additivity_error"] < 1e-6 and len(shap["contributions"]) == len(FEATURE_NAMES)
    ex = view["explanation"]
    assert ex["outcome"] == "declined" and "declined because" in ex["headline"]
    assert any(not c["passed"] and c["code"] == "HIGH_FOIR" for c in ex["policy_checks"])
    assert view["memo"]["sections"]["decision_explanation"]["headline"] == ex["headline"]
    events = {e["event_type"] for e in wf.trace_view(run_id)["steps"]}
    assert "DECISION_EXPLAINED" in events
