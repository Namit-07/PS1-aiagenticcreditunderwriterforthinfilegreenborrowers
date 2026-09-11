"""Borrower schema (Team B) — mirrors shared/schemas/application.json borrower object."""

from pydantic import BaseModel, Field


class Borrower(BaseModel):
    ref_id: str
    age: int = Field(ge=18)
    location_tier: str = Field(pattern=r"tier_[123]")


class BorrowerView(BaseModel):
    """Same shape as the frontend/backend borrower view."""

    ref_id: str
    age: int
    location_tier: str