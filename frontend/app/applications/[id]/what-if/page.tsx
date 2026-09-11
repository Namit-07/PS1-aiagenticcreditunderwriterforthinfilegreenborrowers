"use client";

import { use, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { FlaskConical, Lock, SlidersHorizontal } from "lucide-react";

import { ApplicationPageFrame } from "@/components/applications/application-page-frame";
import { ApprovalPathCard } from "@/components/what-if/approval-path-card";
import { RunLoader } from "@/components/underwriting/run-loader";
import { Alert } from "@/components/ui/alert";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { SectionHeading } from "@/components/ui/section-heading";
import { baseValues, WhatIfForm, type WhatIfFormValues } from "@/components/what-if/what-if-form";
import { ScenarioCompare } from "@/components/what-if/scenario-compare";
import { api, errorMessage } from "@/lib/api";
import type { RunState, WhatIfRequest, WhatIfResponse } from "@/lib/types";
import { shortId } from "@/lib/utils";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function WhatIfPage({ params }: PageProps) {
  const { id } = use(params);

  return (
    <ApplicationPageFrame
      applicationId={id}
      title="What-if analysis"
      description="Simulate changes to the loan or borrower inputs and see how the policy outcome moves."
    >
      <RunLoader applicationId={id}>{({ runId, state }) => <WhatIfWorkbench runId={runId} state={state} />}</RunLoader>
    </ApplicationPageFrame>
  );
}

function WhatIfWorkbench({ runId, state }: { runId: string; state: RunState }) {
  const initial = useMemo(() => baseValues(state.financials), [state.financials]);
  const [applied, setApplied] = useState<Partial<WhatIfFormValues> | null>(null);
  const [result, setResult] = useState<WhatIfResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const searchParams = useSearchParams();
  const autoPath = state.decision === "declined" ? (state.approval_path ?? null) : null;

  // Arriving from the decision page with ?suggest=1 pre-fills the automatic suggestion.
  useEffect(() => {
    if (searchParams.get("suggest") && autoPath) {
      const next: Partial<WhatIfFormValues> = {};
      for (const [k, v] of Object.entries(autoPath.changes)) {
        if (k in initial) next[k as keyof WhatIfFormValues] = String(v);
      }
      setApplied(next);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams, autoPath]);

  const run = async (payload: WhatIfRequest) => {
    setSubmitting(true);
    setError(null);
    try {
      setResult(await api.whatIf(runId, payload));
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  const applySuggestion = (changes: Record<string, number>) => {
    const next: Partial<WhatIfFormValues> = {};
    for (const [k, v] of Object.entries(changes)) {
      if (k in initial) next[k as keyof WhatIfFormValues] = String(v);
    }
    setApplied({ ...next });
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="animate-in-up flex items-center gap-3 rounded-lg border border-info/25 bg-info-soft px-4 py-2.5 text-[13px]">
        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-info/15 text-info">
          <Lock className="h-3.5 w-3.5" />
        </span>
        <p className="min-w-0 text-foreground/85">
          <span className="font-semibold text-foreground">Base run is immutable.</span> Scenarios are computed on a copy of run{" "}
          <span className="font-mono text-xs" title={runId}>
            {shortId(runId, 16)}
          </span>
          . Nothing here changes the recorded decision, evidence or audit trail.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-12">
        <Card className="animate-in-up delay-1 self-start lg:col-span-5 xl:col-span-4">
          <CardHeader>
            <SectionHeading
              icon={<SlidersHorizontal />}
              title="Scenario inputs"
              description="Prefilled from the base run. Only values you change are sent as overrides."
            />
          </CardHeader>
          <CardContent>
            {!state.financials ? (
              <Alert variant="warning" className="mb-4">
                The base run has no financials yet, so inputs cannot be prefilled. You can still enter overrides manually.
              </Alert>
            ) : null}
            <WhatIfForm initial={initial} basePolicy={state.policy?.profile ?? "default"} applied={applied} submitting={submitting} onSubmit={run} />
          </CardContent>
        </Card>

        <div className="flex flex-col gap-6 lg:col-span-7 xl:col-span-8">
          {error ? (
            <Alert variant="destructive" title="Scenario failed">
              {error}
            </Alert>
          ) : null}

          {!result && state.status === "completed" && state.decision === "declined" ? (
            <ApprovalPathCard
              className="animate-in-up delay-1"
              path={autoPath}
              title="Automatic path to approval"
              onApply={applySuggestion}
            />
          ) : null}

          {result ? (
            <ScenarioCompare result={result} onApplySuggestion={applySuggestion} />
          ) : (
            <EmptyState
              className="animate-in-up delay-2 min-h-[320px] lg:min-h-[480px]"
              icon={<FlaskConical />}
              title={submitting ? "Simulating scenario…" : "No scenario yet"}
              description={
                submitting
                  ? "Recomputing financials, risk and policy on a copy of the base run."
                  : "Adjust one or more inputs on the left and run a scenario. Results appear here as a base-vs-scenario comparison."
              }
            />
          )}
        </div>
      </div>
    </div>
  );
}
