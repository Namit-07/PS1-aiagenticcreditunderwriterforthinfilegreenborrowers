import { ArrowRight, FlaskConical, Lock, Sparkles, Wand2 } from "lucide-react";

import { DecisionBadge, RiskBandBadge } from "@/components/applications/status-badge";
import { ReasonsList } from "@/components/decision/reasons-list";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { SectionHeading } from "@/components/ui/section-heading";
import type { Financials, WhatIfResponse } from "@/lib/types";
import { cn, formatCurrency, formatNumber, formatPercent, humanize } from "@/lib/utils";

const DECISION_BAND: Record<string, string> = {
  approved: "bg-success",
  declined: "bg-danger",
  referred: "bg-warning",
  human_review: "bg-info",
};

function bandClass(decision: string | null | undefined): string {
  return (decision && DECISION_BAND[decision]) || "bg-muted-foreground/40";
}

function metric(f: Financials | null, key: "emi" | "foir" | "ltv"): string {
  if (!f) return "—";
  if (key === "emi") return formatCurrency(f.emi ?? f.monthly_emi);
  return formatPercent(f[key]);
}

function MetricRow({ label, base, scenario }: { label: string; base: string; scenario: string }) {
  const changed = base !== scenario;
  return (
    <div className="grid grid-cols-[1.2fr_1fr_1fr] items-center gap-2 border-b py-2.5 text-sm last:border-0">
      <span className="text-muted-foreground">{label}</span>
      <span className="text-right tnum">{base}</span>
      <span className="flex items-center justify-end gap-1.5">
        {changed ? (
          <span className="rounded-md bg-primary-soft px-2 py-0.5 font-semibold text-primary tnum">{scenario}</span>
        ) : (
          <span className="tnum">{scenario}</span>
        )}
      </span>
    </div>
  );
}

