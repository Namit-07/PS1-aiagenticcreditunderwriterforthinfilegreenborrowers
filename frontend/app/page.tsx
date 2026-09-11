import Link from "next/link";
import {
  ArrowRight,
  Check,
  FileSearch,
  GitCompareArrows,
  Leaf,
  Lock,
  ScrollText,
  ShieldCheck,
  Sigma,
  UserCheck,
  type LucideIcon,
} from "lucide-react";

import { Button } from "@/components/ui/button";

const HIGHLIGHTS: { icon: LucideIcon; title: string; text: string }[] = [
  {
    icon: FileSearch,
    title: "Evidence-backed extraction",
    text: "Every extracted fact carries a confidence score and a citation back to the source document and page.",
  },
  {
    icon: UserCheck,
    title: "Human in the loop",
    text: "Low-confidence fields pause the run until a reviewer accepts, corrects or rejects them. Nothing is guessed.",
  },
  {
    icon: ShieldCheck,
    title: "Deterministic and auditable",
    text: "EMI, FOIR and LTV are computed by code, policies live in YAML, and every run can be replayed byte-for-byte.",
  },
];

const PIPELINE: { icon: LucideIcon; label: string; text: string }[] = [
  { icon: FileSearch, label: "Evidence", text: "KYC, bank statement, dealer invoice, platform payouts" },
  { icon: GitCompareArrows, label: "Reconcile", text: "Cross-check names, income and prices across documents" },
  { icon: Sigma, label: "Compute", text: "EMI · FOIR · LTV · volatility, deterministically" },
  { icon: ShieldCheck, label: "Policy", text: "Versioned limits decide approve / refer / reject" },
  { icon: ScrollText, label: "Proof", text: "Trace, replay and an exportable credit memo" },
];

const DEMO_NODES = [
  { name: "Classification", ok: true },
  { name: "Extraction", ok: true },
  { name: "Confidence gate", ok: true },
  { name: "Reconciliation", ok: true },
  { name: "Deterministic compute", ok: true },
  { name: "Risk signal", ok: true },
  { name: "Policy decision", ok: true },
];

