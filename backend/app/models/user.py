"""User ORM model (Team A)."""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.models._base import new_id, utcnow


class User(Base):
    """Application user (underwriter / reviewer / admin).

    Authenticated via demo login or Supabase Auth; this table stores profile metadata.
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String)
    role: Mapped[str] = mapped_column(String, default="underwriter")
    supabase_uid: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[str] = mapped_column(String, default=utcnow)
    last_login_at: Mapped[str | None] = mapped_column(String)
