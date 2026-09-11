# AI Service (Team B)

FastAPI service that runs the **AI underwriting workflow**: document extraction → OCR →
reconciliation → deterministic financial computation → policy evaluation → decision → trace.

## Ownership

- **Team B** builds everything in this directory.
- Loan/credit decisions are surfaced through REST; the main backend (Team A) calls this
  service. The LLM is used for extraction, reconciliation and reasoning **only** —
  financial numbers (EMI, FOIR, LTV) are computed deterministically here.
- The frontend and application PostgreSQL database are owned by Team A. This service is
  **independently runnable** and **replaceable** via the REST contract.

## Run locally

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate   |  macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then set OPENAI_API_KEY (or keep MOCK_AI_MODE=true)
uvicorn app.main:app --reload --port 8100
```

> OCR needs Tesseract installed on the host. On macOS: `brew install tesseract`;
> Debian/Ubuntu: `apt install tesseract-ocr`.

## REST contract

- `POST /underwrite` — start a run
- `GET  /underwrite/{run_id}` — run state
- `POST /underwrite/{run_id}/resume` — resume (human-in-the-loop)
- `GET  /underwrite/{run_id}/trace` — decision trace
- `POST /underwrite/{run_id}/what-if` — scenario evaluation

## Layout

```
app/
  main.py
  agents/          extraction / reconciliation / decision / human_assist
  workflows/       LangGraph underwriting graph
  llm/             OpenAI client, prompts, structured output parsing
  extraction/      pdf_parser, ocr, document_classifier
  reconciliation/  matcher, mismatch_detector
  schemas/         Pydantic models mirroring shared/schemas
  state/           underwriting run state
  utils/           confidence scoring + citation helpers
policies/          YAML policy profiles (default / conservative / aggressive)
tests/             Pytest suite
```

## Turborepo

`package.json` in this folder is a **Turborepo task-runner shim** (pip/uvicorn/pytest
wrappers) so the monorepo can orchestrate Python tasks alongside the frontend. Real
Python dependencies live in `requirements.txt`. Run via the repo root:

```bash
npm run dev -- --filter=@acu/ai-service      # uvicorn --reload :8100
npm run test -- --filter=@acu/ai-service     # pytest tests
```

## MOCK_AI_MODE

With `MOCK_AI_MODE=true` (default) the service serves canned deterministic responses and
does **not** call OpenAI — useful for offline development.