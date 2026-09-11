"""Financials schema (Team B) — mirrors shared/schemas/financials.json.

Financial values are computed deterministically by the financial engine; the LLM never
authors these numbers.
"""

from pydantic import BaseModel, Field


class Financials(BaseModel):
    monthly_income: float = Field(ge=0)
    total_monthly_obligations: float = Field(ge=0)
    monthly_emi: float = Field(ge=0)
    foir: float = Field(ge=0.0, le=1.0)
    ltv: float = Field(ge=0.0, le=1.0)
    effective_rate_nominal: float | None = None