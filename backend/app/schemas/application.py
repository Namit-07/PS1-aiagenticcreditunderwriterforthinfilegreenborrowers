"""Pydantic schemas for applications (Team A) — mirrors shared/schemas/application.json."""

from pydantic import BaseModel, ConfigDict, Field


class ProductRequest(BaseModel):
    type: str
    amount: float = Field(gt=0)
    tenure_months: int = Field(gt=0, le=120)
    rate_annual: float = Field(ge=0, le=100)


class BorrowerView(BaseModel):
    ref_id: str
    age: int = Field(ge=16, le=100)
    location_tier: str
    full_name: str | None = None
    declared_monthly_income: float | None = Field(default=None, ge=0)
    employment_type: str | None = None


class LoanRequestView(BaseModel):
    amount: float = Field(gt=0)
    tenure_months: int = Field(gt=0, le=120)
    vehicle_price: float | None = Field(default=None, ge=0)
    down_payment: float | None = Field(default=None, ge=0)


class ApplicationCreate(BaseModel):
    product: ProductRequest
    borrower: BorrowerView
    loan_request: LoanRequestView


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str = "draft"
    product: ProductRequest
    borrower: BorrowerView
    loan_request: LoanRequestView
    latest_run_id: str | None = None
    latest_decision: str | None = None
    documents_count: int | None = None
    created_at: str | None = None
    updated_at: str | None = None


class UnderwriteRequest(BaseModel):
    policy_profile: str | None = None
