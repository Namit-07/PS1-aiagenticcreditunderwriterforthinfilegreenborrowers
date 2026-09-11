"use client";

import { use } from "react";
import Link from "next/link";
import { BookOpenText, Brain, Calculator, FlaskConical, Gavel, Search, Sparkles, UserCheck, Workflow } from "lucide-react";

import { ApplicationPageFrame } from "@/components/applications/application-page-frame";
import { ApprovalPathCard } from "@/components/what-if/approval-path-card";
import { DecisionBadge, RiskBandBadge, RunStatusBadge } from "@/components/applications/status-badge";
import { FinancialsTable } from "@/components/decision/financials-table";
import { HumanOverrides } from "@/components/decision/human-overrides";
import { PolicyCard } from "@/components/decision/policy-card";
import { ReasonsList } from "@/components/decision/reasons-list";
import { RiskCard } from "@/components/decision/risk-card";
import { RiskReasoningView } from "@/components/decision/risk-reasoning";
import { ShapExplanationView } from "@/components/decision/shap-explanation";
import { RunLoader } from "@/components/underwriting/run-loader";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { RingMeter } from "@/components/ui/ring-meter";
import { SectionHeading } from "@/components/ui/section-heading";
import { cn, confidenceTone, formatPercent, humanize, shortId } from "@/lib/utils";

interface PageProps {
  params: Promise<{ id: string }>;
}

const BAND: Record<string, string> = {
  approved: "bg-success",
  declined: "bg-danger",
  referred: "bg-warning",
  human_review: "bg-info",
};

const WORD: Record<string, string> = {
  approved: "text-success",
  declined: "text-danger",
  referred: "text-warning",
  human_review: "text-info",
};

const TILE: Record<string, string> = {
  approved: "bg-success-soft text-success",
  declined: "bg-danger-soft text-danger",
  referred: "bg-warning-soft text-warning",
  human_review: "bg-info-soft text-info",
};

