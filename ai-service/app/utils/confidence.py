"""Confidence scoring helpers (Team B).

Extracted fields carry a confidence in [0, 1]. Low confidence on *critical* fields
must trigger HUMAN REVIEW so the workflow genuinely pauses for a reviewer.
"""

from __future__ import annotations

from typing import Any

HIGH = 0.85
MEDIUM = 0.60

# Fields whose low confidence forces human review.
CRITICAL_FIELDS = [
    "identity",
    "full_name",
    "monthly_income",
    "loan_amount",
    "vehicle_price",
    "existing_monthly_obligations",
    "bank_credits",
    "employment_income",
    "platform_income",
]


def classify(confidence: float) -> str:
    """Bucket a confidence score: high / medium / low."""
    if confidence >= HIGH:
        return "high"
    if confidence >= MEDIUM:
        return "medium"
    return "low"


def aggregate_confidence(evidence: list[dict[str, Any]]) -> float:
    """Combine per-item confidences into an overall score (simple mean)."""
    if not evidence:
        return 0.0
    return sum(float(e.get("confidence", 0.0)) for e in evidence) / len(evidence)


def low_confidence_fields(fields: dict[str, float], threshold: float = MEDIUM) -> list[str]:
    """Field names whose confidence is below the threshold."""
    return [name for name, conf in fields.items() if float(conf) < threshold]


# Backward-compatible alias
def low_confidence(fields: dict[str, Any], threshold: float = MEDIUM) -> list[str]:
    return low_confidence_fields(fields, threshold)


def critical_low_confidence(
    fields: dict[str, float], threshold: float = MEDIUM
) -> list[dict[str, Any]]:
    """Return critical fields that fall below the confidence threshold.

    Each entry: {field, confidence, threshold, requires_human_review: True}.
    """
    out: list[dict[str, Any]] = []
    for name in CRITICAL_FIELDS:
        if name in fields and float(fields[name]) < threshold:
            out.append(
                {
                    "field": name,
                    "confidence": round(float(fields[name]), 4),
                    "threshold": threshold,
                    "requires_human_review": True,
                }
            )
    return out