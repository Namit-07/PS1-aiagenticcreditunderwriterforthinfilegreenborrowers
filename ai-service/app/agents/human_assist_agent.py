"""Human-assist agent — human-in-the-loop support (Team B).

Suggests concrete review questions for low-confidence / mismatched fields and folds a
reviewer's action into run state. All decisions are persisted via the Store.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class HumanAssistAgent:
    """Helpers for human-in-the-loop decision flow."""

    async def suggest_review_questions(self, run_state: dict[str, Any]) -> list[str]:
        """Given low-confidence areas, propose questions/verifications for the reviewer."""
        questions: list[str] = []
        for item in run_state.get("low_confidence", []) or []:
            field = item.get("field", "?")
            questions.append(
                f"Verify '{field}' (confidence {item.get('confidence')}) against "
                f"{item.get('source_document', 'source document')}: accept, correct, or reject?"
            )
        for item in (run_state.get("reconciliation", {}) or {}).get("items", []) or []:
            questions.append(
                f"Reconcile {item.get('type')}: {item.get('description')} — which source is authoritative?"
            )
        if not questions:
            questions.append("Confirm extracted facts look correct before resuming the workflow.")
        try:
            if not run_state.get("mock", True):
                from app.llm.client import LLMClient
                from app.llm.prompts import SYSTEM_RECONCILE

                parsed = await LLMClient().complete_json(
                    SYSTEM_RECONCILE,
                    "Review context (JSON, ≤1500 chars): " + str(run_state)[:1500],
                )
                extra = parsed.get("questions")
                if isinstance(extra, list) and extra:
                    questions.extend(str(q) for q in extra[:5])
        except Exception:
            pass
        return questions

    async def apply_reviewer_override(self, run_state: dict[str, Any], decision: str, notes: str) -> dict[str, Any]:
        """Fold a reviewer's decision/notes into run state."""
        updated = dict(run_state)
        updated["reviewer_decision"] = decision
        updated["reviewer_notes"] = notes
        history = list(updated.get("review_history", []) or [])
        history.append({"decision": decision, "notes": notes})
        updated["review_history"] = history
        return updated