export default function DecisionPage({ params }: PageProps) {
  const { id } = use(params);

  return (
    <ApplicationPageFrame applicationId={id} title="Decision" description="Outcome of the underwriting run with the facts, numbers and rules behind it.">
      <RunLoader applicationId={id}>
        {({ runId, state }) => {
          const runHref = `?run=${encodeURIComponent(runId)}`;
          const key = state.decision ?? "";
          const blockers = state.reasons.filter((r) => r.severity === "blocker").length;
          const warnings = state.reasons.filter((r) => r.severity === "warning").length;
          return (
            <div className="flex flex-col gap-6">
              {state.status !== "completed" ? (
                <Alert variant="warning" title="Run not completed">
                  This run is <strong>{humanize(state.status)}</strong>. The decision below is preliminary or empty until the run completes.{" "}
                  <Link href={`/applications/${id}/underwriting${runHref}`} className="font-medium underline underline-offset-2">
                    Open the workflow
                  </Link>
                  .
                </Alert>
              ) : null}

              {/* Hero */}
              <Card className="animate-in-up overflow-hidden">
                <div className={cn("h-2", BAND[key] ?? "bg-muted")} aria-hidden="true" />
                <CardHeader className="flex-row flex-wrap items-center justify-between gap-3 space-y-0 pb-3">
                  <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                    <span className="inline-flex items-center gap-1.5 rounded-md border bg-card px-2 py-1 font-mono" title={runId}>
                      <Workflow className="h-3.5 w-3.5 text-primary" /> run {shortId(runId, 16)}
                    </span>
                    <RunStatusBadge status={state.status} />
                    <span>
                      policy <span className="font-medium text-foreground">{state.policy?.profile}</span> · v{state.policy?.version}
                    </span>
                  </div>
                  <DecisionBadge decision={state.decision} className="px-3 py-1 text-sm" />
                </CardHeader>
                <CardContent className="grid gap-6 pt-2 lg:grid-cols-5">
                  <div className="flex flex-col gap-5 lg:col-span-2">
                    <div className="flex items-center gap-5">
                      <span className={cn("flex h-16 w-16 shrink-0 items-center justify-center rounded-xl", TILE[key] ?? "bg-muted text-muted-foreground")}>
                        <Gavel className="h-7 w-7" />
                      </span>
                      <div className="min-w-0">
                        <div className="eyebrow">Underwriting decision</div>
                        <div className={cn("mt-0.5 text-4xl font-bold leading-none tracking-tight sm:text-5xl", WORD[key] ?? "text-foreground")}>
                          {state.decision ? humanize(state.decision) : "—"}
                        </div>
                        <div className="mt-2.5 flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
                          {state.risk ? <RiskBandBadge band={state.risk.risk_band} /> : null}
                          <span className="tnum">
                            {blockers} blocker{blockers === 1 ? "" : "s"} · {warnings} warning{warnings === 1 ? "" : "s"}
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-5 rounded-lg border bg-muted/40 p-4">
                      <RingMeter
                        value={state.confidence ?? 0}
                        tone={state.confidence !== null ? confidenceTone(state.confidence) : "neutral"}
                        size={104}
                        stroke={9}
                        label={state.confidence !== null ? formatPercent(state.confidence, 0) : "—"}
                        sublabel="confidence"
                      />
                      <div className="min-w-0 text-sm">
                        <div className="font-semibold">Decision confidence</div>
                        <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                          Overall extraction confidence{" "}
                          <span className="font-medium text-foreground tnum">{formatPercent(state.confidence_summary?.overall ?? null)}</span>{" "}
                          across {Object.keys(state.confidence_summary?.per_field ?? {}).length} fields.
                        </p>
                      </div>
                    </div>

                    <div className="flex flex-wrap gap-2">
                      <Button asChild size="sm" variant="brand">
                        <Link href={`/applications/${id}/memo${runHref}`}>
                          <BookOpenText /> Open credit memo
                        </Link>
                      </Button>
                      <Button asChild size="sm" variant="outline">
                        <Link href={`/applications/${id}/evidence${runHref}`}>
                          <Search /> Evidence
                        </Link>
                      </Button>
                      <Button asChild size="sm" variant="outline">
                        <Link href={`/applications/${id}/what-if${runHref}`}>
                          <FlaskConical /> What-if
                        </Link>
                      </Button>
                    </div>
                  </div>

                  <div className="min-w-0 lg:col-span-3">
                    <div className="mb-2 flex items-center justify-between">
                      <div className="eyebrow">Reasons</div>
                      <span className="text-xs text-muted-foreground tnum">{state.reasons.length} total</span>
                    </div>
                    <ReasonsList reasons={state.reasons} />
                  </div>
                </CardContent>
              </Card>

              {state.explanation || state.risk?.shap ? (
                <ShapExplanationView className="animate-in-up delay-1" explanation={state.explanation} shap={state.risk?.shap} />
              ) : null}

              {state.status === "completed" && state.decision === "declined" ? (
                <ApprovalPathCard
                  className="animate-in-up delay-1"
                  path={state.approval_path ?? null}
                  applyHref={`/applications/${id}/what-if${runHref}&suggest=1`}
                />
              ) : null}

              {state.memo?.sections?.narrative ? (
                <Card className="animate-in-up delay-1">
                  <CardHeader>
                    <SectionHeading
                      icon={<Sparkles />}
                      title="Plain-language summary"
                      description={
                        state.memo.sections.narrative.generated_by === "template"
                          ? "Template narrative built from the verified numbers (no API key configured)."
                          : `Written by ${state.memo.sections.narrative.generated_by} from the verified numbers only.`
                      }
                    />
                  </CardHeader>
                  <CardContent className="grid gap-4 md:grid-cols-2">
                    <div className="rounded-md border bg-muted/40 p-4">
                      <div className="eyebrow mb-1.5">For the credit committee</div>
                      <p className="text-sm leading-relaxed">{state.memo.sections.narrative.executive_summary}</p>
                    </div>
                    <div className="rounded-md border border-primary/25 bg-primary-soft/40 p-4">
                      <div className="eyebrow mb-1.5">For the borrower</div>
                      <p className="text-sm leading-relaxed">{state.memo.sections.narrative.borrower_explanation}</p>
                    </div>
                  </CardContent>
                </Card>
              ) : null}

              <div className="grid gap-6 lg:grid-cols-2">
                <Card className="animate-in-up delay-1">
                  <CardHeader>
                    <SectionHeading
                      icon={<Calculator />}
                      title="Financials"
                      description={`Deterministic calculations; formula ${state.financials?.formula_version ?? "—"}.`}
                    />
                  </CardHeader>
                  <CardContent>
                    {state.financials ? (
                      <FinancialsTable financials={state.financials} />
                    ) : (
                      <p className="rounded-md border border-dashed px-3 py-6 text-center text-sm text-muted-foreground">
                        Financials not computed.
                      </p>
                    )}
                  </CardContent>
                </Card>
                <div className="flex flex-col gap-6">
                  <div className="animate-in-up delay-2">
                    <RiskCard risk={state.risk} />
                  </div>
                  <div className="animate-in-up delay-3">
                    <PolicyCard policy={state.policy} />
                  </div>
                </div>
              </div>

              <Card className="animate-in-up delay-3">
                <CardHeader>
                  <SectionHeading
                    icon={<Brain />}
                    title="AI risk reasoning"
                    description={
                      <>
                        Narrative produced by the <span className="font-mono text-xs">risk_reasoning</span> node, grounded in the cited evidence.
                      </>
                    }
                  />
                </CardHeader>
                <CardContent>
                  <RiskReasoningView reasoning={state.risk_reasoning} />
                </CardContent>
              </Card>

              <Card className="animate-in-up delay-4">
                <CardHeader>
                  <SectionHeading icon={<UserCheck />} title="Human overrides" description="Reviewer actions applied to this run." />
                </CardHeader>
                <CardContent>
                  <HumanOverrides reviews={state.human_reviews} />
                </CardContent>
              </Card>
            </div>
          );
        }}
      </RunLoader>
    </ApplicationPageFrame>
  );
}
