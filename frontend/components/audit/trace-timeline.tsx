"use client";

import { useState } from "react";
import { Braces, ChevronDown, ChevronRight, History } from "lucide-react";

import { Badge, type BadgeVariant } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { JsonView } from "@/components/ui/json-view";
import type { TraceStep } from "@/lib/types";
import { cn, formatDateTime, humanize } from "@/lib/utils";

function eventVariant(type: string): "success" | "danger" | "warning" | "info" | "secondary" {
  const t = type.toLowerCase();
  if (t.includes("error") || t.includes("fail")) return "danger";
  if (t.includes("pause") || t.includes("human") || t.includes("await")) return "warning";
  if (t.includes("complete") || t.includes("end") || t.includes("finish") || t.includes("decision")) return "success";
  if (t.includes("start") || t.includes("begin")) return "info";
  return "secondary";
}

const BUBBLE: Record<ReturnType<typeof eventVariant>, string> = {
  success: "border-success/40 bg-success-soft text-success",
  danger: "border-danger/40 bg-danger-soft text-danger",
  warning: "border-warning/40 bg-warning-soft text-warning",
  info: "border-info/40 bg-info-soft text-info",
  secondary: "border-border bg-card text-muted-foreground",
};

export function TraceTimeline({ steps }: { steps: TraceStep[] }) {
  const [open, setOpen] = useState<Record<number, boolean>>({});
  if (steps.length === 0) return <EmptyState icon={<History />} title="No trace steps recorded" />;

  return (
    <ol className="relative flex flex-col">
      <span className="absolute bottom-3 left-[15px] top-3 w-px bg-border" aria-hidden="true" />
      {steps.map((s, i) => {
        const expanded = Boolean(open[s.sequence]);
        const hasPayload = s.payload && Object.keys(s.payload).length > 0;
        const variant: BadgeVariant = eventVariant(s.event_type);
        const payloadKeys = hasPayload ? Object.keys(s.payload).length : 0;
        return (
          <li key={s.sequence} className={cn("relative flex gap-4 pb-4 last:pb-0", i === 0 && "animate-in-up")}>
            <span
              className={cn(
                "relative z-10 mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border-2 text-[11px] font-semibold tnum shadow-sm",
                BUBBLE[variant]
              )}
              aria-label={`Step ${s.sequence}`}
            >
              {s.sequence}
            </span>
            <div className="min-w-0 flex-1 rounded-lg border bg-card shadow-card">
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 px-4 py-3">
                <span className="text-sm font-semibold">{humanize(s.agent)}</span>
                <Badge variant={variant} dot>
                  {s.event_type}
                </Badge>
                <span className="text-xs text-muted-foreground tnum">{formatDateTime(s.timestamp)}</span>
                {hasPayload ? (
                  <button
                    type="button"
                    onClick={() => setOpen((o) => ({ ...o, [s.sequence]: !expanded }))}
                    className={cn(
                      "ml-auto inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium transition-colors",
                      expanded ? "bg-primary-soft text-primary" : "text-muted-foreground hover:bg-accent hover:text-foreground"
                    )}
                    aria-expanded={expanded}
                  >
                    {expanded ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
                    <Braces className="h-3.5 w-3.5" />
                    payload
                    <span className="rounded-full bg-muted px-1.5 text-[10px] tnum">{payloadKeys}</span>
                  </button>
                ) : null}
              </div>
              {expanded && hasPayload ? (
                <div className="border-t bg-muted/30 p-3">
                  <JsonView value={s.payload} />
                </div>
              ) : null}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
