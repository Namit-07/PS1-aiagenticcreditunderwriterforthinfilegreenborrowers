# Deployment guide

Target topology (all free / hobby tiers are enough for a demo):

| Component | Where | Why |
|---|---|---|
| `frontend/` (Next.js) | **Vercel** | Zero-config Next.js hosting; env vars baked at build time. |
| `backend/` (FastAPI) | **Render** web service (Docker) | Public API the browser talks to. |
| `ai-service/` (FastAPI) | **Render** web service (Docker), *private* | Only the backend should reach it; it has no auth of its own. |
| Application DB | **Supabase Postgres** | Also gives Auth + Storage. |
| AI-service DB | **Render Postgres** (or a 2nd Supabase project) | Must be a *separate* database — both services create tables named `underwriting_runs`, `audit_events`, `human_reviews`, `credit_memos`. |
| Uploaded documents + memo PDFs | Render **persistent disk** on the backend (quickest) or Supabase Storage (needs the S3 backend implemented) | Local disk on Render is wiped on every deploy without a disk. |

Nothing below is automated; each step is a manual action in the provider's UI unless noted.

---

## 0. Before anything

1. **Commit the code.** `git status` currently shows almost every directory untracked. Vercel and Render deploy from GitHub.
2. Run the gates locally once more:
   ```bash
   cd ai-service && python -m pytest tests -q      # 45 tests
   cd ../backend  && python -m pytest tests -q      # 18 tests
   cd ../frontend && npm run typecheck && npm run build
   ```
3. Decide the auth story. The demo login (any email/password) is `DEMO_AUTH=true`. For anything public set `DEMO_AUTH=false` and use Supabase Auth (step 1.3). The Supabase JWT path exists in `backend/app/services/auth_service.py` but has **not been exercised end to end** — test it on a preview deploy first.

## 1. Supabase (application database, auth, optional storage)

1. Create a project. Note the **connection pooler** URI and rewrite it for SQLAlchemy:
   `postgresql+psycopg://postgres.<ref>:<password>@<pooler-host>:6543/postgres`
2. No migrations are shipped; the backend runs `create_all` at boot, so the tables appear on first start. (Alembic is in `requirements.txt` if you want real migrations later.)
3. Auth → enable Email provider, create the credit-officer accounts, and copy **Project URL**, **anon key** and **JWT secret** (Settings → API).
4. (Optional) Storage → create a bucket `documents`. The backend's `STORAGE_BACKEND` currently supports only `local`; the S3 path returns 501, so either implement it or use a Render disk (step 3.4).

## 2. Render — AI service (deploy this first)

1. New → Web Service → connect the repo, **Root Directory** `ai-service`, Runtime **Docker** (uses `ai-service/Dockerfile`, which installs Tesseract for OCR).
2. Attach a Postgres instance (Render → New → PostgreSQL) and copy its internal URL as `postgresql+psycopg://…`.
3. Environment:
   | Var | Value |
   |---|---|
   | `DATABASE_URL` | the Render Postgres URL (never the Supabase one — table names collide) |
   | `GEMINI_API_KEY` | key from aistudio.google.com/apikey (free tier). Leaving it empty keeps template narrative mode. |
   | `GEMINI_MODEL` | `gemini-2.0-flash` (or any free-tier model) |
   | `POLICY_PROFILE` | `default` |
   | `MOCK_AI_MODE` | leave unset (auto: false when a key is present) |
4. Make it **private** (Render "Private Service") or, if it must be a public Web Service, put it on an unguessable hostname — it has no authentication of its own.
5. Health check path: `/health`. It reports `llm_provider`, `risk_backend` (`xgboost` if the wheel installed, else `fallback`) and `graph_backend`.
6. Build note: `requirements.txt` pulls `xgboost`, `shap`, `pymupdf`, `pytesseract`. The image is large (~1.5 GB) and the first build takes several minutes. If `shap` fails to build on the slim image, remove it — exact SHAP values still come from XGBoost's `pred_contribs`.

## 3. Render — backend

