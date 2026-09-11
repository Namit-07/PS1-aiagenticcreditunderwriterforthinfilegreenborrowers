import Link from "next/link";
import { ArrowRight, FlaskConical, Route, Wand2 } from "lucide-react";

import { DecisionBadge } from "@/components/applications/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import type { Financials, WhatIfMinChange } from "@/lib/types";
import { cn, formatCurrency, formatNumber, formatPercent, humanize } from "@/lib/utils";

function metric(f: Financials | null | undefined, key: "emi" | "foir" | "ltv"): string {
  if (!f) return "—";
  if (key === "emi") return formatCurrency(f.emi ?? f.monthly_emi);
  return formatPercent(f[key]);
}

const LABEL: Record<string, string> = {
  tenure_months: "Tenure",
  loan_amount: "Loan amount",
  down_payment: "Down payment",
  vehicle_price: "Vehicle price",
  annual_rate: "Annual rate",
  monthly_income: "Monthly income",
  existing_monthly_obligations: "Existing obligations",
};

function formatChange(key: string, value: number): string {
  if (key === "tenure_months") return `${formatNumber(value, 0)} months`;
  if (key === "annual_rate") return `${formatNumber(value, 2)}%`;
  return formatCurrency(value);
}

export interface ApprovalPathCardProps {
  /** The automatic what-if result; `null` means the search ran but found no small fix. */
  path: WhatIfMinChange | null | undefined;
  title?: string;
  /** Link to the what-if page (pre-loads the suggestion). */
  applyHref?: string;
  /** Apply the suggestion in-place (what-if workbench). */
  onApply?: (changes: Record<string, number>) => void;
  compact?: boolean;
  className?: string;
}

/**
 * "Path to approval" — shown automatically for declined runs. The AI service searches
 * tenure (up to the policy maximum) and loan reductions on an immutable copy of the
 * run and reports the smallest change that flips the policy decision to approved.
 */
export function ApprovalPathCard({ path, title = "Path to approval", applyHref, onApply, compact, className }: ApprovalPathCardProps) {
  const found = Boolean(path);
  return (
    <Card
      className={cn(
        "overflow-hidden",
        found ? "border-success/40 bg-success-soft/40" : "border-dashed shadow-none",
        className
      )}
    >
      {found ? <div className="h-1.5 w-full bg-success" aria-hidden="true" /> : null}
      <CardHeader className={cn(compact && "pb-3")}>
        <div className="flex items-start gap-3">
          <span
            className={cn(
              "mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-md [&_svg]:h-4 [&_svg]:w-4",
              found ? "bg-success text-white" : "bg-muted text-muted-foreground"
            )}
          >
            <Route />
          </span>
          <div className="min-w-0">
            <div className="eyebrow">Automatic what-if</div>
            <h3 className="mt-0.5 text-[15px] font-semibold leading-tight tracking-tight">{title}</h3>
            <p className="mt-1 text-[13px] leading-snug text-muted-foreground">
              {path
                ? `Smallest change that makes this file approvable under the same policy: ${path.description}.`
                : "The search tried longer tenures (up to the policy maximum) and smaller loan amounts, but no small change alone flips the decision. The blocker is not purely affordability."}
            </p>
          </div>
        </div>
      </CardHeader>
      {path ? (
        <CardContent className="flex flex-col gap-4">
          <div className="flex flex-wrap gap-2">
            {Object.entries(path.changes).map(([k, v]) => (
              <span
                key={k}
                className="inline-flex items-center gap-1.5 rounded-full border border-success/30 bg-card px-3 py-1 text-xs font-medium shadow-sm"
              >
                <span className="text-muted-foreground">{LABEL[k] ?? humanize(k)}</span>
                <ArrowRight className="h-3 w-3 text-success" />
                <span className="font-semibold text-success tnum">{formatChange(k, v)}</span>
              </span>
            ))}
          </div>
          <div className="grid gap-2 sm:grid-cols-4">
            <div className="rounded-md bg-card/80 px-3 py-2">
              <div className="eyebrow">Outcome</div>
              <div className="mt-1">
                <DecisionBadge decision={path.decision?.decision} />
              </div>
            </div>
            {(["emi", "foir", "ltv"] as const).map((k) => (
              <div key={k} className="rounded-md bg-card/80 px-3 py-2">
                <div className="eyebrow">{k.toUpperCase()}</div>
                <div className="mt-1 text-sm font-semibold tnum">{metric(path.financials, k)}</div>
              </div>
            ))}
          </div>
          {onApply || applyHref ? (
            <div className="flex flex-wrap gap-2">
              {onApply ? (
                <Button size="sm" onClick={() => onApply(path.changes)}>
                  <Wand2 /> Apply suggestion to form
                </Button>
              ) : null}
              {applyHref ? (
                <Button asChild size="sm" variant={onApply ? "outline" : "default"}>
                  <Link href={applyHref}>
                    <FlaskConical /> Explore in what-if
                  </Link>
                </Button>
              ) : null}
            </div>
          ) : null}
        </CardContent>
      ) : null}
    </Card>
  );
}
