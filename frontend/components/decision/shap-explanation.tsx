"use client";

import { useState } from "react";
import { Bar, BarChart, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Check, ChevronDown, ChevronRight, MessageSquareText, Sigma, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { SectionHeading } from "@/components/ui/section-heading";
import type { DecisionExplanation, ShapExplanation } from "@/lib/types";
import { cn, formatNumber } from "@/lib/utils";

const METHOD_LABEL: Record<string, string> = {
  tree_shap: "TreeSHAP (shap package) on the fitted XGBoost model",
  xgboost_pred_contribs: "Exact TreeSHAP via XGBoost pred_contribs",
  additive_exact: "Exact Shapley decomposition of the additive fallback model",
};

function phi(v: number): string {
  return `${v >= 0 ? "+" : "−"}${Math.abs(v).toFixed(3)}`;
}

/** Horizontal SHAP bar chart: red bars raise risk, green bars lower it. */
export function ShapChart({ shap, limit = 10 }: { shap: ShapExplanation; limit?: number }) {
  const rows = shap.contributions.filter((c) => c.direction !== "neutral").slice(0, limit);
  if (rows.length === 0) {
    return <p className="text-sm text-muted-foreground">Every feature sits at the baseline; no contribution to show.</p>;
  }
  const max = Math.max(...rows.map((r) => Math.abs(r.shap)), 0.01);
  const data = rows.map((r) => ({ name: r.label, shap: r.shap, value: r.value_display, baseline: r.baseline_display }));
  return (
    <div style={{ height: 34 * data.length + 24 }} className="w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 24, left: 8, bottom: 4 }} barCategoryGap={8}>
          <XAxis
            type="number"
            domain={[-max * 1.1, max * 1.1]}
            tickFormatter={(v: number) => v.toFixed(2)}
            tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis type="category" dataKey="name" width={190} tick={{ fontSize: 12, fill: "hsl(var(--foreground))" }} axisLine={false} tickLine={false} />
          <ReferenceLine x={0} stroke="hsl(var(--border))" />
          <Tooltip
            cursor={{ fill: "hsl(var(--muted) / 0.6)" }}
            contentStyle={{
              background: "hsl(var(--popover))",
              border: "1px solid hsl(var(--border))",
              borderRadius: 8,
              color: "hsl(var(--popover-foreground))",
              fontSize: 12,
            }}
            formatter={(v: number, _n, item) => [
              `${phi(v)} (value ${item.payload.value}, baseline ${item.payload.baseline})`,
              "φ",
            ]}
          />
          <Bar dataKey="shap" radius={[4, 4, 4, 4]} maxBarSize={18} isAnimationActive={false}>
            {data.map((d) => (
              <Cell key={d.name} fill={d.shap > 0 ? "hsl(var(--danger))" : "hsl(var(--success))"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function WaterfallStrip({ shap }: { shap: ShapExplanation }) {
  const tiles = [
    { label: "Baseline borrower", value: shap.base_value, hint: shap.baseline_description ?? "expected model output" },
    { label: "Σ SHAP contributions", value: shap.sum_contributions, hint: "sum of φ over all features", signed: true },
    { label: "This borrower's score", value: shap.score, hint: "0 = safest · 1 = riskiest" },
  ];
  return (
    <div className="grid gap-2 sm:grid-cols-3">
      {tiles.map((t, i) => (
        <div key={t.label} className={cn("rounded-md border bg-muted/40 px-3 py-2.5", i === 2 && "border-primary/30 bg-primary-soft/40")}>
          <div className="eyebrow">{t.label}</div>
          <div className="mt-1 text-xl font-bold tnum">{t.signed ? phi(t.value) : t.value.toFixed(3)}</div>
          <div className="text-[11px] text-muted-foreground">{t.hint}</div>
        </div>
      ))}
    </div>
  );
}

export interface ShapExplanationViewProps {
  explanation: DecisionExplanation | null | undefined;
  shap: ShapExplanation | null | undefined;
  /** Hide the outer card (used inside the memo section). */
  bare?: boolean;
  className?: string;
}

/**
 * "Why this decision" — the linguistic answer, the policy checks with their margins, and
 * the SHAP contributions (chart + table) that explain the model's risk score.
 */
export function ShapExplanationView({ explanation, shap, bare, className }: ShapExplanationViewProps) {
  const [showMath, setShowMath] = useState(false);
  const [showAll, setShowAll] = useState(false);
  if (!explanation && !shap) {
    return <p className="text-sm text-muted-foreground">No explanation recorded for this run.</p>;
  }
  const rows = shap ? (showAll ? shap.contributions : shap.contributions.slice(0, 8)) : [];

  const body = (
    <div className="flex flex-col gap-6">
      {explanation ? (
        <div className="rounded-lg border border-primary/25 bg-primary-soft/40 p-4">
          <div className="flex items-start gap-3">
            <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground">
              <MessageSquareText className="h-4 w-4" />
            </span>
            <div className="min-w-0">
              <p className="text-[15px] font-semibold leading-snug">{explanation.headline}</p>
              <ul className="mt-2 space-y-1.5 text-sm leading-relaxed text-foreground/90">
                {explanation.sentences.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ul>
              <div className="mt-3 flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
                <Badge variant={explanation.generated_by === "template" ? "muted" : "brand"} className="font-mono text-[10px]">
                  words: {explanation.generated_by}
                </Badge>
                {explanation.llm_error ? <span>model unavailable, template used</span> : null}
              </div>
            </div>
          </div>
        </div>
      ) : null}

      {explanation?.policy_checks?.length ? (
        <div>
          <div className="eyebrow mb-2">Policy tests (these decide the outcome)</div>
          <ul className="divide-y rounded-md border">
            {explanation.policy_checks.map((c) => (
              <li key={c.code} className="flex items-center gap-3 px-3 py-2 text-sm">
                <span
                  className={cn(
                    "flex h-6 w-6 shrink-0 items-center justify-center rounded-full",
                    c.passed ? "bg-success-soft text-success" : "bg-danger-soft text-danger"
                  )}
                >
                  {c.passed ? <Check className="h-3.5 w-3.5" /> : <X className="h-3.5 w-3.5" />}
                </span>
                <span className="w-28 shrink-0 font-medium">{c.check}</span>
                <span className="min-w-0 flex-1 text-foreground/85 tnum">{c.display}</span>
                <Badge variant={c.passed ? "success" : "danger"} className="shrink-0">
                  {c.passed ? "pass" : "fail"}
                </Badge>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {shap ? (
        <div className="flex flex-col gap-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="eyebrow">SHAP contributions to the risk score (supporting signal)</div>
            <span className="text-[11px] text-muted-foreground">{METHOD_LABEL[shap.method] ?? shap.method}</span>
          </div>
          <WaterfallStrip shap={shap} />
          <ShapChart shap={shap} />
          <div className="overflow-hidden rounded-md border">
            <table className="w-full text-sm">
              <thead className="bg-muted/60 text-[11px] uppercase tracking-[0.12em] text-muted-foreground">
                <tr>
                  <th className="px-3 py-2 text-left font-semibold">Feature</th>
                  <th className="px-3 py-2 text-right font-semibold">Value</th>
                  <th className="px-3 py-2 text-right font-semibold">Baseline</th>
                  <th className="px-3 py-2 text-right font-semibold">φ (SHAP)</th>
                  <th className="hidden px-3 py-2 text-right font-semibold sm:table-cell">Share</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {rows.map((r) => (
                  <tr key={r.feature} className="hover:bg-accent/40">
                    <td className="px-3 py-2">
                      <div className="font-medium">{r.label}</div>
                      <div className="font-mono text-[11px] text-muted-foreground">{r.feature}</div>
                    </td>
                    <td className="px-3 py-2 text-right tnum">{r.value_display}</td>
                    <td className="px-3 py-2 text-right text-muted-foreground tnum">{r.baseline_display}</td>
                    <td className="px-3 py-2 text-right">
                      <span
                        className={cn(
                          "rounded-md px-2 py-0.5 font-mono text-xs font-semibold tnum",
                          r.direction === "raises" && "bg-danger-soft text-danger",
                          r.direction === "lowers" && "bg-success-soft text-success",
                          r.direction === "neutral" && "bg-muted text-muted-foreground"
                        )}
                      >
                        {phi(r.shap)}
                      </span>
                    </td>
                    <td className="hidden px-3 py-2 text-right sm:table-cell">
                      <div className="ml-auto flex w-24 items-center gap-2">
                        <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
                          <div
                            className={cn("h-full rounded-full", r.direction === "raises" ? "bg-danger" : r.direction === "lowers" ? "bg-success" : "bg-muted-foreground/40")}
                            style={{ width: `${Math.round(r.share * 100)}%` }}
                          />
                        </div>
                        <span className="w-9 text-right text-xs text-muted-foreground tnum">{formatNumber(r.share * 100, 0)}%</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {shap.contributions.length > 8 ? (
            <button type="button" onClick={() => setShowAll((v) => !v)} className="self-start text-xs font-medium text-primary hover:underline">
              {showAll ? "Show top 8 only" : `Show all ${shap.contributions.length} features`}
            </button>
          ) : null}
        </div>
      ) : null}

      {explanation?.math_lines?.length ? (
        <div>
          <button
            type="button"
            onClick={() => setShowMath((v) => !v)}
            className="inline-flex items-center gap-1 rounded-md px-1.5 py-1 text-xs font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
            aria-expanded={showMath}
          >
            {showMath ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
            <Sigma className="h-3.5 w-3.5" /> Show the arithmetic
          </button>
          {showMath ? (
            <pre className="mt-2 overflow-auto rounded-md border bg-[hsl(var(--sidebar))] p-3.5 font-mono text-[12px] leading-relaxed text-[hsl(var(--sidebar-foreground))]">
              {explanation.math_lines.join("\n")}
            </pre>
          ) : null}
        </div>
      ) : null}
    </div>
  );

  if (bare) return <div className={className}>{body}</div>;
  return (
    <Card className={className}>
      <CardHeader>
        <SectionHeading
          icon={<Sigma />}
          title="Why this decision"
          description="Policy margins decide the outcome; SHAP values show which of this borrower's features move the model's risk score and by how much."
        />
      </CardHeader>
      <CardContent>{body}</CardContent>
    </Card>
  );
}