1. New → Web Service, Root Directory `backend`, Runtime Docker.
2. Environment:
   | Var | Value |
   |---|---|
   | `DATABASE_URL` | Supabase pooler URL from step 1.1 |
   | `AI_SERVICE_URL` | internal URL of the AI service, e.g. `http://acu-ai-service:8100` (private) or its `https://….onrender.com` |
   | `MOCK_AI_MODE` | `false` |
   | `DEMO_AUTH` | `false` for real users (`true` keeps the hackathon login) |
   | `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_JWT_SECRET` | from step 1.3 (only needed when `DEMO_AUTH=false`) |
   | `SECRET_KEY` | long random string (signs demo tokens) |
   | `CORS_ORIGINS` | `https://<your-app>.vercel.app` (comma-separated if several) |
   | `UPLOAD_DIR` | `/app/data/uploads` |
   | `MAX_UPLOAD_MB` | `10` |
3. Health check path: `/health` (it also pings the AI service and reports its status).
4. **Attach a persistent disk** mounted at `/app/data` (1 GB is plenty). Uploads go to `/app/data/uploads`, auto-generated memo PDFs to `/app/data/memos`. Without the disk both vanish on every deploy.
5. Instance size: the free tier sleeps after inactivity; the first request after a sleep takes ~30 s and the frontend will show "Cannot reach backend" until it wakes. Use a Starter instance for a live demo.

## 4. Vercel — frontend

1. Import the repo, **Root Directory** `frontend`, Framework Next.js.
2. Install command: `npm install --legacy-peer-deps` (the root `.npmrc` sets this for local installs; Vercel installs inside `frontend/` so set it explicitly). Build command: `npm run build`.
3. Environment (build-time — redeploy after changing):
   | Var | Value |
   |---|---|
   | `NEXT_PUBLIC_BACKEND_URL` | `https://<backend>.onrender.com` |
   | `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` | from step 1.3 (safe to expose; anon key only) |
4. Never put `GEMINI_API_KEY`, `SUPABASE_SERVICE_ROLE_KEY` or `SUPABASE_JWT_SECRET` in Vercel — the frontend never needs them.
5. After the first deploy copy the Vercel URL back into the backend's `CORS_ORIGINS` and redeploy the backend.

## 5. Smoke test the deployment

1. `GET https://<backend>/health` → `status: ok` and `ai_service.status: ok`.
2. Log in on the Vercel URL, create an application, upload the four files from `sample-data/borrower-001/`, start underwriting, watch the 10 nodes complete, open Decision → confirm the SHAP card, the narrative (`generated_by` should read `gemini:…` once the key is set) and "Download PDF".
3. Run the scenario matrix against production (creates 5 applications):
   ```bash
   # point the seed script at the deployed backend
   python - <<'EOF'
   import re, pathlib
   p = pathlib.Path("scripts_or_scratch/seed_demo.py")  # the seeding helper used during development
   EOF
   ```
   (or simply repeat step 2 with `sample-data/borrower-003/` to see a declined run with a path to approval).
4. Check the review queue with the low-confidence documents (`test-cases/low_confidence.json` texts) to confirm pause → resume works across the network.

## 6. Self-hosting alternative (Docker Compose)

`docker-compose.yml` is a starting point, not complete. Before using it:
- add `DATABASE_URL` for `ai-service` (a second Postgres database) — today it falls back to SQLite *inside the container* and loses runs on rebuild;
- add volumes for `backend:/app/data` (uploads + memos) and for the AI-service data dir;
- pass `GEMINI_API_KEY` through to `ai-service`;
- the frontend is intentionally not in compose (run it on Vercel or add a Node service).

## Known gaps to close before calling it production

- **Auth**: demo login on by default; Supabase JWT path untested; AI service unauthenticated.
- **Storage**: only the local-disk backend exists; S3/Supabase Storage returns 501.
- **Postgres**: both services are written dialect-neutrally (JSON stored as text) but have only been run on SQLite so far.
- **Migrations**: `create_all` at boot; no Alembic revisions yet.
- **Tests**: no frontend end-to-end tests (`frontend/e2e/` is empty) and no CI workflow.
- **Feature gaps vs the brief**: mismatches are advisory (refer) only, never blocking; the what-if search covers tenure and ticket size but not a co-applicant.
