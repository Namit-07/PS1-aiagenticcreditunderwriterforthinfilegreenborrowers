"use client";

import { use } from "react";
import Link from "next/link";
import {
  ArrowRight,
  BookOpenText,
  CalendarClock,
  FileText,
  FlaskConical,
  Gavel,
  History,
  RefreshCw,
  Search,
  Sparkles,
  Upload,
  Workflow,
  type LucideIcon,
} from "lucide-react";

import { ApplicationPageFrame } from "@/components/applications/application-page-frame";
import { StartUnderwriting } from "@/components/applications/start-underwriting";
import {
  ApplicationStatusBadge,
  DecisionBadge,
  RunStatusBadge,
} from "@/components/applications/status-badge";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton, SkeletonBlock } from "@/components/ui/skeleton";
import { Stat, StatGrid } from "@/components/ui/stat";
import { useAsync } from "@/hooks/use-async";
import { api } from "@/lib/api";
import { NODE_ORDER } from "@/lib/types";
import { formatCurrency, formatDateTime, formatNumber, humanize, shortId } from "@/lib/utils";

interface PageProps {
  params: Promise<{ id: string }>;
}

const LINKS: { segment: string; label: string; icon: LucideIcon; text: string }[] = [
  { segment: "documents", label: "Documents", icon: FileText, text: "Upload KYC, bank statements, invoices." },
  { segment: "underwriting", label: "Underwriting", icon: Workflow, text: "Agent workflow and human review." },
  { segment: "evidence", label: "Evidence", icon: Search, text: "Extracted facts with citations." },
  { segment: "decision", label: "Decision", icon: Gavel, text: "Outcome, financials, risk and policy." },
  { segment: "what-if", label: "What-if", icon: FlaskConical, text: "Simulate changes on an immutable base." },
  { segment: "audit", label: "Audit", icon: History, text: "Trace timeline and deterministic replay." },
  { segment: "memo", label: "Credit memo", icon: BookOpenText, text: "Printable memo and PDF export." },
];

function initialsOf(name: string | null | undefined, fallback: string): string {
  const src = (name ?? "").trim() || fallback;
  const parts = src.split(/[\s._-]+/).filter(Boolean);
  return parts.slice(0, 2).map((p) => p[0]!.toUpperCase()).join("") || "?";
}

