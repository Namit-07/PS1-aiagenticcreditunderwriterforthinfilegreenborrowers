# Backend (Team A)

FastAPI main backend for the AI Credit Underwriter. Owns the application PostgreSQL
database, storage integration, main business APIs, AI-service integration, audit and
credit-memo features.

## Ownership

- **Team A** builds everything in this directory.
- The AI agents / LLM / LangGraph logic live in `../ai-service` (Team B) and are **not**
  implemented here.
- This service talks to the AI service over REST (see shared API contract in the root
  `README.md`).

## Run locally

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate   |  macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then edit values
alembic upgrade head          # apply migrations (when migrations exist)
uvicorn app.main:app --reload --port 8000
```

## Layout

```
app/
  main.py            FastAPI entrypoint / router mounting
  config.py          Settings from environment (Pydantic)
  api/               Route modules (auth, applications, documents, ...)
  models/            SQLAlchemy ORM models
  schemas/           Pydantic request/response schemas
  services/          Business logic (incl. ai_service integration + mock mode)
  db/database.py     Engine / session
tests/               Pytest suite
```

## Turborepo

`package.json` in this folder is a **Turborepo task-runner shim** (pip/uvicorn/pytest
wrappers) so the monorepo can orchestrate Python tasks alongside the frontend. The real
Python dependencies live in `requirements.txt`. Run via the repo root:

```bash
npm run dev -- --filter=@acu/backend       # uvicorn --reload :8000
npm run test -- --filter=@acu/backend      # pytest tests
```

## MOCK_AI_MODE

`MOCK_AI_MODE=true` (default in dev) lets Team A build and run the backend + frontend
without the real AI service. The `ai_service.py` service returns canned deterministic
responses when the flag is set.

## Endpoints (planned)

See the root `README.md` → "Shared API Contract".
