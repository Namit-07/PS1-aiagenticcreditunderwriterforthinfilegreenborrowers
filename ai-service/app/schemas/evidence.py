"""Evidence schema (Team B) — mirrors shared/schemas/evidence.json."""

from typing import Any

from pydantic import BaseModel, Field


class Citation(BaseModel):
    document_id: str
    text_snippet: str
    page: int | None = None


class EvidenceItem(BaseModel):
    id: str
    source_document_id: str
    category: str
    field_name: str
    value: Any = None
    unit: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    page_ref: int | None = None
    reconciled: bool = False
    citations: list[Citation] = []