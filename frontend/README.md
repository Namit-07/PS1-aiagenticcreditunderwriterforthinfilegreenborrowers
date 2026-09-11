# Frontend (Team A)

Next.js 15 + TypeScript + Tailwind CSS + shadcn/ui web application for the AI Credit
Underwriter.

## Ownership

- **Team A** builds everything in this directory (UI/UX, dashboard, auth, applications,
  document uploads, review, audit, what-if, credit memo, deployment).
- The internal AI agent logic belongs to **Team B** (`../ai-service`) and is called via
  the backend REST API — never implemented in the frontend.

## Tech

- **Next.js 15+** (App Router), **TypeScript**, **Tailwind CSS**, **shadcn/ui**,
  **Lucide React**, **Recharts**, **React Hook Form**, **Zod**, **Supabase Auth**,
  **Playwright** (E2E).

## Run locally

This folder is part of a Turborepo monorepo. Install and run from the **repo root**, or
standalone here:

```bash
# From the repo root (recommended):
npm install
npm run dev -- --filter=frontend      # http://localhost:3000

# Or standalone inside frontend/:
npm install
cp .env.example .env.local   # then add Supabase values
npm run dev                  # http://localhost:3000
```

Useful scripts:

```bash
npm run typecheck   # tsc --noEmit
npm run build       # production build (deploy to Vercel)
npm run test:e2e    # Playwright
```

## Layout

```
app/          App Router pages (login, dashboard, applications/** , review, settings)
components/   Feature components (ui/ = shadcn primitives)
lib/          api / auth / types / validations / utils
hooks/        Shared React hooks (shadcn-friendly home)
public/       Static assets
e2e/          Playwright specs (create when writing tests)
```

## Development note

- Start with the backend running in `MOCK_AI_MODE=true` so the UI can be built against
  stable API shapes before Team B ships the real AI service.