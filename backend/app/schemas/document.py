"""Pydantic schemas for documents (Team A)."""

from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: str
    application_id: str
    file_name: str
    category: str | None = None
    storage_key: str
    content_type: str | None = None
    size_bytes: int = 0
    text_preview: str | None = None
    ocr_confidence: float | None = None
    uploaded_at: str | None = None
