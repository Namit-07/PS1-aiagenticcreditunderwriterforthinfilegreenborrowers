"use client";

import { use } from "react";
import Link from "next/link";
import { ArrowRight, BookOpenText, Calculator, GitCompareArrows, RefreshCw, Search, UserCheck, Workflow } from "lucide-react";

import { ApplicationPageFrame } from "@/components/applications/application-page-frame";
import { DecisionBadge, RiskBandBadge, RunStatusBadge, SeverityBadge } from "@/components/applications/status-badge";
import { FinancialsTable } from "@/components/decision/financials-table";
import { HumanReviewPanel } from "@/components/human-review/human-review-panel";
import { ReconciliationList } from "@/components/reconciliation/reconciliation-list";
import { NodeStepper } from "@/components/underwriting/node-stepper";
import { ApprovalPathCard } from "@/components/what-if/approval-path-card";
import { RunLoader } from "@/components/underwriting/run-loader";
import { RunStatusBanner } from "@/components/underwriting/run-status-banner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { RingMeter } from "@/components/ui/ring-meter";
import { SectionHeading } from "@/components/ui/section-heading";
import { cn, confidenceTone, formatPercent, humanize, shortId } from "@/lib/utils";

interface PageProps {
  params: Promise<{ id: string }>;
}

const DECISION_BAND: Record<string, string> = {
  approved: "bg-success",
  declined: "bg-danger",
  referred: "bg-warning",
  human_review: "bg-info",
};

const DECISION_TEXT: Record<string, string> = {
  approved: "text-success",
  declined: "text-danger",
  referred: "text-warning",
  human_review: "text-info",
};

