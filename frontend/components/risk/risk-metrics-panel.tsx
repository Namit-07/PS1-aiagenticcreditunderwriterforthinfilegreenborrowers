"use client";

import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { Stat, StatGrid } from "@/components/ui/stat";
import type { RiskMetrics } from "@/lib/types";
import { cn } from "@/lib/utils";

function pct(v: number | null | undefined, digits = 2): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return `${(v * 100).toFixed(digits)}%`;
}

function num(v: number | null | undefined, digits = 3): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return v.toFixed(digits);
}

function Cell({ label, value, variant }: { label: string; value: number; variant: string }) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-lg border py-3 text-[15px] font-semibold tnum",
        variant
      )}
    >
      <span className="text-[11px] uppercase tracking-wide opacity-70">{label}</span>
      <span className="mt-0.5">{value}</span>
    </div>
  );
}

function RocCurve({ metrics }: { metrics: RiskMetrics }) {
  const pts = (metrics.roc_points ?? []).map((p) => ({ x: p.fpr, tpr: p.tpr, chance: p.fpr }));
  if (pts.length === 0) {
    return <EmptyState title="No ROC points" description="The model returned no curve data." />;
  }
  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={pts} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
          <CartesianGrid stroke="hsl(var(--border))" strokeDasharray="3 3" />
          <XAxis
            dataKey="x"
            domain={[0, 1]}
            tickLine={false}
            axisLine={false}
            tickMargin={8}
            tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
          />
          <YAxis
            domain={[0, 1]}
            tickLine={false}
            axisLine={false}
            width={40}
            tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
          />
          <Tooltip
            labelFormatter={(l) => `FPR ${num(Number(l), 2)}`}
            contentStyle={{
              background: "hsl(var(--popover))",
              border: "1px solid hsl(var(--border))",
              borderRadius: 10,
              color: "hsl(var(--popover-foreground))",
              fontSize: 12,
              padding: "8px 12px",
            }}
            itemStyle={{ padding: 0, fontVariantNumeric: "tabular-nums" }}
          />
          <Line dataKey="chance" name="Chance (0.5)" stroke="hsl(var(--border))" strokeDasharray="5 4" dot={false} />
          <Line
            dataKey="tpr"
            name="Model"
            stroke="hsl(var(--primary))"
            strokeWidth={2.5}
            dot={{ fill: "hsl(var(--primary))", r: 3 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
export function RiskMetricsPanel({ metrics }: { metrics: RiskMetrics | null }) {
  if (!metrics) {
    return (
      <EmptyState
        title="No risk-model metrics"
        description="Start the AI service (or run an underwrite) to see model evaluation scores."
      />
    );
  }

  const cm = metrics.confusion_matrix;

  return (
    <div className="flex flex-col gap-6">
      {/* Header badges */}
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant={metrics.backend === "xgboost" ? "brand" : "outline"} className="font-mono text-[11px]">
          backend: {metrics.backend}
        </Badge>
        <Badge variant="outline" className="font-mono text-[11px]">
          {metrics.model_version}
        </Badge>
        {metrics.data_version ? (
          <Badge variant="muted" className="font-mono text-[11px]">
            {metrics.data_version}
          </Badge>
        ) : null}
        <Badge variant="muted" className="font-mono text-[11px]">
          positive: {metrics.positive_class} ≥ {metrics.threshold}
        </Badge>
        <Badge variant="muted" className="font-mono text-[11px]">
          n = {metrics.n_samples}
        </Badge>
      </div>

      {/* Primary metric cards */}
      <StatGrid>
        <Stat label="Accuracy" value={pct(metrics.accuracy)} hint="Correctly classified" />
        <Stat label="Precision" value={pct(metrics.precision)} hint="tp / (tp + fp)" />
        <Stat label="Recall (sensitivity)" value={pct(metrics.recall_sensitivity)} hint="tp / (tp + fn)" />
        <Stat label="Specificity" value={pct(metrics.specificity)} hint="tn / (tn + fp)" />
        <Stat label="F1 score" value={pct(metrics.f1_score)} hint="Harmonic mean P & R" />
        <Stat label="ROC AUC" value={num(metrics.roc_auc)} hint="0.5 = random" />
        <Stat label="Matthews CC" value={num(metrics.matthews_cc)} hint="−1 .. +1" />
        <Stat label="Youden index" value={num(metrics.youden_index)} hint="sens + spec − 1" />
        <Stat label="NPV" value={pct(metrics.npv)} hint="tn / (tn + fn)" />
        <Stat label="False positive rate" value={pct(metrics.fpr)} hint="1 − specificity" />
        <Stat label="Prevalence" value={pct(metrics.prevalence)} hint="Positives / n" />
        <Stat label="Backend" value={metrics.backend} hint={metrics.model_version} />
      </StatGrid>

      <div className="grid items-stretch gap-6 lg:grid-cols-2">
        {/* Confusion matrix */}
        <div className="flex flex-col gap-3 rounded-lg border bg-card p-5">
          <div className="flex items-baseline justify-between">
            <h3 className="text-[15px] font-semibold tracking-tight">Confusion matrix</h3>
            <span className="text-xs text-muted-foreground">rows = actual · cols = predicted</span>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <Cell label="TN" value={cm.tn} variant="bg-success/15 text-success" />
            <Cell label="FP" value={cm.fp} variant="bg-danger/15 text-danger" />
            <Cell label="FN" value={cm.fn} variant="bg-warning/15 text-warning" />
            <Cell label="TP" value={cm.tp} variant="bg-primary/15 text-primary" />
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            {cm.tp + cm.fn} actually risky · model flagged {cm.tp + cm.fp} · {metrics.n_samples} evaluated.
          </p>
        </div>

        {/* ROC curve */}
        <div className="flex flex-col gap-3 rounded-lg border bg-card p-5">
          <div className="flex items-baseline justify-between">
            <h3 className="text-[15px] font-semibold tracking-tight">ROC curve</h3>
            <span className="text-xs text-muted-foreground">
              AUC = <span className="font-semibold tnum">{num(metrics.roc_auc)}</span>
            </span>
          </div>
          <RocCurve metrics={metrics} />
        </div>
      </div>

      {metrics.note ? <p className="text-xs leading-relaxed text-muted-foreground">{metrics.note}</p> : null}
    </div>
  );
}