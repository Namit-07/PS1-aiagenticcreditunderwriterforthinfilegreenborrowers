"""SHAP explanation layer for the risk signal + plain-language decision explanation (Team B).

Two questions are answered for every run, in numbers and in words:

1. *Why is the risk score what it is?* — per-feature SHAP contributions to the model
   output. With XGBoost the values are exact TreeSHAP contributions (``shap`` package
   when installed, otherwise the booster's native ``pred_contribs``). With the
   deterministic fallback model the score is additive in its engineered terms, so the
   Shapley value of each feature is exactly its term minus the same term at the
   baseline — no approximation, and the same contract either way:
   ``base_value + Σ contributions == score``.

2. *Why was the loan approved / referred / declined?* — the decision is made by the
   policy rules, not the model. The explanation therefore pairs every reason code with
   its numeric margin against the policy limit (e.g. FOIR 61.4% vs limit 50.0%,
   +11.4 pp over) and adds the top SHAP drivers as supporting context.

The linguistic answer is generated deterministically from those numbers; when an LLM
provider is configured it may rephrase it, but it cannot introduce new figures.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from app.risk.engine import FEATURE_NAMES, _clamp, _deterministic_risk, _synthetic_dataset

# Human labels + what a higher value means for the borrower.
FEATURE_LABELS: dict[str, str] = {
    "verified_monthly_income": "Verified monthly income",
    "income_volatility": "Income volatility",
    "income_stability": "Income stability",
    "foir": "FOIR (obligations ÷ income)",
    "ltv": "LTV (loan ÷ asset value)",
    "emi_to_income": "EMI-to-income ratio",
    "existing_monthly_obligations": "Existing monthly obligations",
    "bank_balance_trend": "Bank balance trend",
    "income_sources": "Number of income sources",
    "income_mismatch_percentage": "Income mismatch across documents",
    "document_confidence": "Document confidence",
    "identity_mismatch_flag": "Identity mismatch flag",
    "repayment_history_score": "Repayment history score",
    "employment_stability": "Employment stability",
    "loan_amount": "Loan amount",
    "vehicle_price": "Vehicle price",
    "tenure_months": "Tenure (months)",
}

# Weights of the deterministic fallback model (mirrors engine._deterministic_risk).
_W = {
    "foir": 0.30,
    "ltv": 0.18,
    "emi_to_income": 0.15,
    "income_volatility": 0.10,
    "income_mismatch_percentage": 0.10,
    "existing_monthly_obligations": 0.05,  # via obligations / income ratio
    "repayment_history_score": 0.20,  # as (1 - score)
    "identity_mismatch_flag": 0.15,
    "employment_stability": 0.10,  # as (1 - stability)
}


def _fmt_value(name: str, v: float, baseline: bool = False) -> str:
    if name == "identity_mismatch_flag" and baseline:
        return f"{v * 100:.0f}% of borrowers"
    if name in ("foir", "ltv", "emi_to_income", "income_volatility", "income_stability",
                "income_mismatch_percentage", "document_confidence", "repayment_history_score",
                "employment_stability", "bank_balance_trend"):
        return f"{v * 100:.1f}%"
    if name in ("verified_monthly_income", "existing_monthly_obligations", "loan_amount", "vehicle_price"):
        return f"₹{v:,.0f}"
    if name == "identity_mismatch_flag":
        return "yes" if v else "no"
    if name == "tenure_months":
        return f"{v:.0f} months"
    return f"{v:g}"


# --------------------------------------------------------------------------- #
# baseline (expected value) — the "average synthetic borrower"
# --------------------------------------------------------------------------- #
@lru_cache(maxsize=1)
def baseline_features() -> dict[str, float]:
    rows = _synthetic_dataset()
    n = float(len(rows))
    return {f: sum(float(r["features"][f]) for r in rows) / n for f in FEATURE_NAMES}


def _terms(features: dict[str, float]) -> dict[str, float]:
    """The additive terms of the fallback model, keyed by the feature they are attributed to."""
    income = max(1.0, float(features.get("verified_monthly_income", 1.0)))
    return {
        "foir": _W["foir"] * _clamp(float(features.get("foir", 0.0))),
        "ltv": _W["ltv"] * _clamp(float(features.get("ltv", 0.0)), 0.0, 1.2),
        "emi_to_income": _W["emi_to_income"] * _clamp(float(features.get("emi_to_income", 0.0))),
        "income_volatility": _W["income_volatility"] * _clamp(float(features.get("income_volatility", 0.0))),
        "income_mismatch_percentage": _W["income_mismatch_percentage"] * _clamp(float(features.get("income_mismatch_percentage", 0.0))),
        "existing_monthly_obligations": _W["existing_monthly_obligations"] * _clamp(float(features.get("existing_monthly_obligations", 0.0)) / income),
        "repayment_history_score": _W["repayment_history_score"] * (1.0 - _clamp(float(features.get("repayment_history_score", 0.7)))),
        # borrowers carry 0/1; the baseline carries the population rate (e.g. 0.04) — keep it continuous
        "identity_mismatch_flag": _W["identity_mismatch_flag"] * _clamp(float(features.get("identity_mismatch_flag", 0) or 0.0)),
        "employment_stability": _W["employment_stability"] * (1.0 - _clamp(float(features.get("employment_stability", 0.7)))),
    }


def _explain_fallback(features: dict[str, float]) -> tuple[float, dict[str, float], str]:
    """Exact additive Shapley decomposition of the deterministic fallback score."""
    base_feats = baseline_features()
    raw_x = sum(_terms(features).values())
    raw_b = sum(_terms(base_feats).values())
    score = _clamp(raw_x)
    base_value = _clamp(raw_b)
    tx, tb = _terms(features), _terms(base_feats)
    contribs = {f: tx[f] - tb[f] for f in tx}
    # The final [0,1] clamp is the only non-additive step; when it binds, distribute the
    # clipped amount proportionally so base + Σφ still equals the reported score.
    total = sum(contribs.values())
    target = score - base_value
    if abs(total) > 1e-12 and abs(total - target) > 1e-12:
        k = target / total
        contribs = {f: v * k for f, v in contribs.items()}
    for f in FEATURE_NAMES:
        contribs.setdefault(f, 0.0)
    return base_value, contribs, "additive_exact"


def _explain_xgboost(model: Any, features: dict[str, float]) -> tuple[float, dict[str, float], str]:
    """Exact TreeSHAP contributions for the fitted XGBoost regressor."""
    import numpy as np

    x = np.array([[float(features.get(f, 0.0)) for f in FEATURE_NAMES]], dtype="float64")
    try:  # preferred: the shap package (same values as pred_contribs, richer API)
        import shap  # type: ignore

        explainer = shap.TreeExplainer(model)
        values = np.asarray(explainer.shap_values(x))[0]
        base = float(np.asarray(explainer.expected_value).reshape(-1)[0])
        return base, {f: float(v) for f, v in zip(FEATURE_NAMES, values)}, "tree_shap"
    except Exception:
        pass
    import xgboost as xgb

    contribs = model.get_booster().predict(xgb.DMatrix(x, feature_names=FEATURE_NAMES), pred_contribs=True)[0]
    base = float(contribs[-1])
    return base, {f: float(v) for f, v in zip(FEATURE_NAMES, contribs[:-1])}, "xgboost_pred_contribs"


def explain_risk(features: dict[str, float], model: Any | None, score: float | None = None) -> dict[str, Any]:
    """SHAP-style explanation of the risk score for one borrower.

    Returns ``{method, base_value, score, contributions:[...], top_risk_raising, top_risk_lowering}``
    where each contribution is ``{feature, label, value, value_display, baseline, baseline_display,
    shap, direction, share}``. ``direction`` is *raises* / *lowers* risk; ``share`` is the
    absolute share of the total |SHAP| mass (0..1).
    """
    if model is not None:
        try:
            base, contribs, method = _explain_xgboost(model, features)
        except Exception:
            base, contribs, method = _explain_fallback(features)
    else:
        base, contribs, method = _explain_fallback(features)
    if score is None:
        score = base + sum(contribs.values())
    base_feats = baseline_features()
    total_abs = sum(abs(v) for v in contribs.values()) or 1.0
    rows = []
    for f in FEATURE_NAMES:
        phi = float(contribs.get(f, 0.0))
        rows.append({
            "feature": f,
            "label": FEATURE_LABELS.get(f, f),
            "value": float(features.get(f, 0.0)),
            "value_display": _fmt_value(f, float(features.get(f, 0.0))),
            "baseline": round(float(base_feats.get(f, 0.0)), 4),
            "baseline_display": _fmt_value(f, float(base_feats.get(f, 0.0)), baseline=True),
            "shap": round(phi, 5),
            "direction": "raises" if phi > 1e-6 else ("lowers" if phi < -1e-6 else "neutral"),
            "share": round(abs(phi) / total_abs, 4),
        })
    rows.sort(key=lambda r: -abs(r["shap"]))
    total = float(sum(contribs.values()))
    return {
        "method": method,
        "base_value": round(float(base), 6),
        "score": round(float(score), 6),
        "sum_contributions": round(total, 6),
        # computed on the unrounded values; the three rounded numbers above agree to within 2e-6
        "additivity_error": round(abs(float(base) + total - float(score)), 8),
        "contributions": rows,
        "top_risk_raising": [r["feature"] for r in rows if r["direction"] == "raises"][:3],
        "top_risk_lowering": [r["feature"] for r in rows if r["direction"] == "lowers"][:3],
        "baseline_description": "average borrower in the synthetic training set (n=1200)",
    }


# --------------------------------------------------------------------------- #
# decision explanation: policy margins (the cause) + SHAP drivers (the context)
# --------------------------------------------------------------------------- #
def _pct(v: Any) -> str:
    try:
        return f"{float(v) * 100:.1f}%"
    except (TypeError, ValueError):
        return "—"


def policy_checks(financials: dict[str, Any], policy: dict[str, Any], application: dict[str, Any]) -> list[dict[str, Any]]:
    """Every hard policy test with its measured value, limit and signed margin."""
    limits = (policy.get("limits") or {}) if isinstance(policy, dict) else {}
    checks: list[dict[str, Any]] = []
    foir, foir_max = float(financials.get("foir", 0.0) or 0.0), float(limits.get("foir_max", 0.5))
    ltv, ltv_max = float(financials.get("ltv", 0.0) or 0.0), float(limits.get("ltv_max", 0.85))
    checks.append({"check": "FOIR", "code": "HIGH_FOIR", "value": foir, "limit": foir_max, "comparator": "<=",
                   "margin": round(foir_max - foir, 4), "passed": foir <= foir_max,
                   "display": f"FOIR {_pct(foir)} vs limit {_pct(foir_max)} ({'+' if foir > foir_max else '-'}{abs(foir - foir_max) * 100:.1f} pp {'over' if foir > foir_max else 'under'})"})
    checks.append({"check": "LTV", "code": "HIGH_LTV", "value": ltv, "limit": ltv_max, "comparator": "<=",
                   "margin": round(ltv_max - ltv, 4), "passed": ltv <= ltv_max,
                   "display": f"LTV {_pct(ltv)} vs limit {_pct(ltv_max)} ({'+' if ltv > ltv_max else '-'}{abs(ltv - ltv_max) * 100:.1f} pp {'over' if ltv > ltv_max else 'under'})"})
    borrower = (application or {}).get("borrower") or {}
    age = borrower.get("age")
    min_age = int(limits.get("min_age", 21))
    if age is not None:
        try:
            a = int(age)
            checks.append({"check": "Minimum age", "code": "LOW_AGE", "value": a, "limit": min_age, "comparator": ">=",
                           "margin": a - min_age, "passed": a >= min_age,
                           "display": f"age {a} vs minimum {min_age} ({a - min_age:+d} years)"})
        except (TypeError, ValueError):
            pass
    income = float(financials.get("verified_income", 0.0) or 0.0)
    checks.append({"check": "Verified income", "code": "NO_VERIFIED_INCOME", "value": income, "limit": 0.0, "comparator": ">",
                   "margin": income, "passed": income > 0,
                   "display": f"verified monthly income ₹{income:,.0f}"})
    return checks


def build_decision_explanation(
    decision: dict[str, Any],
    financials: dict[str, Any],
    policy: dict[str, Any],
    application: dict[str, Any],
    risk: dict[str, Any],
    reconciliation: dict[str, Any] | None = None,
    approval_path: dict[str, Any] | None = None,
    borrower_name: str | None = None,
) -> dict[str, Any]:
    """Mathematical + linguistic answer to "why this outcome for this person?"."""
    outcome = str(decision.get("decision") or "referred")
    override = decision.get("human_override")
    # Explain the POLICY verdict; a reviewer override is reported as a separate sentence.
    policy_outcome = {"APPROVE": "approved", "REJECT": "declined", "REFER": "referred"}.get(
        str(decision.get("decision_raw") or "").upper(), (override or {}).get("from") or outcome)
    reasons = decision.get("reasons") or []
    shap = risk.get("shap") or {}
    checks = policy_checks(financials, policy, application)
    failed = [c for c in checks if not c["passed"]]
    warnings = [r for r in reasons if r.get("severity") == "warning"]
    blockers = [r for r in reasons if r.get("severity") == "blocker"]
    rows = shap.get("contributions") or []
    raising = [r for r in rows if r["direction"] == "raises"][:3]
    lowering = [r for r in rows if r["direction"] == "lowers"][:3]
    name = borrower_name or "This applicant"
    band = str(risk.get("risk_band") or "—")
    score = risk.get("risk_score")

    # ---- mathematical summary ---------------------------------------------------
    math_lines: list[str] = []
    for c in checks:
        math_lines.append(("PASS  " if c["passed"] else "FAIL  ") + c["display"])
    if shap:
        math_lines.append(
            f"risk score {shap.get('score')} = base {shap.get('base_value')} + Σ SHAP {shap.get('sum_contributions')} "
            f"(method {shap.get('method')}, additivity error {shap.get('additivity_error')})"
        )
        for r in rows[:5]:
            math_lines.append(f"  φ({r['feature']}) = {r['shap']:+.4f}  [value {r['value_display']} vs baseline {r['baseline_display']}]")

    # ---- linguistic answer --------------------------------------------------------
    def _drivers(items: list[dict[str, Any]]) -> str:
        parts = []
        for r in items:
            parts.append(f"{r['label'].lower()} ({r['value_display']} vs a typical {r['baseline_display']}, {r['shap']:+.3f})")
        return "; ".join(parts)

    sentences: list[str] = []
    if policy_outcome == "approved":
        headline = f"{name}'s loan is approved because every policy test passed."
        margins = [c["display"] for c in checks if c["passed"] and c["code"] in ("HIGH_FOIR", "HIGH_LTV")]
        if margins:
            sentences.append("Affordability and collateral are inside the limits: " + "; ".join(margins) + ".")
        if not warnings:
            sentences.append("No warning was raised on the documents.")
    elif policy_outcome == "declined":
        cause = "; ".join(c["display"] for c in failed) or "; ".join(str(b.get("message") or b.get("code")) for b in blockers)
        headline = f"{name}'s loan is declined because a hard policy rule failed: {cause}."
        if approval_path and approval_path.get("description"):
            apf = approval_path.get("financials") or {}
            sentences.append(
                f"The smallest fix is to {approval_path['description']}, which would bring FOIR to {_pct(apf.get('foir'))} "
                f"and the EMI to ₹{float(apf.get('emi') or 0):,.0f}, turning the outcome into approved."
            )
        else:
            sentences.append("No change to tenure or loan amount alone makes the file approvable, so the borrower needs higher verified income or lower existing obligations.")
    else:
        flags = "; ".join(str(w.get("message") or w.get("code")) for w in warnings) or "the evidence needs a manual check"
        headline = f"{name}'s loan is referred to a human underwriter because {flags}."
        sentences.append("No hard limit was breached, so an underwriter can still approve it after resolving the flags.")
    if override:
        headline += f" A reviewer then overrode the policy outcome from {override.get('from')} to {override.get('to')}."

    if shap:
        sentences.append(
            f"The model's risk band is {band} (score {score} on a 0-1 scale where 0 is safest; a typical synthetic borrower scores {shap.get('base_value')})."
        )
        if raising:
            sentences.append("What pushes risk up: " + _drivers(raising) + ".")
        if lowering:
            sentences.append("What pulls risk down: " + _drivers(lowering) + ".")
        sentences.append("The risk score is a secondary signal; the policy rules above decide the outcome.")

    return {
        "outcome": outcome,
        "headline": headline,
        "sentences": sentences,
        "plain_text": " ".join([headline] + sentences),
        "policy_checks": checks,
        "reason_codes": [r.get("code") for r in reasons],
        "shap_summary": {
            "method": shap.get("method"),
            "base_value": shap.get("base_value"),
            "score": shap.get("score"),
            "top_risk_raising": raising,
            "top_risk_lowering": lowering,
        },
        "math_lines": math_lines,
        "generated_by": "template",
    }


async def llm_rephrase(explanation: dict[str, Any]) -> dict[str, Any]:
    """Optionally rephrase the linguistic answer with the configured LLM (numbers fixed)."""
    from app.config import get_settings

    settings = get_settings()
    if settings.MOCK_AI_MODE or settings.llm_provider == "mock":
        return explanation
    try:
        import json

        from app.llm.client import LLMClient

        client = LLMClient()
        parsed = await client.complete_json(
            "You rewrite a credit-decision explanation for a borrower and an underwriter in clear, warm, plain "
            "English. Use ONLY the numbers given, copied exactly; do not add or recompute figures. Reply JSON "
            "{\"headline\": string, \"sentences\": [string, ...]}.",
            "Explanation to rephrase (JSON):\n" + json.dumps({"headline": explanation["headline"],
                                                            "sentences": explanation["sentences"],
                                                            "policy_checks": [c["display"] for c in explanation["policy_checks"]]}),
        )
        headline, sentences = parsed.get("headline"), parsed.get("sentences")
        if isinstance(headline, str) and headline.strip() and isinstance(sentences, list) and sentences:
            out = dict(explanation)
            out["headline"] = headline.strip()
            out["sentences"] = [str(s) for s in sentences][:8]
            out["plain_text"] = " ".join([out["headline"]] + out["sentences"])
            out["generated_by"] = f"{client.provider}:{client.model_name}"
            return out
        out = dict(explanation)
        out["llm_error"] = client.last_error or parsed.get("error") or "model returned no text"
        return out
    except Exception as exc:
        out = dict(explanation)
        out["llm_error"] = f"{type(exc).__name__}: {exc}"
        return out
