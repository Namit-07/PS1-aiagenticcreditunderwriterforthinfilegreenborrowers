"""Risk model evaluation routes — Team A (proxies the AI-service /risk/metrics).

GET /risk/metrics  -> XGBoost/failure-fallback evaluation scores + confusion matrix.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from app.services import ai_service

router = APIRouter()


@router.get("/metrics")
async def risk_metrics(
    threshold: float = Query(0.50, ge=0.0, le=1.0),
    n: int = Query(800, ge=100, le=5000),
) -> dict[str, Any]:
    """Confusion matrix, accuracy, precision, recall/sensitivity, specificity, F1, AUC, ROC."""
    return await ai_service.get_risk_metrics(threshold=threshold, n=n)