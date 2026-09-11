"""Application ORM model (Team A)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.models._base import dumps, loads, new_id, utcnow


class Application(Base):
    """A credit application (shared/schemas/application.json)."""

    __tablename__ = "applications"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    status: Mapped[str] = mapped_column(String, default="draft", index=True)
    product_json: Mapped[str] = mapped_column(Text, default="{}")
    borrower_json: Mapped[str] = mapped_column(Text, default="{}")
    loan_request_json: Mapped[str] = mapped_column(Text, default="{}")
    latest_run_id: Mapped[str | None] = mapped_column(String, index=True)
    latest_decision: Mapped[str | None] = mapped_column(String)
    created_by: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[str] = mapped_column(String, default=utcnow)
    updated_at: Mapped[str] = mapped_column(String, default=utcnow, onupdate=utcnow)

    @property
    def product(self) -> dict[str, Any]:
        return loads(self.product_json)

    @property
    def borrower(self) -> dict[str, Any]:
        return loads(self.borrower_json)

    @property
    def loan_request(self) -> dict[str, Any]:
        return loads(self.loan_request_json)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "status": self.status,
            "product": self.product,
            "borrower": self.borrower,
            "loan_request": self.loan_request,
            "latest_run_id": self.latest_run_id,
            "latest_decision": self.latest_decision,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any], created_by: str | None = None) -> "Application":
        return cls(
            status=str(payload.get("status") or "draft"),
            product_json=dumps(payload.get("product") or {}),
            borrower_json=dumps(payload.get("borrower") or {}),
            loan_request_json=dumps(payload.get("loan_request") or {}),
            created_by=created_by,
        )
