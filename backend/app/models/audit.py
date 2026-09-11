"""Audit ORM model (Team A)."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.models._base import new_id, utcnow


class AuditEvent(Base):
    """Immutable audit event for a run (mirrored AI trace + backend actions)."""

    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(String, ForeignKey("underwriting_runs.id"), index=True)
    sequence: Mapped[int] = mapped_column(Integer, default=0)
    step: Mapped[str] = mapped_column(String)
    actor: Mapped[str] = mapped_column(String)
    timestamp: Mapped[str] = mapped_column(String, default=utcnow)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