export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col bg-background">
      {/* ---- hero ---- */}
      <section className="relative overflow-hidden bg-sidebar text-sidebar-foreground">
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.12]"
          style={{
            backgroundImage: "radial-gradient(hsl(150 40% 70%) 1px, transparent 1px)",
            backgroundSize: "24px 24px",
          }}
          aria-hidden="true"
        />
        <div
          className="pointer-events-none absolute -right-40 -top-40 h-[520px] w-[520px] rounded-full opacity-40 blur-3xl"
          style={{ background: "radial-gradient(closest-side, hsl(158 55% 30%), transparent)" }}
          aria-hidden="true"
        />

        <header className="relative mx-auto flex w-full max-w-6xl items-center justify-between px-6 py-5">
          <div className="flex items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-gradient text-white shadow-glow">
              <Leaf className="h-[18px] w-[18px]" />
            </span>
            <span className="leading-tight">
              <span className="block text-[15px] font-bold tracking-tight text-white">Verdant</span>
              <span className="block text-[11px] text-sidebar-muted">AI Credit Underwriter</span>
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Button asChild variant="ghost" size="sm" className="text-sidebar-foreground hover:bg-white/10 hover:text-white">
              <Link href="/dashboard">Dashboard</Link>
            </Button>
            <Button asChild size="sm" variant="brand">
              <Link href="/login">
                Sign in <ArrowRight />
              </Link>
            </Button>
          </div>
        </header>

        <div className="relative mx-auto grid w-full max-w-6xl items-center gap-12 px-6 pb-20 pt-10 lg:grid-cols-[1.1fr_0.9fr] lg:pb-28 lg:pt-16">
          <div className="animate-in-up">
            <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-sidebar-foreground">
              <span className="h-1.5 w-1.5 rounded-full bg-lime" />
              Agentic underwriting for thin-file green borrowers
            </span>
            <h1 className="mt-5 text-4xl font-bold leading-[1.08] tracking-tight text-white sm:text-5xl lg:text-[56px]">
              Underwrite EV and solar loans for people <span className="text-brand-gradient">without a credit history.</span>
            </h1>
            <p className="mt-5 max-w-xl text-[15px] leading-relaxed text-sidebar-foreground/85 sm:text-base">
              Verdant reads KYC, bank statements, dealer invoices and gig-platform earnings, reconciles what they say,
              computes affordability deterministically and applies an explicit policy. Anything uncertain goes to a
              human before a decision is issued. Every run is traceable and replayable.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <Button asChild size="lg" variant="brand">
                <Link href="/login">
                  Open the underwriter <ArrowRight />
                </Link>
              </Button>
              <Button asChild size="lg" variant="outline" className="border-white/15 bg-white/5 text-white hover:bg-white/10 hover:text-white">
                <Link href="/dashboard">See the dashboard</Link>
              </Button>
            </div>
            <dl className="mt-10 grid max-w-md grid-cols-3 gap-4 border-t border-white/10 pt-6">
              {[
                ["10", "pipeline nodes"],
                ["3", "policy profiles"],
                ["100%", "replayable runs"],
              ].map(([v, l]) => (
                <div key={l}>
                  <dt className="text-[11px] uppercase tracking-[0.14em] text-sidebar-muted">{l}</dt>
                  <dd className="mt-1 text-2xl font-bold tnum text-white">{v}</dd>
                </div>
              ))}
            </dl>
          </div>

          {/* product preview */}
          <div className="animate-in-up delay-2 relative">
            <div className="absolute -inset-4 rounded-3xl bg-brand-gradient opacity-20 blur-2xl" aria-hidden="true" />
            <div className="relative rounded-2xl border border-white/10 bg-[hsl(162_22%_8%)] p-5 shadow-pop">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-[11px] uppercase tracking-[0.14em] text-sidebar-muted">Run · example</div>
                  <div className="mt-0.5 text-sm font-semibold text-white">Ravi Kumar · EV two-wheeler · ₹90,000</div>
                </div>
                <span className="inline-flex items-center gap-1.5 rounded-full border border-success/40 bg-success/15 px-2.5 py-1 text-xs font-semibold text-[hsl(152_60%_70%)]">
                  <Check className="h-3.5 w-3.5" /> Approved
                </span>
              </div>

              <ol className="mt-5 space-y-2">
                {DEMO_NODES.map((n, i) => (
                  <li key={n.name} className="flex items-center gap-3 text-[13px]">
                    <span className="flex h-6 w-6 items-center justify-center rounded-full bg-success text-white">
                      <Check className="h-3.5 w-3.5" />
                    </span>
                    <span className="text-sidebar-foreground">{n.name}</span>
                    <span className="ml-auto font-mono text-[11px] text-sidebar-muted">{(i + 1) * 3} ms</span>
                  </li>
                ))}
              </ol>

              <div className="mt-5 grid grid-cols-3 gap-2">
                {[
                  ["EMI", "₹3,076"],
                  ["FOIR", "14.2%"],
                  ["LTV", "75.0%"],
                ].map(([k, v]) => (
                  <div key={k} className="rounded-lg border border-white/10 bg-white/5 px-3 py-2">
                    <div className="text-[10px] uppercase tracking-[0.14em] text-sidebar-muted">{k}</div>
                    <div className="mt-0.5 text-base font-semibold tnum text-white">{v}</div>
                  </div>
                ))}
              </div>
              <div className="mt-4 flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-[12px] text-sidebar-foreground">
                <Lock className="h-3.5 w-3.5 text-lime" />
                Policy default v1.0 · formula v1 · trace of 17 events recorded
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ---- pipeline ---- */}
      <section className="mx-auto w-full max-w-6xl px-6 py-16">
        <div className="eyebrow">How a run works</div>
        <h2 className="mt-2 text-2xl font-bold tracking-tight sm:text-3xl">Evidence → Reconcile → Compute → Policy → Proof</h2>
        <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
          The language model only labels and explains. Every number that matters is produced by deterministic code and
          checked against a versioned policy.
        </p>
        <ol className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {PIPELINE.map((step, i) => (
            <li key={step.label} className={`surface animate-in-up delay-${Math.min(i, 4)} relative p-5`}>
              <span className="absolute right-4 top-4 font-mono text-[11px] text-muted-foreground">0{i + 1}</span>
              <span className="flex h-9 w-9 items-center justify-center rounded-md bg-primary-soft text-primary">
                <step.icon className="h-4 w-4" />
              </span>
              <div className="mt-3 text-sm font-semibold">{step.label}</div>
              <p className="mt-1 text-[13px] leading-snug text-muted-foreground">{step.text}</p>
            </li>
          ))}
        </ol>
      </section>

      {/* ---- highlights ---- */}
      <section className="mx-auto w-full max-w-6xl px-6 pb-20">
        <div className="grid gap-4 md:grid-cols-3">
          {HIGHLIGHTS.map((h) => (
            <div key={h.title} className="surface p-6">
              <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-gradient text-white shadow-glow">
                <h.icon className="h-5 w-5" />
              </span>
              <h3 className="mt-4 text-base font-semibold">{h.title}</h3>
              <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{h.text}</p>
            </div>
          ))}
        </div>
        <div className="mt-10 flex flex-col items-start justify-between gap-4 rounded-2xl border bg-card p-6 shadow-card sm:flex-row sm:items-center">
          <div>
            <div className="text-base font-semibold">Ready to try it on synthetic borrowers?</div>
            <p className="mt-1 text-sm text-muted-foreground">Sign in with any email. No real borrower data is used anywhere.</p>
          </div>
          <Button asChild size="lg" variant="brand">
            <Link href="/login">
              Sign in <ArrowRight />
            </Link>
          </Button>
        </div>
      </section>

      <footer className="border-t bg-card">
        <div className="mx-auto flex w-full max-w-6xl flex-wrap items-center justify-between gap-3 px-6 py-5 text-xs text-muted-foreground">
          <span className="flex items-center gap-2">
            <Leaf className="h-3.5 w-3.5 text-primary" /> Verdant · AI Agentic Credit Underwriter
          </span>
          <span>Deterministic financials · versioned policy · full audit trail</span>
        </div>
      </footer>
    </main>
  );
}