export default function UnderwritingPage({ params }: PageProps) {
  const { id } = use(params);

  return (
    <ApplicationPageFrame
      applicationId={id}
      title="Underwriting workflow"
      description="Live view of the agent pipeline. The run pauses for human review when extraction confidence is low."
    >
      <RunLoader applicationId={id} poll>
        {({ runId, state, setState, reload }) => {
          const runHref = `?run=${encodeURIComponent(runId)}`;
          const decisionKey = state.decision ?? "";
          return (
            <div className="flex flex-col gap-6">
              {/* Run meta row */}
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span
                    className="inline-flex items-center gap-1.5 rounded-md border bg-card px-2.5 py-1 font-mono text-xs text-muted-foreground"
                    title={runId}
                  >
                    <Workflow className="h-3.5 w-3.5 text-primary" />
                    run {shortId(runId, 16)}
                  </span>
                  <RunStatusBadge status={state.status} />
                  <Badge variant="outline">
                    policy {state.policy?.profile} · v{state.policy?.version}
                  </Badge>
                </div>
                <Button variant="outline" size="sm" onClick={reload}>
                  <RefreshCw /> Refresh
                </Button>
              </div>

              <div className="animate-in-up">
                <RunStatusBanner state={state} />
              </div>

              {/* Pipeline — the hero */}
              <Card className="animate-in-up delay-1">
                <CardHeader>
                  <SectionHeading
                    icon={<Workflow />}
                    title="Pipeline"
                    description="Ten deterministic-then-agentic nodes, executed in order."
                  />
                </CardHeader>
                <CardContent>
                  <NodeStepper nodes={state.nodes ?? []} runStatus={state.status} />
                </CardContent>
              </Card>

              {state.status === "awaiting_human" ? (
                <div className="animate-in-up delay-2">
                  <HumanReviewPanel state={state} onResumed={setState} />
                </div>
              ) : null}

              {state.status === "completed" ? (
                <Card className="animate-in-up delay-2 overflow-hidden">
                  <div className={cn("h-1.5", DECISION_BAND[decisionKey] ?? "bg-muted")} aria-hidden="true" />
                  <CardContent className="flex flex-col gap-6 p-5 sm:p-6 md:flex-row md:items-start">
                    <div className="flex items-center gap-5 md:w-72 md:shrink-0 md:flex-col md:items-start">
                      <RingMeter
                        value={state.confidence ?? 0}
                        tone={state.confidence !== null ? confidenceTone(state.confidence) : "neutral"}
                        size={104}
                        stroke={9}
                        label={state.confidence !== null ? formatPercent(state.confidence, 0) : "—"}
                        sublabel="confidence"
                      />
                      <div className="min-w-0">
                        <div className="eyebrow">Decision</div>
                        <div className={cn("mt-0.5 text-3xl font-bold leading-none tracking-tight", DECISION_TEXT[decisionKey] ?? "text-foreground")}>
                          {state.decision ? humanize(state.decision) : "—"}
                        </div>
                        <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
                          <DecisionBadge decision={state.decision} />
                          {state.risk ? <RiskBandBadge band={state.risk.risk_band} /> : null}
                          {state.risk ? (
                            <span className="text-xs text-muted-foreground tnum">score {state.risk.risk_score.toFixed(2)}</span>
                          ) : null}
                        </div>
                      </div>
                    </div>

                    <div className="min-w-0 flex-1">
                      <div className="eyebrow mb-2">Top reason codes</div>
                      {state.reasons.length > 0 ? (
                        <ul className="divide-y rounded-md border">
                          {state.reasons.slice(0, 6).map((r, i) => (
                            <li key={`${r.code}-${i}`} className="flex items-start gap-3 px-3 py-2.5 text-sm">
                              <SeverityBadge severity={r.severity} />
                              <div className="min-w-0">
                                <div className="font-mono text-xs font-medium">{r.code}</div>
                                {r.message ? <div className="text-[13px] text-foreground/85">{r.message}</div> : null}
                              </div>
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p className="text-sm text-muted-foreground">No reason codes were recorded for this decision.</p>
                      )}
                      <div className="mt-4 flex flex-wrap gap-2">
                        <Button asChild size="sm" variant="brand">
                          <Link href={`/applications/${id}/decision${runHref}`}>
                            Open decision page <ArrowRight />
                          </Link>
                        </Button>
                        <Button asChild size="sm" variant="outline">
                          <Link href={`/applications/${id}/evidence${runHref}`}>
                            <Search /> Evidence
                          </Link>
                        </Button>
                        <Button asChild size="sm" variant="outline">
                          <Link href={`/applications/${id}/memo${runHref}`}>
                            <BookOpenText /> Credit memo
                          </Link>
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ) : null}

              {state.status === "completed" && state.decision === "declined" ? (
                <ApprovalPathCard
                  className="animate-in-up delay-3"
                  path={state.approval_path ?? null}
                  applyHref={`/applications/${id}/what-if${runHref}&suggest=1`}
                />
              ) : null}

              {state.human_reviews.length > 0 ? (
                <Card className="animate-in-up delay-3">
                  <CardHeader>
                    <SectionHeading
                      icon={<UserCheck />}
                      title="Human reviews recorded"
                      description={`${state.human_reviews.length} reviewer action${state.human_reviews.length === 1 ? "" : "s"} applied to this run.`}
                    />
                  </CardHeader>
                  <CardContent>
                    <ul className="divide-y rounded-md border text-sm">
                      {state.human_reviews.map((h) => (
                        <li key={h.id} className="flex flex-wrap items-center gap-2 px-3 py-2">
                          <span className="font-mono text-xs font-medium">{h.field}</span>
                          <Badge variant="secondary">{humanize(h.action)}</Badge>
                          <span className="text-xs text-muted-foreground">by {h.reviewer ?? "—"}</span>
                          {h.note ? <span className="text-xs text-muted-foreground">· {h.note}</span> : null}
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              ) : null}

              <div className="grid gap-6 lg:grid-cols-2">
                <Card className="animate-in-up delay-3">
                  <CardHeader>
                    <SectionHeading
                      icon={<Calculator />}
                      title="Financials"
                      description={`Deterministic compute output (formula ${state.financials?.formula_version ?? "—"}).`}
                    />
                  </CardHeader>
                  <CardContent>
                    {state.financials ? (
                      <FinancialsTable financials={state.financials} compact />
                    ) : (
                      <p className="rounded-md border border-dashed px-3 py-6 text-center text-sm text-muted-foreground">
                        Not computed yet.
                      </p>
                    )}
                  </CardContent>
                </Card>
                <Card className="animate-in-up delay-4">
                  <CardHeader>
                    <SectionHeading
                      icon={<GitCompareArrows />}
                      title="Reconciliation"
                      description="Cross-document consistency checks."
                    />
                  </CardHeader>
                  <CardContent>
                    <ReconciliationList reconciliation={state.reconciliation} />
                  </CardContent>
                </Card>
              </div>
            </div>
          );
        }}
      </RunLoader>
    </ApplicationPageFrame>
  );
}
