"""ORM models (Team A). Importing this package registers every table on ``Base``.

14 tables:
  users, applications, documents, underwriting_runs, evidence, decisions, audit_events,
  human_reviews, what_if_runs, credit_memos, reconciliation_items, financial_metrics,
  risk_scores, replay_snapshots
"""

from app.models.application import Application
from app.models.audit import AuditEvent
from app.models.decision import Decision
from app.models.document import Document
from app.models.evidence import Evidence
from app.models.underwriting import (
    CreditMemo,
    FinancialMetric,
    HumanReview,
    ReconciliationItem,
    ReplaySnapshot,
    RiskScore,
    UnderwritingRun,
    WhatIfRun,
)
from app.models.user import User

__all__ = [
    "Application", "AuditEvent", "Decision", "Document", "Evidence", "CreditMemo", "FinancialMetric",
    "HumanReview", "ReconciliationItem", "ReplaySnapshot", "RiskScore", "UnderwritingRun", "WhatIfRun",
    "User",
]
