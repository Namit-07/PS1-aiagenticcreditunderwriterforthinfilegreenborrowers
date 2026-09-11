"""Evidence matching across documents (Team B)."""

from __future__ import annotations

from typing import Any


def numeric_close(a: float, b: float, tolerance: float = 0.02) -> bool:
    """True if |a - b| / max(|a|,|b|,1) <= tolerance."""
    try:
        denom = max(abs(float(a)), abs(float(b)), 1.0)
        return abs(float(a) - float(b)) / denom <= tolerance
    except Exception:
        return False


def match_field(extractions: list[dict[str, Any]], field_name: str, tolerance: float = 0.02) -> dict[str, Any]:
    """Match values extracted for the same field across sources."""
    vals = [e for e in extractions if e.get("field") == field_name and e.get("value") is not None]
    numerics = [float(e["value"]) for e in vals if isinstance(e.get("value"), (int, float))]
    if not numerics:
        texts = sorted({str(e.get("value")) for e in vals})
        return {"field": field_name, "value": texts[0] if len(texts) == 1 else None,
                "sources": [e.get("source_document") for e in vals],
                "in_tolerance": len(texts) <= 1, "count": len(vals)}
    lo, hi = min(numerics), max(numerics)
    base = max(abs(hi), abs(lo), 1.0)
    pct = (hi - lo) / base
    return {"field": field_name, "value": float(sum(numerics) / len(numerics)),
            "sources": [e.get("source_document") for e in vals],
            "in_tolerance": pct <= tolerance, "mismatch_percentage": round(pct, 4),
            "count": len(vals)}