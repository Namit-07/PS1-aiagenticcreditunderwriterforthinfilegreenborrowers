import { CheckCircle2, Loader2, UserCheck, XCircle } from "lucide-react";

import { DecisionBadge } from "@/components/applications/status-badge";
import type { RunState } from "@/lib/types";
import { cn, formatDateTime, formatPercent } from "@/lib/utils";

type Tone = "info" | "warning" | "success" | "danger";

const STRIP: Record<Tone, string> = {
  info: "border-info/30 bg-info-soft",
  warning: "border-warning/40 bg-warning-soft",
  success: "border-success/30 bg-success-soft",
  danger: "border-danger/30 bg-danger-soft",
};

const TILE: Record<Tone, string> = {
  info: "bg-info text-white",
  warning: "bg-warning text-white",
  success: "bg-success text-white",
  danger: "bg-danger text-white",
};

const TEXT: Record<Tone, string> = {
  info: "text-info",
  warning: "text-warning",
  success: "text-success",
  danger: "text-danger",
};

function Strip({
  tone,
  icon,
  eyebrow,
  title,
  message,
  aside,
  pulse,
}: {
  tone: Tone;
  icon: React.ReactNode;
  eyebrow: string;
  title: string;
  message: React.ReactNode;
  aside?: React.ReactNode;
  pulse?: boolean;
}) {
  return (
    <div
      role="status"
      aria-live="polite"
      className={cn("flex flex-wrap items-center gap-4 rounded-lg border px-4 py-4 sm:px-5", STRIP[tone])}
    >
      <span
        className={cn(
          "flex h-11 w-11 shrink-0 items-center justify-center rounded-lg shadow-sm [&_svg]:h-5 [&_svg]:w-5",
          TILE[tone],
          pulse && "pulse-ring"
        )}
        aria-hidden="true"
      >
        {icon}
      </span>
      <div className="min-w-0 flex-1">
        <div className={cn("eyebrow", TEXT[tone])}>{eyebrow}</div>
        <div className="text-lg font-semibold leading-tight tracking-tight sm:text-xl">{title}</div>
        <div className="mt-1 text-[13px] text-foreground/80">{message}</div>
      </div>
      {aside ? <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto">{aside}</div> : null}
    </div>
  );
}

export function RunStatusBanner({ state }: { state: RunState }) {
  switch (state.status) {
    case "created":
    case "running":
      return (
        <Strip
          tone="info"
          pulse
          icon={<Loader2 className="animate-spin" />}
          eyebrow="Run in progress"
          title="The agent workflow is executing"
          message="Nodes run in order; the page auto-refreshes every 1.5 s until the run settles."
          aside={
            <span className="inline-flex items-center gap-2 rounded-full border border-info/30 bg-card px-3 py-1 text-xs font-medium text-info">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-info opacity-60" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-info" />
              </span>
              Live · auto-refreshing every 1.5 s
            </span>
          }
        />
      );
    case "awaiting_human": {
      const n = state.low_confidence.length;
      return (
        <Strip
          tone="warning"
          icon={<UserCheck />}
          eyebrow="Paused for human review"
          title={`${n} field${n === 1 ? "" : "s"} need${n === 1 ? "s" : ""} a reviewer`}
          message="Extraction confidence fell below the policy threshold. Review each field below to resume the run."
          aside={
            <span className="rounded-full border border-warning/40 bg-card px-3 py-1 text-xs font-medium text-warning">
              Waiting on you
            </span>
          }
        />
      );
    }
    case "completed":
      return (
        <Strip
          tone="success"
          icon={<CheckCircle2 />}
          eyebrow="Run completed"
          title="Decision issued"
          message={
            <>
              {state.confidence !== null ? (
                <>
                  Confidence <span className="font-semibold text-foreground tnum">{formatPercent(state.confidence)}</span>
                </>
              ) : (
                "Confidence not reported"
              )}
              {state.updated_at ? (
                <>
                  {" "}
                  · finished <span className="tnum">{formatDateTime(state.updated_at)}</span>
                </>
              ) : null}
            </>
          }
          aside={<DecisionBadge decision={state.decision} className="px-3 py-1 text-sm" />}
        />
      );
    case "failed":
      return (
        <Strip
          tone="danger"
          icon={<XCircle />}
          eyebrow="Run failed"
          title="The workflow reported an error"
          message={
            <span className="font-mono text-xs [overflow-wrap:anywhere]">
              {state.error ?? "No error detail was returned. Check the audit trace for the failing step."}
            </span>
          }
        />
      );
    default:
      return null;
  }
}
