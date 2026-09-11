# Master prompt — pitch deck for "Verdant: AI Agentic Credit Underwriter for Thin-File Green Borrowers"

Copy everything below the line into the AI that will build the presentation.

---

You are a senior product designer and fintech pitch consultant. Build a **12-slide hackathon pitch deck** (16:9) for the project described below. Output, for every slide: a slide title, the on-slide content (max 40 words of body text, bullet fragments not sentences), a described visual (diagram, chart, screenshot placeholder or icon set), and 60–90 words of speaker notes. Then give a design system (palette, fonts, layout rules) and a 3-minute talk track. Do not invent numbers; where a figure is not supplied, write `[fill]`.

## The project in one paragraph
Verdant is an AI-agentic credit underwriting platform for **thin-file green borrowers** in India — gig-economy drivers and small operators buying EV two/three-wheelers or solar assets who have no formal credit history but rich alternative evidence (gig-platform payouts, bank statements, KYC, dealer invoices). It reads the documents, cross-checks them, computes affordability deterministically, applies an explicit YAML credit policy, pauses for a human when evidence is weak, and issues a decision that is explained in numbers and in words, replayable, and exportable as a credit memo PDF. The language model labels and narrates; it never produces a financial number.

## Problem
- Millions of green-mobility borrowers are "credit invisible": no bureau score, so lenders decline or price them out.
- Manual underwriting of alternative documents is slow, inconsistent and unauditable.
- Black-box ML scores are not explainable to regulators or borrowers.

## Solution — the pipeline (10 nodes, state saved after every node)
classification → extraction → confidence validation (human gate) → reconciliation → deterministic compute → XGBoost risk → risk reasoning → policy decision → explanation → audit.
Strict order: **Evidence → Reconciliation → Compute → Policy → Decision → Proof**.

## Key features (each deserves a slide or half-slide)
1. **Typed extraction with citations** — every fact is `{value, confidence, source document, page, evidence snippet}`; unreadable = null, never guessed. Text, PDF (PyMuPDF) and scanned images (Tesseract OCR).
2. **Deterministic compute** — EMI, FOIR, LTV, obligations, income volatility/stability in versioned code (formula v1). Replay re-executes a run and diffs it: byte-for-byte deterministic.
3. **Cross-document reconciliation** — declared vs credited income, name and address drift, application price vs invoice, loan vs invoice, missing documents; severity bands → reason codes.
4. **Policy-as-config** — three YAML profiles (default: FOIR ≤ 50%, LTV ≤ 80%, age ≥ 21; conservative 40/70/23; aggressive 60/90/18). Edit a cut-off, the next run uses it, no code change, no restart; the exact snapshot is stored per run.
5. **Assist mode (human in the loop)** — a critical field below the confidence threshold pauses the run *in the database*; the officer accepts / corrects / rejects each field with a note (and can override the decision); the run resumes from saved state. Nothing proceeds until every flagged field is reviewed.
6. **Risk signal + SHAP explainability** — XGBoost (synthetic training set, exact deterministic fallback) gives a secondary 0–1 risk score. A SHAP layer reports per-feature contributions with `base value + Σφ = score`, shown as a red/green bar chart and table. A "Why this decision" block pairs the policy margins that actually decided (e.g. "FOIR 61.4% vs limit 50.0%, +11.4 pp over") with the SHAP drivers, in a plain-language paragraph per borrower.
7. **Audit trail and credit memo** — every node logs inputs, outputs and model/policy/formula versions; the memo separates facts, calculations, model signal, AI reasoning, policy, human overrides and decision; the **PDF is generated automatically** when a run completes.
8. **What-if and automatic "path to approval"** — scenarios run on an immutable copy of the run. For every declined file the system automatically searches longer tenures and smaller tickets and reports the smallest change that flips the outcome (e.g. "extend tenure 24 → 42 months: EMI ₹7,344 → ₹4,687, FOIR 61.4% → 49.1%, approved").
9. **Gemini narrative (free tier, ₹0)** — with an API key, Gemini writes the executive summary and a borrower-facing explanation from verified numbers only; any model error or rate limit falls back to a deterministic template, so underwriting never blocks on the model.

