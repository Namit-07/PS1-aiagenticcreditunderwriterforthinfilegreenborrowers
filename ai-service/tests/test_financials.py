"""Deterministic financial engine tests (EMI / FOIR / LTV) — Team B."""

import math

import pytest

from app.financials import engine as fe


def test_monthly_rate():
    assert fe.monthly_rate(12.0) == pytest.approx(0.01)
    assert fe.monthly_rate(0.0) == 0.0
    with pytest.raises(ValueError):
        fe.monthly_rate(-1)


def test_emi_matches_textbook_formula():
    # P=100000, 12% p.a., 12 months -> 8884.88
    assert fe.emi(100000, 12.0, 12) == pytest.approx(8884.88, abs=0.01)
    # zero-rate loan is straight-line
    assert fe.emi(120000, 0.0, 12) == pytest.approx(10000.0)


def test_emi_rejects_bad_inputs():
    with pytest.raises(ValueError):
        fe.emi(-1, 10, 12)
    with pytest.raises(ValueError):
        fe.emi(1000, 10, 0)


def test_ltv_and_foir():
    assert fe.ltv_ratio(90000, 120000) == pytest.approx(0.75)
    assert fe.obligations_ratio(2500, 3000, 38900) == pytest.approx(5500 / 38900)
    assert fe.obligations_ratio(2500, 3000, 0) == 0.0
    with pytest.raises(ValueError):
        fe.ltv_ratio(1, 0)


def test_income_aggregates():
    series = [38500, 41000, 36200, 39800, 37900, 40100]
    assert fe.verified_monthly_income(series) == pytest.approx(39150.0)  # median
    vol = fe.income_volatility(series)
    assert 0 < vol < 0.1
    assert fe.income_stability(series) == pytest.approx(1 - vol)
    assert fe.verified_monthly_income([]) == 0.0


def test_compute_all_is_reproducible_and_snapshots_inputs():
    inputs = {"loan_amount": 90000, "vehicle_price": 120000, "annual_rate": 14.0, "tenure_months": 36,
              "existing_monthly_obligations": 2500,
              "monthly_incomes": [38500, 41000, 36200, 39800, 37900, 40100]}
    a = fe.compute_all(inputs)
    b = fe.compute_all(dict(inputs))
    assert a == b
    assert a["formula_version"] == fe.FORMULA_VERSION
    assert a["calculation_inputs"]["loan_amount"] == 90000
    assert a["ltv"] == pytest.approx(0.75)
    assert a["emi"] == pytest.approx(fe.emi(90000, 14.0, 36), abs=0.01)
    assert a["foir"] == pytest.approx((2500 + a["emi"]) / 39150, abs=1e-3)
    assert not math.isnan(a["income_volatility"])
