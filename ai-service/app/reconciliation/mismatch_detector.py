"""Mismatch detection for reconciliation (Team B)."""

from __future__ import annotations

from typing import Any


def detect_mismatches(reconciled: dict[str, Any]) -> list[dict[str, Any]]:
    """Return mismatch records from engine.reconcile() output items."""
    return list(reconciled.get("items", []) or [])


def flag_for_human_review(mismatches: list[dict[str, Any]], threshold: int = 1) -> bool:
    """True when HIGH-severity mismatches meet/exceed the threshold."""
    high = sum(1 for m in mismatches if str(m.get("severity", "")).upper() == "HIGH")
    return high >= max(1, threshold)