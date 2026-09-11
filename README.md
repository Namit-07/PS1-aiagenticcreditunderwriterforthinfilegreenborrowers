# Verdant — AI Agentic Credit Underwriter for Thin-File Green Borrowers

Verdant underwrites small green-asset loans (EV two/three-wheelers, solar) for borrowers who have
**no formal credit history** but plenty of alternative evidence: gig-platform payouts, bank
statements, KYC and dealer invoices. It reads the documents, cross-checks what they say, computes
affordability deterministically, applies an explicit credit policy, pauses for a human whenever the
evidence is weak, and produces a decision that is **explained in numbers and in words, replayable
and exportable as a credit memo**.

The pipeline is strictly **Evidence → Reconciliation → Compute → Policy → Decision → Proof**.
The language model labels, summarises and explains; it never produces a financial number.

---

## What it does

| Capability | How |
|---|---|
| **Typed extraction** | KYC, bank statement, dealer invoice and platform-earnings documents are parsed into a strict schema. Every fact carries `{value, confidence, source_document, page, evidence}`; anything unreadable is `null`, never guessed. Text, PDF (PyMuPDF) and scanned images (Tesseract OCR) are supported. |
| **Deterministic compute** | EMI, FOIR, LTV, obligations, income volatility and stability are computed in versioned Python (`formula_version: v1`). Replay re-executes the run byte-for-byte and diffs it. |
| **Cross-document reconciliation** | Declared vs credited income, name and address drift, application price vs invoice, loan vs invoice, and missing documents are flagged with severity bands and turned into reason codes. |
| **Policy as config** | Three YAML profiles (`default`, `conservative`, `aggressive`) hold every cut-off. They are loaded fresh on each run, so editing a limit takes effect on the next run with no restart. The exact snapshot used is stored on every run. |
| **Assist mode (human in the loop)** | A critical field below the confidence threshold pauses the run in the database. A reviewer accepts, corrects or rejects each field (with a note and an optional decision override) and the run resumes from saved state. Nothing proceeds until every flagged field is reviewed. |
| **Risk signal + SHAP** | An XGBoost model (trained on synthetic data; exact deterministic fallback when the package is absent) gives a secondary risk score. A SHAP layer reports per-feature contributions with `base_value + Σφ = score`, and a plain-language explanation pairs the policy margins that actually decided the outcome with those drivers. |
| **Audit trail & credit memo** | Every node writes a trace event with inputs, outputs and model/policy/formula versions. A credit memo separates facts, calculations, model signal, AI reasoning, policy, human overrides and the decision; a PDF is rendered automatically the moment a run completes. |
| **What-if & path to approval** | Scenarios run on an immutable copy of the run. For every **declined** file the service automatically searches longer tenures and smaller tickets and reports the smallest change that flips the decision to approved. |
| **Gemini narrative (free tier)** | With a `GEMINI_API_KEY`, Gemini writes the memo's executive summary, the borrower-facing explanation and rephrases the decision explanation from the verified numbers only. Without a key a deterministic template is used; model errors or rate limits fall back to it automatically. |

---

## Architecture

```
Next.js 15 (frontend, :3000)
   │  REST
   ▼
FastAPI backend (:8000)  — applications, documents, auth, dashboard, memo PDF, mirrors every run
   │  REST (shared contract)
   ▼
FastAPI AI service (:8100) — 10-node underwriting pipeline, policies, risk model, SHAP, what-if
   │  optional
   ▼
Gemini (REST, free tier)
```

Three independently runnable services, one shared contract (`shared/schemas/*.json`,
`shared/reason_codes.yaml`). The AI service owns the workflow and is replaceable behind its REST
API; the backend owns the application database and never contains AI logic; the frontend talks only
to the backend.

### The ten pipeline nodes

`classification → extraction → confidence_validation → reconciliation → deterministic_compute →
xgboost_risk → risk_reasoning → decision_policy → explanation → audit`

State is persisted after every node, which is what makes pause/resume, replay and what-if real
rather than UI tricks. `confidence_validation` is the human gate.

### Decision matrix

| Condition | Outcome |
|---|---|
| Any **blocker** reason (`HIGH_FOIR`, `HIGH_LTV`, `LOW_AGE`, `MAX_TENURE_EXCEEDED`, `NO_VERIFIED_INCOME`) | `declined` (+ automatic path to approval) |
| Any **warning** reason (`INCOME_MISMATCH`, `NAME_MISMATCH`, `ADDRESS_MISMATCH`, `MISSING_DOCUMENT`, `LOW_OVERALL_CONFIDENCE`, …) | `referred` to a human |
| Critical field below the confidence threshold | run pauses as `awaiting_human` (`human_review`) |
| Otherwise | `approved` |

Reason codes and severities are the shared contract in `shared/reason_codes.yaml`.

---

## Repository layout

```
frontend/      Next.js 15 + TypeScript + Tailwind ("Verdant" design system), 14 screens
backend/       FastAPI + SQLAlchemy; applications, documents, auth, dashboard, memo PDF, run mirror
ai-service/    FastAPI; agents, extraction/OCR, reconciliation, financial engine, policy engine,
               risk model + SHAP, workflow, LLM client, tests
shared/        JSON schemas + reason codes (the contract between services)
sample-data/   Synthetic borrower documents + generator script + synthetic training CSV
test-cases/    Nine ready-to-post scenarios with expected outcomes (drive the test suites)
DEPLOYMENT.md  Step-by-step deployment guide (Vercel + Render + Supabase)
```

---

## Quick start (local)

Prerequisites: Python 3.11+, Node 18+. Optional: Tesseract (OCR), a Gemini key.

