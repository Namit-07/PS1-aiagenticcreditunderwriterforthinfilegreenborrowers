import type { ReactNode } from "react";
import { Activity, CheckCircle2, Clock, FileText, Redo2, Timer, UserCheck, XCircle } from "lucide-react";

import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { RingMeter } from "@/components/ui/ring-meter";
import type { DashboardStats } from "@/lib/types";
import { cn, formatDuration, formatPercent } from "@/lib/utils";

type Tone = "neutral" | "success" | "danger" | "warning" | "info";

interface Kpi {
  label: string;
  value: ReactNode;
  icon: ReactNode;
  hint?: ReactNode;
  tone: Tone;
}

const TILE: Record<Tone, string> = {
  neutral: "bg-primary-soft text-primary",
  success: "bg-success-soft text-success",
  danger: "bg-danger-soft text-danger",
  warning: "bg-warning-soft text-warning",
  info: "bg-info-soft text-info",
};

const DELAY = ["", "delay-1", "delay-2", "delay-3", "delay-4", "delay-4"];

const ACCENT: Record<Tone, string> = {
  neutral: "bg-primary/70",
  success: "bg-success",
  danger: "bg-danger",
  warning: "bg-warning",
  info: "bg-info",
};

function share(part: number, total: number): string {
  if (!total || !Number.isFinite(part)) return "—";
  return formatPercent(part / total, 0);
}

/** Hero KPI row: one boxed tile per headline number, colour-accented per outcome. */
export function KpiCards({ stats }: { stats: DashboardStats }) {
  const total = stats.total_applications;
  const kpis: Kpi[] = [
    {
      label: "Total applications",
      value: stats.total_applications,
      icon: <FileText />,
      hint: "All loan files in the book",
      tone: "neutral",
    },
    {
      label: "Pending review",
      value: stats.pending_review,
      icon: <Clock />,
      hint: "Not yet decided",
      tone: "info",
    },
    {
      label: "Approved",
      value: stats.approved,
      icon: <CheckCircle2 />,
      hint: `${share(stats.approved, total)} of applications`,
      tone: "success",
    },
    {
      label: "Declined",
      value: stats.declined,
      icon: <XCircle />,
      hint: `${share(stats.declined, total)} of applications`,
      tone: "danger",
    },
    {
      label: "Referred",
      value: stats.referred,
      icon: <Redo2 />,
      hint: `${share(stats.referred, total)} of applications`,
      tone: "warning",
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
      {kpis.map((k, i) => (
        <Card
          key={k.label}
          className={cn("relative flex flex-col overflow-hidden p-4 sm:p-5 animate-in-up", DELAY[i])}
        >
          <span className={cn("absolute inset-x-0 top-0 h-[3px]", ACCENT[k.tone])} aria-hidden="true" />
          <div className="flex items-start justify-between gap-2">
            <span className="eyebrow leading-tight">{k.label}</span>
            <span
              className={cn(
                "flex h-9 w-9 shrink-0 items-center justify-center rounded-md [&_svg]:h-4 [&_svg]:w-4",
                TILE[k.tone]
              )}
            >
              {k.icon}
            </span>
          </div>
          <div className="mt-3 text-[28px] font-bold leading-none tracking-tight tnum sm:text-[30px]">{k.value}</div>
          {k.hint ? <div className="mt-2 text-xs text-muted-foreground">{k.hint}</div> : null}
        </Card>
      ))}

      {/* Approval rate gets a radial gauge instead of an icon tile. */}
      <Card className="relative flex flex-col overflow-hidden p-4 sm:p-5 animate-in-up delay-4">
        <span className="absolute inset-x-0 top-0 h-[3px] bg-brand-gradient" aria-hidden="true" />
        <div className="flex items-start justify-between gap-2">
          <span className="eyebrow leading-tight">Approval rate</span>
          <RingMeter value={stats.approval_rate} tone="good" size={40} stroke={5} className="-mt-1 -mr-1" />
        </div>
        <div className="mt-3 text-[28px] font-bold leading-none tracking-tight tnum sm:text-[30px]">
          {formatPercent(stats.approval_rate)}
        </div>
        <div className="mt-2 text-xs text-muted-foreground">Portfolio approval rate</div>
      </Card>
    </div>
  );
}

interface HealthRow {
  label: string;
  value: ReactNode;
  hint: string;
  icon: ReactNode;
  tone: Tone;
}

/** Compact operational strip built from the run-level stats only. */
export function PipelineHealth({ stats, className }: { stats: DashboardStats; className?: string }) {
  const awaitingShare = stats.runs_total > 0 ? stats.runs_awaiting_human / stats.runs_total : 0;
  const rows: HealthRow[] = [
    {
      label: "Runs total",
      value: stats.runs_total,
      hint: "Underwriting runs executed",
      icon: <Activity />,
      tone: "neutral",
    },
    {
      label: "Awaiting human",
      value: stats.runs_awaiting_human,
      hint: stats.runs_awaiting_human > 0 ? "Paused for a reviewer" : "Nothing waiting on a reviewer",
      icon: <UserCheck />,
      tone: stats.runs_awaiting_human > 0 ? "warning" : "success",
    },
    {
      label: "Avg run duration",
      value: formatDuration(stats.avg_run_duration_ms),
      hint: "Mean wall-clock per run",
      icon: <Timer />,
      tone: "info",
    },
  ];

  return (
    <Card className={cn("flex flex-col", className)}>
      <div className="flex items-center justify-between gap-3 border-b px-5 py-4">
        <div>
          <div className="text-[15px] font-semibold leading-tight tracking-tight">Pipeline health</div>
          <p className="mt-0.5 text-[13px] text-muted-foreground">Agent workflow throughput and hand-offs.</p>
        </div>
        <span className="inline-flex items-center gap-1.5 rounded-full border bg-card px-2.5 py-1 text-[11px] font-medium text-muted-foreground">
          <span
            className={cn(
              "h-1.5 w-1.5 rounded-full",
              stats.runs_awaiting_human > 0 ? "bg-warning" : "bg-success"
            )}
            aria-hidden="true"
          />
          {stats.runs_awaiting_human > 0 ? "Attention" : "Healthy"}
        </span>
      </div>
      <dl className="flex flex-1 flex-col divide-y">
        {rows.map((r) => (
          <div key={r.label} className="flex items-center gap-3 px-5 py-3.5">
            <span
              className={cn(
                "flex h-9 w-9 shrink-0 items-center justify-center rounded-md [&_svg]:h-4 [&_svg]:w-4",
                TILE[r.tone]
              )}
            >
              {r.icon}
            </span>
            <div className="min-w-0 flex-1">
              <dt className="eyebrow">{r.label}</dt>
              <dd className="truncate text-xs text-muted-foreground">{r.hint}</dd>
            </div>
            <dd className="text-xl font-semibold tracking-tight tnum">{r.value}</dd>
          </div>
        ))}
      </dl>
      <div className="border-t bg-muted/40 px-5 py-3">
        <div className="mb-1.5 flex items-center justify-between text-xs">
          <span className="text-muted-foreground">Share of runs awaiting a human</span>
          <span className="font-medium tnum">{formatPercent(awaitingShare, 0)}</span>
        </div>
        <Progress value={awaitingShare} tone={stats.runs_awaiting_human > 0 ? "warn" : "good"} label="Runs awaiting human" />
      </div>
    </Card>
  );
}
