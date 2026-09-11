"""Policy-as-config engine (Team B).

Policies live in YAML files (``default`` / ``conservative`` / ``aggressive``) and are
not hardcoded. Each underwriting run records the exact policy name/version/configuration
that was applied, so future policy changes never rewrite history.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:  # PyYAML when available
    import yaml  # type: ignore

    _HAS_YAML = True
except Exception:  # pragma: no cover
    _HAS_YAML = False

from app.utils.mini_yaml import parse as _mini_parse

# Reason codes that reflect a hard policy failure (blocker) vs. warning.
_BLOCKER_CODES = {
    "HIGH_FOIR",
    "HIGH_LTV",
    "LOW_AGE",
    "HIGH_EXISTING_OBLIGATIONS",
    "HIGH_RISK_SCORE",
    "LOAN_EXCEEDS_ELIGIBLE",
}
_WARNING_CODES = {
    "HIGH_FOIR",
    "HIGH_LTV",
    "INCOME_MISMATCH",
    "LOW_DOCUMENT_CONFIDENCE",
    "LOW_OVERALL_CONFIDENCE",
}


def load_policy(path: str | Path) -> dict[str, Any]:
    """Load and normalise a policy file into a plain dict."""
    p = Path(path)
    raw = p.read_text(encoding="utf-8")
    if _HAS_YAML:
        data = yaml.safe_load(raw) or {}
    else:
        data = _mini_parse(raw)
    return data or {}


def policy_metadata(policy: dict[str, Any]) -> dict[str, Any]:
    """Return stable identification + the exact config snapshot used by a run."""
    return {
        "name": str(policy.get("profile", "default")),
        "version": str(policy.get("version", "1.0")),
        "config": json.dumps(policy, sort_keys=True, default=str),
    }


def get_limits(policy: dict[str, Any]) -> dict[str, Any]:
    return policy.get("limits", {})


def get_confidence_limits(policy: dict[str, Any]) -> dict[str, Any]:
    return policy.get("confidence", {})


def get_mismatch_config(policy: dict[str, Any]) -> dict[str, Any]:
    return policy.get("mismatch", {})


def financial_violations(financials: dict[str, Any], policy: dict[str, Any]) -> list[dict[str, Any]]:
    """Evaluate deterministic financials against policy limits.

    Returns a list of violation dicts, each: {code, severity, message, field}.
    """
    limits = get_limits(policy)
    violations: list[dict[str, Any]] = []
    foir_max = float(limits.get("foir_max", 0.5))
    ltv_max = float(limits.get("ltv_max", 0.85))

    foir = float(financials.get("foir", 0.0))
    ltv = float(financials.get("ltv", 0.0))

    if foir > foir_max:
        violations.append(
            {
                "code": "HIGH_FOIR",
                "severity": "blocker",
                "message": f"FOIR {foir:.2%} exceeds policy limit {foir_max:.2%}",
                "field": "foir",
            }
        )
    if ltv > ltv_max:
        violations.append(
            {
                "code": "HIGH_LTV",
                "severity": "blocker",
                "message": f"LTV {ltv:.2%} exceeds policy limit {ltv_max:.2%}",
                "field": "ltv",
            }
        )
    return violations


def confidence_violations(confidence: dict[str, Any], policy: dict[str, Any]) -> list[dict[str, Any]]:
    """Evaluate aggregate confidence against policy thresholds."""
    conf_limits = get_confidence_limits(policy)
    violations: list[dict[str, Any]] = []
    overall = float(confidence.get("overall", 1.0))
    overall_min = float(conf_limits.get("overall_min", 0.55))
    if overall < overall_min:
        violations.append(
            {
                "code": "LOW_OVERALL_CONFIDENCE",
                "severity": "warning",
                "message": f"Overall confidence {overall:.2f} below threshold {overall_min:.2f}",
                "field": "overall_confidence",
            }
        )
    return violations

def application_violations(application: dict[str, Any], policy: dict[str, Any]) -> list[dict[str, Any]]:
    """Evaluate borrower / loan-request facts (age, tenure) against policy limits."""
    limits = get_limits(policy)
    violations: list[dict[str, Any]] = []
    borrower = (application or {}).get("borrower", {}) or {}
    lr = (application or {}).get("loan_request", {}) or {}
    prod = (application or {}).get("product", {}) or {}
    age = borrower.get("age")
    min_age = int(limits.get("min_age", 21))
    if age is not None:
        try:
            if int(age) < min_age:
                violations.append(
                    {
                        "code": "LOW_AGE",
                        "severity": "blocker",
                        "message": f"Borrower age {int(age)} is below policy minimum {min_age}",
                        "field": "age",
                    }
                )
        except (TypeError, ValueError):
            pass
    tenure = lr.get("tenure_months", prod.get("tenure_months"))
    max_tenure = int(limits.get("max_tenure_months", 60))
    if tenure is not None:
        try:
            if int(tenure) > max_tenure:
                violations.append(
                    {
                        "code": "MAX_TENURE_EXCEEDED",
                        "severity": "blocker",
                        "message": f"Tenure {int(tenure)} months exceeds policy maximum {max_tenure}",
                        "field": "tenure_months",
                    }
                )
        except (TypeError, ValueError):
            pass
    return violations


def income_violations(financials: dict[str, Any], policy: dict[str, Any]) -> list[dict[str, Any]]:
    """No verified income means FOIR cannot be computed -> hard stop."""
    if float(financials.get("verified_income", 0.0) or 0.0) <= 0:
        return [
            {
                "code": "NO_VERIFIED_INCOME",
                "severity": "blocker",
                "message": "No verified monthly income could be established from evidence",
                "field": "verified_income",
            }
        ]
    return []


def required_documents(policy: dict[str, Any]) -> list[str]:
    """Document kinds the policy insists on (flags.require_<kind>)."""
    flags = policy.get("flags", {}) or {}
    defaults = {"kyc": True, "bank_statement": True, "dealer_invoice": True, "platform_earnings": False}
    return [k for k, d in defaults.items() if bool(flags.get(f"require_{k}", d))]