## Decision matrix
- Any blocker (HIGH_FOIR, HIGH_LTV, LOW_AGE, MAX_TENURE_EXCEEDED, NO_VERIFIED_INCOME) → **declined** (+ automatic path to approval)
- Any warning (INCOME_MISMATCH, NAME/ADDRESS_MISMATCH, MISSING_DOCUMENT, LOW_OVERALL_CONFIDENCE…) → **referred** to a human
- Critical field below confidence threshold → **paused for human review**
- Otherwise → **approved**

## Architecture
Next.js 15 frontend (:3000) → FastAPI backend (:8000; applications, documents, auth, dashboard, run mirror, memo PDF) → FastAPI AI service (:8100; pipeline, policies, risk + SHAP, what-if) → Gemini (optional, REST). Three independently deployable services with one shared contract (JSON schemas + reason codes). SQLite locally, Postgres in production. Deploy target: Vercel + Render + Supabase.

## Demo storyline (use for a "live demo" slide and the talk track)
1. Create an application for "Ravi Kumar", EV two-wheeler, ₹90,000 over 36 months.
2. Upload four synthetic documents (KYC, bank statement, dealer invoice, platform earnings).
3. Start underwriting → watch the 10-node timeline complete in well under a second → **Approved**, FOIR 14.2%, LTV 75.0%, confidence 88%.
4. Open a second borrower ("Arjun Mehta", ₹150,000 over 24 months) → **Declined** on HIGH_FOIR (61.4% vs 50%) → the path-to-approval card already shows "extend tenure to 42 months → approved", with SHAP bars showing FOIR as the top risk driver.
5. Open a low-confidence file → the run is **paused**; the officer corrects the illegible income figure → run resumes → approved, with the correction in the audit trail.
6. Show the credit memo PDF and the deterministic replay (all diffs equal).

## Evidence of rigour (numbers you may quote)
- 9 scenario fixtures drive the test suites: clean approval, high FOIR, high LTV, low age, income mismatch, identity mismatch, missing document, low confidence, what-if approval.
- Automated tests: 45 (AI service) + 18 (backend); frontend type-checks and builds.
- Model evaluation endpoint (`/risk/metrics`) reports accuracy, precision, recall, specificity, F1, AUC on synthetic data — quote as `[fill]` unless the team supplies values, and label them "synthetic data".
- All data is synthetic; no real personal data anywhere.

## Differentiators to emphasise
Explainable by construction (policy margins + SHAP + words), deterministic and replayable, human-in-the-loop that genuinely pauses state, policy changes without code, automatic "what would get this person approved", ₹0 to run (free-tier Gemini, optional).

## Honest limitations (one slide, builds trust)
Demo auth, local file storage, synthetic training data, mismatches are advisory not blocking, co-applicant scenario not yet in the what-if search. Roadmap: Supabase auth + storage, bureau/alt-data connectors, co-applicant modelling, lender-specific policy packs, portfolio monitoring.

## Suggested slide order
1 Title · 2 Problem · 3 Who we serve (persona: gig EV driver) · 4 Solution & pipeline diagram · 5 Evidence & reconciliation · 6 Deterministic compute + policy-as-config · 7 Human in the loop · 8 Explainability (SHAP + "why this decision") · 9 Path to approval / what-if · 10 Audit trail & credit memo · 11 Architecture, stack, testing · 12 Limitations, roadmap, ask.

## Design direction
Name: **Verdant**. Palette: deep forest green `#1F5E3D` primary, lime accent `#8BC34A`, warm off-white `#F8F6F1` background, charcoal text `#141F1A`; status colours reserved — green approved, red declined, amber referred, blue human review. Fonts: Inter (body), JetBrains Mono for codes/numbers. Style: clean fintech, generous whitespace, 12 px rounded cards, one idea per slide, real-looking UI screenshots framed in a browser window (mark as `[screenshot: <screen>]`). Avoid stock clip-art and gradients on text.
