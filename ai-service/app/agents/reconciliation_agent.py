"""Reconciliation agent — cross-checks evidence across documents (Team B)."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.reconciliation import engine as recon_engine


class ReconciliationAgent:
    """Detect and resolve mismatches between independent evidence sources."""

    def __init__(self) -> None:
        self.mismatches: list[dict[str, Any]] = []

    async def run(
        self, evidence: list[dict[str, Any]], policy: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Reconcile extracted evidence -> {reconciled_fields, mismatches, ...}.

        ``policy`` supplies mismatch tolerances and the required document list; the
        arithmetic itself lives in :mod:`app.reconciliation.engine`.
        """
        from app.policy.engine import required_documents

        policy = policy or {}
        facts: dict[str, Any] = {}
        docs: set[str] = set()
        for e in evidence or []:
            if e.get("kind"):
                docs.add(str(e["kind"]))
            if e.get("value") is None or e.get("review_status") == "rejected":
                continue
            if isinstance(e.get("value"), list):
                continue  # series (e.g. bank_credits) are not reconciled as single facts
            facts.setdefault(e.get("field", "monthly_income"), []).append(
                {
                    "value": e.get("value"),
                    "source": e.get("source_document", "?"),
                    "page": e.get("page"),
                    "confidence": e.get("confidence", 0.0),
                }
            )
        facts["documents_available"] = sorted(docs)
        result = recon_engine.reconcile(
            facts,
            {"mismatch": policy.get("mismatch", {}) or {},
             "required_documents": required_documents(policy) if policy else None},
        )
        self.mismatches = result.get("items", [])
        return {
            "reconciled_fields": sorted(facts.keys()),
            "mismatches": self.mismatches,
            "income_mismatch_percentage": result.get("income_mismatch_percentage"),
            "has_high_severity": result.get("has_high_severity", False),
            "documents_available": facts["documents_available"],
            "overall_confidence": 0.0,
        }

    def _new_mismatch(self, field_name: str, values: list[Any]) -> dict[str, Any]:
        return {
            "id": str(uuid4()),
            "field": field_name,
            "values": values,
            "resolved": False,
        }