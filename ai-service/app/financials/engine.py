"""Deterministic Financial Compute Engine (Team B).

Financial numbers (EMI, FOIR, LTV, obligations, income aggregates) are computed with
deterministic, unit-tested Python functions. The LLM is NEVER the source of these
values — the model only reads the outputs.

Everything returns the exact inputs used (``calculation_inputs``) so results are
reproducible for audit and replay.
"""

from __future__ import annotations

import statistics
from typing import Any

FORMULA_VERSION = "v1"
MONTHS_PER_YEAR = 12


def monthly_rate(annual_rate: float) -> float:
    """Convert an annual % interest rate to a monthly decimal rate."""
    if annual_rate < 0:
        raise ValueError("annual_rate cannot be negative")
    if annual_rate == 0:
        return 0.0
    return annual_rate / (100.0 * MONTHS_PER_YEAR)


def emi(principal: float, annual_rate: float, tenure_months: int) -> float:
    """Equated Monthly Installment.

    EMI = P * r * (1 + r)^n / ((1 + r)^n - 1)
    """
    if principal < 0:
        raise ValueError("principal cannot be negative")
    if not isinstance(tenure_months, int) or tenure_months <= 0:
        raise ValueError("tenure_months must be a positive integer")

    r = monthly_rate(annual_rate)
    if r == 0:
        return principal / tenure_months
    factor = (1.0 + r) ** tenure_months
    return principal * r * factor / (factor - 1.0)


def ltv_ratio(loan_amount: float, vehicle_price: float) -> float:
    """Loan-to-Value ratio (0..1+)."""
    if vehicle_price <= 0:
        raise ValueError("vehicle_price must be positive")
    return loan_amount / vehicle_price


def obligations_ratio(
    existing_monthly_obligations: float,
    proposed_emi: float,
    verified_monthly_income: float,
) -> float:
    """Fixed Obligation to Income Ratio = (obligations + EMI) / income."""
    if verified_monthly_income <= 0:
        return 0.0
    return (existing_monthly_obligations + proposed_emi) / verified_monthly_income


def coef_of_variation(values: list[float]) -> float:
    """Coefficient of variation (std / mean). 0.0 when degenerate."""
    if not values:
        return 0.0
    try:
        mean = statistics.fmean(values) if hasattr(statistics, "fmean") else statistics.mean(values)
    except statistics.StatisticsError:
        return 0.0
    if mean <= 0:
        return 0.0
    try:
        std = statistics.pstdev(values)
    except statistics.StatisticsError:
        return 0.0
    return std / mean


def verified_monthly_income(monthly_incomes: list[float]) -> float:
    """Robust monthly income estimate = median of reconciled incomes."""
    if not monthly_incomes:
        return 0.0
    return float(statistics.median([max(0.0, i) for i in monthly_incomes]))


def income_volatility(monthly_incomes: list[float]) -> float:
    """Income volatility as coefficient of variation."""
    return coef_of_variation(monthly_incomes)


def income_stability(monthly_incomes: list[float]) -> float:
    """Income stability = 1 - volatility (clamped 0..1)."""
    return max(0.0, min(1.0, 1.0 - income_volatility(monthly_incomes)))


def loan_to_income(loan_amount: float, verified_monthly_income: float) -> float:
    """Loan amount as a multiple of annual verified income."""
    if verified_monthly_income <= 0:
        return 0.0
    return loan_amount / (verified_monthly_income * MONTHS_PER_YEAR)


def emi_to_income(monthly_emi: float, verified_monthly_income: float) -> float:
    """EMI-to-income ratio."""
    if verified_monthly_income <= 0:
        return 0.0
    return monthly_emi / verified_monthly_income


def compute_all(inputs: dict[str, Any]) -> dict[str, Any]:
    """Run the full deterministic financial computation.

    Expected ``inputs`` keys:
        loan_amount, vehicle_price, annual_rate, tenure_months,
        existing_monthly_obligations, monthly_incomes (list), down_payment (optional)

    Returns ``emi``, ``foir``, ``ltv`` and derived aggregates plus the
    ``calculation_inputs`` snapshot and ``formula_version``.
    """
    loan_amount = float(inputs.get("loan_amount", 0.0))
    vehicle_price = float(inputs.get("vehicle_price", 0.0) or inputs.get("loan_amount", 0.0))
    annual_rate = float(inputs.get("annual_rate", 0.0))
    tenure_months = int(inputs.get("tenure_months", 36))
    existing_obligations = float(inputs.get("existing_monthly_obligations", 0.0))
    monthly_incomes = [float(i) for i in (inputs.get("monthly_incomes") or [])]

    emi_value = emi(loan_amount, annual_rate, tenure_months)
    income = verified_monthly_income(monthly_incomes)
    foir_value = obligations_ratio(existing_obligations, emi_value, income)
    ltv_value = ltv_ratio(loan_amount, vehicle_price)

    return {
        "emi": round(emi_value, 2),
        "foir": round(foir_value, 4),
        "ltv": round(ltv_value, 4),
        "existing_obligations": round(existing_obligations, 2),
        "verified_income": round(income, 2),
        "income_stability": round(income_stability(monthly_incomes), 4),
        "income_volatility": round(income_volatility(monthly_incomes), 4),
        "loan_to_income": round(loan_to_income(loan_amount, income), 4),
        "emi_to_income": round(emi_to_income(emi_value, income), 4),
        "down_payment": round(float(inputs.get("down_payment", 0.0) or 0.0), 2),
        "calculation_inputs": {
            "loan_amount": round(loan_amount, 2),
            "vehicle_price": round(vehicle_price, 2),
            "annual_rate": annual_rate,
            "tenure_months": tenure_months,
            "existing_monthly_obligations": round(existing_obligations, 2),
            "monthly_incomes": [round(i, 2) for i in monthly_incomes],
        },
        "formula_version": FORMULA_VERSION,
    }