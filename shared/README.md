# Shared Contracts

This directory is the **single source of truth** for the API/data contract between
Team A (frontend + backend) and Team B (AI service). Both teams should reference these
schemas rather than inventing their own field names.

## Contents

| File                      | Purpose                                                            |
|---------------------------|-------------------------------------------------------------------|
| `schemas/application.json`| Credit application payload (borrower, loan, product, flag)         |
| `schemas/evidence.json`   | Extracted evidence items tied to source documents                  |
| `schemas/financials.json` | Deterministic financial outputs (EMI, FOIR, LTV, income, etc.)     |
| `schemas/decision.json`   | Underwriting decision + reasons + confidence                       |
| `schemas/audit_event.json`| Audit trace / event log entry                                      |
| `reason_codes.yaml`       | Canonical decline / refer / human-review reason codes              |

## Conventions

- These are **human-readable single source of truth** definitions — whether a given team validates them with
  Pydantic (Python) or Zod (TypeScript) is up to that team.
- The **AI service** produces `evidence`, `financials` and `decision` shapes.
- The **backend** persists the application, documents, runs, and audit events.
- The **frontend** consumes the same shapes from backend REST endpoints.

## Governance Rule

- Financial numbers are **always** computed deterministically by the backend/AI financial
  logic — never authored by the LLM. The LLM only extracts/annotates/reconciles.