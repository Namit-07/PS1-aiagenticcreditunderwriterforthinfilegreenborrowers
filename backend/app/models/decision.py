"""Decision ORM model (Team A)."""

from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.models._base import new_id, utcnow


class Decision(Base):
    """Final/override decision for a run (append-only history)."""

    __tablename__ = "decisions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(String, ForeignKey("underwriting_runs.id"), index=True)
    decision: Mapped[str] = mapped_column(String)
    confidence: Mapped[float | None] = mapped_column(Float)
    reasons_json: Mapped[str] = mapped_column(Text, default="[]")
    decided_by: Mapped[str] = mapped_column(String, default="ai-service")
    is_override: Mapped[int] = mapped_column(Integer, default=0)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String, default=utcnow)