export default function ApplicationDetailPage({ params }: PageProps) {
  const { id } = use(params);
  const app = useAsync(() => api.getApplication(id), [id]);
  const docs = useAsync(() => api.listDocuments(id), [id]);
  const latestRunId = app.data?.latest_run_id ?? null;
  const run = useAsync(() => api.getRun(latestRunId as string), [latestRunId], Boolean(latestRunId));

  const a = app.data;
  const runHref = latestRunId ? `?run=${encodeURIComponent(latestRunId)}` : "";
  const docCount = docs.data?.length ?? 0;

  const nodesDone = run.data?.nodes?.filter((n) => n.status === "ok").length ?? 0;
  const nodesTotal = run.data?.nodes?.length || NODE_ORDER.length;
  const runProgress = run.data?.status === "completed" ? 1 : nodesDone / nodesTotal;
  const runTone =
    run.data?.status === "failed"
      ? "bad"
      : run.data?.status === "awaiting_human"
        ? "warn"
        : run.data?.status === "completed"
          ? "good"
          : "neutral";

  return (
    <ApplicationPageFrame
      applicationId={id}
      title={a ? a.borrower.full_name || a.borrower.ref_id : "Application"}
      description={
        a
          ? `${humanize(a.product.type)} · ${formatCurrency(a.loan_request?.amount ?? a.product.amount)} · ${a.product.tenure_months} months`
          : undefined
      }
      actions={
        <>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              app.reload();
              docs.reload();
              run.reload();
            }}
          >
            <RefreshCw /> Refresh
          </Button>
          <Button asChild size="sm" variant="secondary">
            <Link href={`/applications/${id}/documents`}>
              <Upload /> Upload documents
            </Link>
          </Button>
        </>
      }
    >
      {app.error ? (
        <Alert variant="destructive" title="Could not load application">
          {app.error}
        </Alert>
      ) : null}

      {app.loading && !a ? (
        <div className="grid gap-6 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <CardContent className="p-6">
              <SkeletonBlock lines={6} />
            </CardContent>
          </Card>
          <div className="flex flex-col gap-6">
            <Skeleton className="h-40" />
            <Skeleton className="h-48" />
          </div>
        </div>
      ) : a ? (
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Borrower + key facts */}
          <Card className="animate-in-up lg:col-span-2">
            <CardHeader className="gap-4 pb-5">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="flex min-w-0 items-center gap-4">
                  <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-xl bg-brand-gradient text-lg font-semibold tracking-wide text-white shadow-glow">
                    {initialsOf(a.borrower.full_name, a.borrower.ref_id)}
                  </div>
                  <div className="min-w-0">
                    <div className="eyebrow">Borrower</div>
                    <CardTitle className="mt-1 truncate text-xl">{a.borrower.full_name || a.borrower.ref_id}</CardTitle>
                    <CardDescription className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-0.5">
                      <span className="font-mono text-xs">{a.borrower.ref_id}</span>
                      <span className="text-muted-foreground/50">·</span>
                      <span>{humanize(a.borrower.employment_type)}</span>
                      <span className="text-muted-foreground/50">·</span>
                      <span>{humanize(a.borrower.location_tier)}</span>
                    </CardDescription>
                  </div>
                </div>
                <div className="flex flex-col items-start gap-1.5 sm:items-end">
                  <ApplicationStatusBadge status={a.status} />
                  <span className="font-mono text-[11px] text-muted-foreground" title={a.id}>
                    {shortId(a.id, 18)}
                  </span>
                </div>
              </div>
            </CardHeader>
            <CardContent className="flex flex-col gap-6">
              <section>
                <div className="eyebrow mb-2">Loan request</div>
                <StatGrid>
                  <Stat label="Amount" value={formatCurrency(a.loan_request?.amount ?? a.product.amount)} hint={humanize(a.product.type)} />
                  <Stat label="Tenure" value={`${a.loan_request?.tenure_months ?? a.product.tenure_months} months`} />
                  <Stat label="Annual rate" value={`${formatNumber(a.product.rate_annual)}%`} />
                  <Stat label="Vehicle price" value={formatCurrency(a.loan_request?.vehicle_price ?? null)} />
                  <Stat label="Down payment" value={formatCurrency(a.loan_request?.down_payment ?? null)} />
                  <Stat label="Declared income" value={formatCurrency(a.borrower.declared_monthly_income ?? null)} hint="per month" />
                </StatGrid>
              </section>
              <section>
                <div className="eyebrow mb-2">Borrower profile</div>
                <StatGrid>
                  <Stat label="Age" value={a.borrower.age} hint="years" />
                  <Stat label="Location tier" value={humanize(a.borrower.location_tier)} />
                  <Stat label="Employment" value={humanize(a.borrower.employment_type)} />
                </StatGrid>
              </section>
            </CardContent>
            <CardFooter className="flex-wrap gap-x-6 gap-y-2 text-xs text-muted-foreground">
              <span className="inline-flex items-center gap-1.5">
                <CalendarClock className="h-3.5 w-3.5" /> Created <span className="text-foreground tnum">{formatDateTime(a.created_at)}</span>
              </span>
              <span className="inline-flex items-center gap-1.5">
                Updated <span className="text-foreground tnum">{formatDateTime(a.updated_at)}</span>
              </span>
              <span className="inline-flex items-center gap-1.5">
                <FileText className="h-3.5 w-3.5" />
                <span className="text-foreground tnum">{docs.loading ? "…" : docs.error ? "—" : docCount}</span>
                {docCount === 1 ? "document" : "documents"}
                <Link href={`/applications/${id}/documents`} className="ml-1 font-medium text-primary hover:underline">
                  Manage
                </Link>
              </span>
            </CardFooter>
          </Card>

          <div className="flex flex-col gap-6">
            {/* Latest run */}
            <Card className="animate-in-up delay-1">
              <CardHeader className="flex-row items-start justify-between gap-3 space-y-0">
                <div className="flex items-start gap-3">
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-primary-soft text-primary">
                    <Workflow className="h-4 w-4" />
                  </span>
                  <div className="min-w-0">
                    <CardTitle>Latest run</CardTitle>
                    <CardDescription className="mt-0.5">
                      {latestRunId ? (
                        <span className="font-mono text-xs" title={latestRunId}>
                          {shortId(latestRunId, 16)}
                        </span>
                      ) : (
                        "No underwriting run yet."
                      )}
                    </CardDescription>
                  </div>
                </div>
                {run.data ? <RunStatusBadge status={run.data.status} /> : null}
              </CardHeader>
              <CardContent className="flex flex-col gap-4">
                {latestRunId ? (
                  run.loading && !run.data ? (
                    <SkeletonBlock lines={3} />
                  ) : run.error ? (
                    <Alert variant="warning">{run.error}</Alert>
                  ) : run.data ? (
                    <>
                      <div className="flex items-center justify-between gap-3 rounded-md bg-muted/50 px-3 py-2.5">
                        <span className="eyebrow">Decision</span>
                        <DecisionBadge decision={run.data.decision ?? a.latest_decision} />
                      </div>
                      <div>
                        <div className="mb-1.5 flex items-center justify-between text-xs">
                          <span className="text-muted-foreground">Pipeline progress</span>
                          <span className="tnum font-medium">
                            {run.data.status === "completed" ? nodesTotal : nodesDone}/{nodesTotal} nodes
                          </span>
                        </div>
                        <Progress value={runProgress} tone={runTone} label="Pipeline progress" />
                        <div className="mt-1.5 text-[11px] text-muted-foreground">
                          Policy <span className="font-medium text-foreground">{run.data.policy?.profile}</span> v{run.data.policy?.version} ·
                          updated <span className="tnum">{formatDateTime(run.data.updated_at)}</span>
                        </div>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <Button asChild size="sm" variant={run.data.status === "completed" ? "outline" : "default"}>
                          <Link href={`/applications/${id}/underwriting${runHref}`}>
                            <Workflow /> Open workflow
                          </Link>
                        </Button>
                        {run.data.status === "completed" ? (
                          <Button asChild size="sm">
                            <Link href={`/applications/${id}/decision${runHref}`}>
                              <Gavel /> View decision
                            </Link>
                          </Button>
                        ) : null}
                      </div>
                    </>
                  ) : null
                ) : (
                  <div className="flex items-center justify-between gap-3 rounded-md bg-muted/50 px-3 py-2.5">
                    <span className="eyebrow">Decision</span>
                    <DecisionBadge decision={a.latest_decision} />
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Start underwriting */}
            <Card className="animate-in-up delay-2 border-primary/25">
              <CardHeader className="flex-row items-start gap-3 space-y-0">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-primary-soft text-primary">
                  <Sparkles className="h-4 w-4" />
                </span>
                <div>
                  <CardTitle>Start underwriting</CardTitle>
                  <CardDescription className="mt-0.5">
                    Runs the agentic workflow on the uploaded documents. Each run is immutable.
                  </CardDescription>
                </div>
              </CardHeader>
              <CardContent>
                <StartUnderwriting applicationId={id} />
                {!docs.loading && docCount === 0 ? (
                  <p className="mt-3 rounded-md border border-warning/40 bg-warning-soft px-3 py-2 text-xs text-foreground/85">
                    No documents uploaded yet. The run can start, but extraction will have nothing to read.
                  </p>
                ) : null}
              </CardContent>
            </Card>
          </div>
        </div>
      ) : null}

      <section className="animate-in-up delay-3">
        <div className="eyebrow mb-3">Sections</div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {LINKS.map((l) => {
            const href = `/applications/${id}/${l.segment}${["documents", "memo"].includes(l.segment) ? "" : runHref}`;
            return (
              <Link
                key={l.segment}
                href={href}
                className="group surface flex items-start gap-3 p-4 transition-all duration-150 hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-pop focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-primary-soft text-primary">
                  <l.icon className="h-4 w-4" />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-2 text-sm font-semibold">
                    {l.label}
                    <ArrowRight className="h-3.5 w-3.5 text-muted-foreground opacity-0 transition-all group-hover:translate-x-0.5 group-hover:opacity-100" />
                  </div>
                  <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">{l.text}</p>
                </div>
              </Link>
            );
          })}
        </div>
      </section>
    </ApplicationPageFrame>
  );
}
