"""Evidence citation helpers (Team B).

Citations let the UI and audit trace point back to the exact source document text.
"""

from typing import Any


def build_citation(document_id: str, text_snippet: str, page: int | None = None) -> dict[str, Any]:
    """Construct a citation object per shared/schemas/evidence.json."""
    return {"document_id": document_id, "text_snippet": text_snippet, "page": page}


def attach_citation(evidence: dict[str, Any], citation: dict[str, Any]) -> dict[str, Any]:
    """Attach a citation to an evidence item and return the updated item."""
    evidence.setdefault("citations", []).append(citation)
    return evidence