function OutcomeCard({
  band,
  icon,
  title,
  description,
  decision,
  confidence,
  meta,
  children,
  className,
}: {
  band: string;
  icon: React.ReactNode;
  title: string;
  description: React.ReactNode;
  decision: string | null | undefined;
  confidence: number | null | undefined;
  meta?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <Card className={cn("overflow-hidden", className)}>
      <div className={cn("h-1.5 w-full", band)} aria-hidden="true" />
      <CardHeader className="gap-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <SectionHeading icon={icon} title={title} description={description} />
          <DecisionBadge decision={decision} className="px-3 py-1 text-sm" />
        </div>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
          <span>
            confidence <span className="font-semibold text-foreground tnum">{formatPercent(confidence ?? null)}</span>
          </span>
          {meta}
        </div>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

export function ScenarioCompare({
  result,
  onApplySuggestion,
}: {
  result: WhatIfResponse;
  onApplySuggestion: (changes: Record<string, number>) => void;
}) {
  const { base, scenario, min_change_for_approval: suggestion } = result;
  const overrideEntries = Object.entries(scenario.overrides ?? {}).filter(([, v]) => v !== undefined && v !== null);

  return (
    <div className="flex flex-col gap-6">
      <div className="grid gap-6 md:grid-cols-2">
        <OutcomeCard
          className="animate-in-up"
          band={bandClass(base.decision?.decision)}
          icon={<Lock />}
          title="Base run"
          description="Immutable. The stored decision is never modified by a scenario."
          decision={base.decision?.decision}
          confidence={base.decision?.confidence}
        >
          <ReasonsList reasons={base.decision?.reasons ?? []} />
        </OutcomeCard>

        <OutcomeCard
          className="animate-in-up delay-1 ring-1 ring-primary/20"
          band={bandClass(scenario.decision?.decision)}
          icon={<FlaskConical />}
          title="Scenario"
          description={
            overrideEntries.length ? (
              <span className="flex flex-wrap gap-1">
                {overrideEntries.map(([k, v]) => (
                  <span key={k} className="rounded-md bg-primary-soft px-1.5 py-0.5 text-[11px] font-medium text-primary tnum">
                    {humanize(k)} = {formatNumber(v as number)}
                  </span>
                ))}
              </span>
            ) : (
              "No overrides — identical to base."
            )
          }
          decision={scenario.decision?.decision}
          confidence={scenario.decision?.confidence}
          meta={
            scenario.risk ? (
              <>
                <RiskBandBadge band={scenario.risk.risk_band} />
                <span>
                  score <span className="font-semibold text-foreground tnum">{scenario.risk.risk_score.toFixed(3)}</span>
                </span>
              </>
            ) : null
          }
        >
          <ReasonsList reasons={scenario.decision?.reasons ?? []} />
        </OutcomeCard>
      </div>

      <Card className="animate-in-up delay-2">
        <CardHeader>
          <SectionHeading title="Key metrics" description="Base vs scenario. Changed values are highlighted." />
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-[1.2fr_1fr_1fr] gap-2 border-b pb-2">
            <span className="eyebrow">Metric</span>
            <span className="eyebrow text-right">Base</span>
            <span className="eyebrow text-right text-primary">Scenario</span>
          </div>
          <MetricRow label="Decision" base={humanize(base.decision?.decision)} scenario={humanize(scenario.decision?.decision)} />
          <MetricRow label="EMI" base={metric(base.financials, "emi")} scenario={metric(scenario.financials, "emi")} />
          <MetricRow label="FOIR" base={metric(base.financials, "foir")} scenario={metric(scenario.financials, "foir")} />
          <MetricRow label="LTV" base={metric(base.financials, "ltv")} scenario={metric(scenario.financials, "ltv")} />
          <MetricRow
            label="Verified income"
            base={formatCurrency(base.financials?.verified_income ?? base.financials?.monthly_income ?? null)}
            scenario={formatCurrency(scenario.financials?.verified_income ?? scenario.financials?.monthly_income ?? null)}
          />
        </CardContent>
      </Card>

      <Card
        className={cn(
          "animate-in-up delay-3 overflow-hidden",
          suggestion ? "border-success/40 bg-success-soft/40" : "border-dashed shadow-none"
        )}
      >
        {suggestion ? <div className="h-1.5 w-full bg-success" aria-hidden="true" /> : null}
        <CardHeader>
          <div className="flex items-start gap-3">
            <span
              className={cn(
                "mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-md [&_svg]:h-4 [&_svg]:w-4",
                suggestion ? "bg-success text-white" : "bg-primary-soft text-primary"
              )}
            >
              <Sparkles />
            </span>
            <div className="min-w-0">
              <h3 className="text-[15px] font-semibold leading-tight tracking-tight">Minimum change for approval</h3>
              <p className="mt-0.5 text-[13px] text-muted-foreground">
                {suggestion
                  ? suggestion.description
                  : "No suggestion available. Either the scenario is already approvable, the search was not requested, or no small change flips the decision."}
              </p>
            </div>
          </div>
        </CardHeader>
        {suggestion ? (
          <CardContent className="flex flex-col gap-4">
            <div className="flex flex-wrap gap-2">
              {Object.entries(suggestion.changes).map(([k, v]) => (
                <span
                  key={k}
                  className="inline-flex items-center gap-1.5 rounded-full border border-success/30 bg-card px-3 py-1 text-xs font-medium shadow-sm"
                >
                  <span className="text-muted-foreground">{humanize(k)}</span>
                  <ArrowRight className="h-3 w-3 text-success" />
                  <span className="font-semibold text-success tnum">{formatNumber(v)}</span>
                </span>
              ))}
            </div>
            <div className="flex flex-wrap items-center gap-x-4 gap-y-2 rounded-md bg-card/70 px-3 py-2.5 text-sm">
              <span className="flex items-center gap-2">
                <span className="text-muted-foreground">Resulting decision</span>
                <DecisionBadge decision={suggestion.decision?.decision} />
              </span>
              {suggestion.financials ? (
                <span className="flex flex-wrap gap-x-3 text-xs text-muted-foreground tnum">
                  <span>
                    EMI <span className="font-medium text-foreground">{metric(suggestion.financials, "emi")}</span>
                  </span>
                  <span>
                    FOIR <span className="font-medium text-foreground">{metric(suggestion.financials, "foir")}</span>
                  </span>
                  <span>
                    LTV <span className="font-medium text-foreground">{metric(suggestion.financials, "ltv")}</span>
                  </span>
                </span>
              ) : null}
            </div>
            <div>
              <Button size="sm" onClick={() => onApplySuggestion(suggestion.changes)}>
                <Wand2 /> Apply suggestion to form
              </Button>
            </div>
          </CardContent>
        ) : null}
      </Card>
    </div>
  );
}