```bash
# 1. AI service
cd ai-service
pip install -r requirements.txt          # xgboost/shap/pymupdf are optional; fallbacks exist
cp .env.example .env                     # add GEMINI_API_KEY to enable the model
uvicorn app.main:app --reload --port 8100

# 2. Backend (new terminal)
cd backend
pip install -r requirements.txt
cp .env.example .env                     # SQLite by default; DATABASE_URL for Postgres
uvicorn app.main:app --reload --port 8000

# 3. Frontend (new terminal, from the repo root — npm workspaces)
npm install
cp frontend/.env.example frontend/.env.local   # NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
npm run dev -- --filter=frontend
```

Open http://localhost:3000, sign in with any email and password (demo auth), create an application,
upload the four files from `sample-data/borrower-001/`, and start underwriting.

### Try the scenarios

Each file in `test-cases/` is a complete `POST /underwrite` payload with its expected outcome:

| Scenario | Expected |
|---|---|
| `clean_approval` | approved |
| `high_foir`, `high_ltv`, `low_age` | declined (with an automatic path to approval where one exists) |
| `income_mismatch`, `identity_mismatch`, `missing_document` | referred |
| `low_confidence` | pauses for human review, approved after correction |
| `what_if_approval` | declined base run; tenure 48 months flips it to approved |

`sample-data/generate_sample_data.py` regenerates both the documents and these fixtures.

### Tests

```bash
cd ai-service && python -m pytest tests -q     # financials, reconciliation, extraction, workflow,
                                               # SHAP/explanations, API
cd backend    && python -m pytest tests -q     # applications, underwriting proxy, AI integration
cd frontend   && npm run typecheck && npm run build
```

---

## Screens

Dashboard · Applications · New application · Application overview · Documents · Underwriting
workflow (live 10-node timeline, human-review panel) · Evidence viewer (citations) · Decision
(reasons, financials, risk + SHAP, policy, AI reasoning, path to approval, narrative) · What-if ·
Audit (trace + replay) · Credit memo (PDF export) · Review queue · Settings (policy profiles, model
provider status).

---

## API contract

**Backend ↔ AI service**

```
POST /underwrite                    start a run (202)          GET  /underwrite                  list runs
GET  /underwrite/{run_id}           run state                  POST /underwrite/{run_id}/resume  human review
GET  /underwrite/{run_id}/trace     audit trail + node status  GET  /underwrite/{run_id}/replay  deterministic replay
POST /underwrite/{run_id}/what-if   immutable scenario         GET  /health · GET /policies
```

**Frontend ↔ backend**

```
POST /auth/login · GET /auth/me
POST/GET /applications · GET /applications/{id} · POST /applications/{id}/underwrite
POST/GET /applications/{id}/documents · DELETE /documents/{id}
GET /underwriting/{run_id} · POST …/resume · GET …/trace · GET …/replay · POST …/what-if · GET …/memo.pdf
GET /applications/{id}/credit-memo[?format=pdf] · POST /applications/{id}/decision
GET /dashboard/stats · GET /audit/runs · GET /health
```

The run state (`GET /underwriting/{run_id}`) carries everything the UI needs: status, decision,
reasons, financials, risk (with `shap`), evidence, reconciliation, low-confidence fields, human
reviews, policy snapshot, node statuses, `approval_path`, `explanation`, the memo and
`memo_pdf_url`.

---

## Configuration

| Service | Key variables |
|---|---|
| ai-service | `GEMINI_API_KEY`, `GEMINI_MODEL` (default `gemini-2.0-flash`), `MOCK_AI_MODE` (auto: false when a key is set), `POLICY_PROFILE`, `DATABASE_URL` |
| backend | `DATABASE_URL`, `AI_SERVICE_URL`, `DEMO_AUTH`, `SUPABASE_URL` / `SUPABASE_ANON_KEY` / `SUPABASE_JWT_SECRET`, `UPLOAD_DIR`, `MAX_UPLOAD_MB`, `CORS_ORIGINS` |
| frontend | `NEXT_PUBLIC_BACKEND_URL`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` |

Both Python services default to a local SQLite file and accept any SQLAlchemy Postgres URL. The
`.env.example` in each folder lists everything.

### Enable Gemini

```bash
# ai-service/.env
GEMINI_API_KEY=your-key-from-aistudio.google.com/apikey
```

Restart the AI service; `GET /health` on port 8100 then reports `llm_provider: gemini`. Gemini is
called over plain REST with `httpx`, so no SDK is needed. It only ever rewrites text from
pre-formatted verified numbers.

---

## Design principles

1. **No AI logic in the backend, no UI in the AI service.** The contract in `shared/` is the boundary.
2. **Numbers come from code.** EMI, FOIR, LTV, SHAP values and policy margins are computed
   deterministically and versioned; the model reasons and narrates.
3. **Every fact is cited.** Field, value, confidence, source document, page and the text snippet.
4. **Policy is data.** Cut-offs live in YAML; every run stores the exact snapshot it used.
5. **History is immutable.** What-if and replay never mutate a run; human reviews are append-only
   with reviewer, timestamp and note.
6. **Synthetic data only.** All borrowers, documents and the model's training set are invented; no
   real personal data is used anywhere.

---

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for the Vercel + Render + Supabase walkthrough, the environment
variables per service, the smoke test, and the known gaps to close before a production launch
(real auth, durable storage, Postgres validation, migrations, CI).

---

## Tech stack

Next.js 15 · React 19 · TypeScript · Tailwind CSS · Recharts · Zod · FastAPI · Pydantic ·
SQLAlchemy · SQLite/PostgreSQL · httpx · XGBoost + SHAP (optional, exact fallbacks) · PyMuPDF +
Tesseract (optional) · Gemini (optional) · Pytest · Playwright · Docker · Turborepo.
