"""Evidence ORM model (Team A)."""

from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.models._base import new_id


class Evidence(Base):
    """Persisted extracted/reconciled evidence for an underwriting run (mirror)."""

    __tablename__ = "evidence"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(String, ForeignKey("underwriting_runs.id"), index=True)
    document_ref: Mapped[str | None] = mapped_column(String)
    field_name: Mapped[str] = mapped_column(String)
    value_json: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    page: Mapped[int | None] = mapped_column(Integer)
    evidence_text: Mapped[str | None] = mapped_column(Text)
    review_status: Mapped[str] = mapped_column(String, default="auto")
