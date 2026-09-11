"""Risk-score metrics tests (Team B): confusion matrix + classification scores."""

from __future__ import annotations

from app.risk.engine import FEATURE_NAMES, get_risk_metrics


def _in_01(value):
    return 0.0 <= value <= 1.0


def test_metrics_contract_and_ranges():
    m = get_risk_metrics(threshold=0.5, n=800)
    for k in ("threshold", "n_samples", "prevalence", "confusion_matrix", "accuracy",
              "precision", "recall_sensitivity", "specificity", "npv", "fpr",
              "f1_score", "youden_index", "matthews_cc", "roc_auc", "roc_points",
              "backend", "model_version"):
        assert k in m, f"missing key {k}"
    cm = m["confusion_matrix"]
    assert cm["tp"] + cm["tn"] + cm["fp"] + cm["fn"] == m["n_samples"]
    assert cm["matrix"] == [[cm["tn"], cm["fp"]], [cm["fn"], cm["tp"]]]
    for v in cm.values():
        if isinstance(v, int):
            assert v >= 0
    for k in ("accuracy", "precision", "recall_sensitivity", "specificity", "npv",
              "f1_score"):
        assert _in_01(m[k]), f"{k} out of range: {m[k]}"
    assert _in_01(m["fpr"])
    assert 0.0 <= m["roc_auc"] <= 1.0


def test_self_consistent_fallback_has_strong_metrics():
    """Because the fallback mirrors the synthetic label generator, the signal should
    clearly separate risky vs clean borrowers (high AUC, high accuracy)."""
    m = get_risk_metrics(threshold=0.5, n=800)
    assert m["roc_auc"] > 0.90, m["roc_auc"]
    assert m["accuracy"] > 0.90, m["accuracy"]
    assert m["f1_score"] > 0.85, m["f1_score"]


def test_metrics_are_deterministic():
    a = get_risk_metrics(threshold=0.5, n=800, seed=7)
    b = get_risk_metrics(threshold=0.5, n=800, seed=7)
    assert a == b


def test_feature_names_loosely_ordered_ok():
    assert len(FEATURE_NAMES) >= 15
    for f in ("verified_monthly_income", "foir", "ltv", "emi_to_income",
              "income_mismatch_percentage", "document_confidence"):
        assert f in FEATURE_NAMES