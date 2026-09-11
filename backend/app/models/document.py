"""Document ORM model (Team A)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.models._base import new_id, utcnow


class Document(Base):
    """Metadata for an uploaded borrower document (bytes live in storage)."""

    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    application_id: Mapped[str] = mapped_column(String, ForeignKey("applications.id"), index=True)
    file_name: Mapped[str] = mapped_column(String)
    category: Mapped[str | None] = mapped_column(String)
    storage_key: Mapped[str] = mapped_column(String)
    content_type: Mapped[str | None] = mapped_column(String)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    text_preview: Mapped[str | None] = mapped_column(Text)
    extracted_text: Mapped[str | None] = mapped_column(Text)
    ocr_confidence: Mapped[str | None] = mapped_column(String)
    uploaded_by: Mapped[str | None] = mapped_column(String)
    uploaded_at: Mapped[str] = mapped_column(String, default=utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "application_id": self.application_id,
            "file_name": self.file_name,
            "category": self.category,
            "storage_key": self.storage_key,
            "content_type": self.content_type,
            "size_bytes": self.size_bytes,
            "text_preview": self.text_preview,
            "ocr_confidence": float(self.ocr_confidence) if self.ocr_confidence else None,
            "uploaded_at": self.uploaded_at,
        }
