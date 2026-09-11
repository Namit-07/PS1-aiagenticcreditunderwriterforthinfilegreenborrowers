import { AlertCircle, Check, Loader2, Minus, Pause } from "lucide-react";

import { NODE_ORDER, type NodeStatus, type NodeStatusValue, type RunStatus } from "@/lib/types";
import { cn, formatDuration, humanize } from "@/lib/utils";

type VisualStatus = NodeStatusValue | "running";

const CIRCLE: Record<VisualStatus, string> = {
  pending: "border-border bg-card text-muted-foreground",
  running: "border-info bg-info text-white pulse-ring",
  ok: "border-success bg-success text-white",
  paused: "border-warning bg-warning text-white",
  error: "border-danger bg-danger text-white",
  skipped: "border-border bg-muted text-muted-foreground",
};

const LABEL: Record<VisualStatus, string> = {
  pending: "text-muted-foreground",
  running: "text-info",
  ok: "text-success",
  paused: "text-warning",
  error: "text-danger",
  skipped: "text-muted-foreground",
};

const STATUS_TEXT: Record<VisualStatus, string> = {
  pending: "Pending",
  running: "Running",
  ok: "Done",
  paused: "Paused",
  error: "Error",
  skipped: "Skipped",
};

function CircleGlyph({ status, index }: { status: VisualStatus; index: number }) {
  switch (status) {
    case "ok":
      return <Check className="h-4 w-4" strokeWidth={3} />;
    case "running":
      return <Loader2 className="h-4 w-4 animate-spin" />;
    case "paused":
      return <Pause className="h-4 w-4" strokeWidth={3} />;
    case "error":
      return <AlertCircle className="h-4 w-4" />;
    case "skipped":
      return <Minus className="h-4 w-4" />;
    default:
      return <span className="text-xs font-semibold tnum">{index + 1}</span>;
  }
}

interface Step {
  name: string;
  index: number;
  status: VisualStatus;
  duration?: number;
}

/**
 * Renders the ordered workflow nodes. Falls back to the contract's NODE_ORDER when the
 * run has not reported nodes yet. Marks the first pending node as "running" while the run runs.
 */
export function NodeStepper({ nodes, runStatus }: { nodes: NodeStatus[]; runStatus: RunStatus }) {
  const byName = new Map(nodes.map((n) => [n.name, n]));
  const names = nodes.length > 0 ? nodes.map((n) => n.name) : [...NODE_ORDER];
  const firstPending = names.find((n) => (byName.get(n)?.status ?? "pending") === "pending");

  const steps: Step[] = names.map((name, index) => {
    const node = byName.get(name);
    const raw: NodeStatusValue = node?.status ?? "pending";
    const running = runStatus === "running" && raw === "pending" && name === firstPending;
    return { name, index, status: running ? "running" : raw, duration: node?.duration_ms };
  });

  const done = steps.filter((s) => s.status === "ok").length;
  const totalMs = steps.reduce((acc, s) => acc + (s.duration ?? 0), 0);
  const hasTiming = steps.some((s) => s.duration !== undefined);

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
        <span>
          <span className="font-semibold text-foreground tnum">{done}</span> of{" "}
          <span className="tnum">{steps.length}</span> nodes complete
        </span>
        {hasTiming ? (
          <span>
            Total compute <span className="font-medium text-foreground tnum">{formatDuration(totalMs)}</span>
          </span>
        ) : null}
      </div>

      {/* Horizontal timeline (desktop) */}
      <ol className="hidden lg:grid" style={{ gridTemplateColumns: `repeat(${steps.length}, minmax(0, 1fr))` }} aria-label="Workflow nodes">
        {steps.map((s, i) => {
          const prev = steps[i - 1];
          const inFilled = prev?.status === "ok";
          const outFilled = s.status === "ok";
          return (
            <li key={s.name} className="relative flex flex-col items-center px-1 text-center">
              {/* connector: left half + right half so fills align with completion */}
              {i > 0 ? (
                <span
                  aria-hidden="true"
                  className={cn("absolute left-0 top-[17px] h-0.5 w-1/2 transition-colors duration-500", inFilled ? "bg-success" : "bg-border")}
                />
              ) : null}
              {i < steps.length - 1 ? (
                <span
                  aria-hidden="true"
                  className={cn("absolute right-0 top-[17px] h-0.5 w-1/2 transition-colors duration-500", outFilled ? "bg-success" : "bg-border")}
                />
              ) : null}
              <span
                className={cn(
                  "relative z-10 flex h-9 w-9 items-center justify-center rounded-full border-2 transition-colors duration-300",
                  CIRCLE[s.status]
                )}
                aria-hidden="true"
              >
                <CircleGlyph status={s.status} index={s.index} />
              </span>
              <div className="mt-2.5 min-w-0 max-w-full">
                <div className="text-[11px] font-semibold leading-tight text-foreground [overflow-wrap:anywhere]">{humanize(s.name)}</div>
                <div className={cn("mt-1 text-[10px] font-medium uppercase tracking-wide", LABEL[s.status])}>
                  {STATUS_TEXT[s.status]}
                </div>
                {s.duration !== undefined ? (
                  <div className="text-[10px] text-muted-foreground tnum">{formatDuration(s.duration)}</div>
                ) : null}
              </div>
            </li>
          );
        })}
      </ol>

      {/* Vertical list (mobile / tablet) */}
      <ol className="flex flex-col lg:hidden" aria-label="Workflow nodes">
        {steps.map((s, i) => {
          const last = i === steps.length - 1;
          return (
            <li key={s.name} className="relative flex gap-3 pb-4 last:pb-0">
              {!last ? (
                <span
                  aria-hidden="true"
                  className={cn("absolute left-[17px] top-9 h-[calc(100%-2.25rem)] w-0.5", s.status === "ok" ? "bg-success" : "bg-border")}
                />
              ) : null}
              <span
                className={cn(
                  "relative z-10 flex h-9 w-9 shrink-0 items-center justify-center rounded-full border-2",
                  CIRCLE[s.status]
                )}
                aria-hidden="true"
              >
                <CircleGlyph status={s.status} index={s.index} />
              </span>
              <div
                className={cn(
                  "flex min-w-0 flex-1 items-center justify-between gap-3 rounded-md border px-3 py-2",
                  s.status === "running" && "border-info/40 bg-info-soft",
                  s.status === "paused" && "border-warning/40 bg-warning-soft",
                  s.status === "error" && "border-danger/40 bg-danger-soft",
                  s.status === "ok" && "bg-card",
                  (s.status === "pending" || s.status === "skipped") && "border-dashed bg-transparent"
                )}
              >
                <div className="min-w-0">
                  <div className="truncate text-sm font-medium">
                    <span className="mr-1.5 text-muted-foreground tnum">{s.index + 1}.</span>
                    {humanize(s.name)}
                  </div>
                  <div className={cn("text-[11px] font-medium uppercase tracking-wide", LABEL[s.status])}>{STATUS_TEXT[s.status]}</div>
                </div>
                {s.duration !== undefined ? (
                  <span className="shrink-0 text-xs text-muted-foreground tnum">{formatDuration(s.duration)}</span>
                ) : null}
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
