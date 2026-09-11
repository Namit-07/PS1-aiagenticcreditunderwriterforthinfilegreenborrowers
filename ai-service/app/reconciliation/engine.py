"""Reconciliation engine (Team B).

Compares the same fact across independent sources. The LLM MAY help identify a
discrepancy, but every numerical discrepancy percentage is computed deterministically
here (the LLM never does the arithmetic).

Input ``facts`` is a dict of ``fact_name -> list[source_value]`` where each
source_value is ``{"value":..., "source": "bank_statement.pdf", "page": ...,
"confidence": ...}``.
"""

from __future__ import annotations

from typing import Any

REQUIRED_DOCUMENTS = ["kyc", "bank_statement", "dealer_invoice"]

# canonical mismatch types
NAME_MISMATCH = "NAME_MISMATCH"
ADDRESS_MISMATCH = "ADDRESS_MISMATCH"
INCOME_MISMATCH = "INCOME_MISMATCH"
VEHICLE_PRICE_MISMATCH = "VEHICLE_PRICE_MISMATCH"
LOAN_VS_INVOICE = "LOAN_VS_INVOICE"
EXISTING_OBLIGATIONS = "EXISTING_OBLIGATIONS"
DUPLICATE_DOCUMENT = "DUPLICATE_DOCUMENT"
MISSING_DOCUMENT = "MISSING_DOCUMENT"


def _sev(pct: float) -> str:
    return "HIGH" if pct >= 0.15 else ("MEDIUM" if pct >= 0.05 else "LOW")


def _text_sources(items: list[dict[str, Any]]) -> list[str]:
    return sorted({str(i.get("source", "?")) for i in items})


def _text_mismatch(fact: str, items: list[dict[str, Any]], kind: str) -> dict[str, Any] | None:
    vals = [str(i.get("value", "")).strip().lower() for i in items if i.get("value")]
    unique = sorted(set(vals))
    if len(unique) <= 1:
        return None
    return {
        "type": kind,
        "severity": "HIGH",
        "description": f"{fact} differs across documents",
        "documents": _text_sources(items),
        "evidence": [str(i.get("value")) for i in items],
        "impact": f"Confidence in {fact.lower()} is reduced; may require human verification.",
    }


def _numeric_mismatch(
    fact: str,
    items: list[dict[str, Any]],
    kind: str,
) -> dict[str, Any] | None:
    numerics = [float(i["value"]) for i in items if isinstance(i.get("value"), (int, float))]
    if len(numerics) < 2:
        return None
    lo, hi = min(numerics), max(numerics)
    base = max(abs(hi), abs(lo), 1.0)
    pct = (hi - lo) / base
    if pct < 0.001:
        return None
    return {
        "type": kind,
        "severity": _sev(pct),
        "description": f"{fact} differs across documents by {pct:.1%}",
        "documents": _text_sources(items),
        "evidence": [str(v) for v in numerics],
        "impact": f"Discrepancy in {fact.lower()} of {pct:.1%} ({lo} vs {hi}).",
        "mismatch_percentage": round(pct, 4),
    }


def income_mismatch_percentage(items: list[dict[str, Any]]) -> float | None:
    """Deterministic discrepancy between declared and verified income sources."""
    numerics = [float(i["value"]) for i in items if isinstance(i.get("value"), (int, float))]
    if len(numerics) < 2:
        return None
    lo, hi = min(numerics), max(numerics)
    base = max(abs(hi), abs(lo), 1.0)
    return round((hi - lo) / base, 4)


def reconcile(facts: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    """Run all reconciliation checks.

    Returns ``{"items": [...], "income_mismatch_percentage": float|None,
    "has_high_severity": bool, "human_review_mismatch_threshold": int}``.
    """
    items: list[dict[str, Any]] = []
    conf = policy.get("mismatch", {})

    if "full_name" in facts:
        m = _text_mismatch("Full name", facts["full_name"], NAME_MISMATCH)
        if m:
            items.append(m)
    if "address" in facts:
        m = _text_mismatch("Address", facts["address"], ADDRESS_MISMATCH)
        if m:
            items.append(m)

    if "monthly_income" in facts:
        m = _numeric_mismatch("Monthly income", facts["monthly_income"], INCOME_MISMATCH)
        if m:
            items.append(m)

    if "vehicle_price" in facts:
        m = _numeric_mismatch(
            "Vehicle price", facts["vehicle_price"], VEHICLE_PRICE_MISMATCH
        )
        if m:
            items.append(m)

    if "loan_amount" in facts and "vehicle_price" in facts:
        loans = [float(i["value"]) for i in facts["loan_amount"] if isinstance(i.get("value"), (int, float))]
        prices = [float(i["value"]) for i in facts["vehicle_price"] if isinstance(i.get("value"), (int, float))]
        if loans and prices and max(prices) > 0:
            ltv = min(loans) / max(prices)
            if ltv > float(conf.get("ltv_warn_threshold", 0.85)):
                items.append(
                    {
                        "type": LOAN_VS_INVOICE,
                        "severity": "MEDIUM",
                        "description": f"Loan amount is {ltv:.1%} of vehicle invoice value",
                        "documents": sorted(set(_text_sources(facts["loan_amount"]) + _text_sources(facts["vehicle_price"]))),
                        "evidence": [f"loan {min(loans)}", f"price {max(prices)}"],
                        "impact": "Loan size relative to vehicle value is high.",
                        "mismatch_percentage": round(ltv, 4),
                    }
                )

    required = list(policy.get("required_documents") or REQUIRED_DOCUMENTS)
    missing = [d for d in required if d not in facts.get("documents_available", [])]
    for doc in missing:
        items.append(
            {
                "type": MISSING_DOCUMENT,
                "severity": "HIGH",
                "description": f"Required document missing: {doc}",
                "documents": [],
                "evidence": [],
                "impact": "Cannot verify key facts without this document.",
            }
        )

    has_high = any(i["severity"] == "HIGH" for i in items)
    return {
        "items": items,
        "income_mismatch_percentage": income_mismatch_percentage(facts.get("monthly_income", [])),
        "has_high_severity": has_high,
        "human_review_mismatch_threshold": int(conf.get("human_review_mismatch_threshold", 1)),
    }