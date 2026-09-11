import { SeverityBadge } from "@/components/applications/status-badge";
import type { Reason } from "@/lib/types";
import { cn } from "@/lib/utils";

const RAIL: Record<string, string> = {
  blocker: "bg-danger",
  warning: "bg-warning",
  info: "bg-info",
};

export function ReasonsList({ reasons, emptyText = "No reasons recorded." }: { reasons: Reason[]; emptyText?: string }) {
  if (!reasons || reasons.length === 0) {
    return <p className="rounded-md border border-dashed px-3 py-4 text-center text-sm text-muted-foreground">{emptyText}</p>;
  }
  return (
    <ul className="divide-y overflow-hidden rounded-md border">
      {reasons.map((r, i) => (
        <li key={`${r.code}-${i}`} className="relative flex items-start gap-3 py-2.5 pl-4 pr-3 text-sm">
          <span aria-hidden="true" className={cn("absolute inset-y-0 left-0 w-[3px]", RAIL[r.severity] ?? "bg-border")} />
          <div className="shrink-0 pt-px">
            <SeverityBadge severity={r.severity} />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
              <span className="font-mono text-xs font-semibold tracking-tight">{r.code}</span>
              {r.field ? (
                <span className="rounded bg-muted px-1.5 py-px font-mono text-[10px] text-muted-foreground">{r.field}</span>
              ) : null}
            </div>
            {r.message ? <div className="mt-0.5 text-[13px] leading-relaxed text-foreground/85">{r.message}</div> : null}
          </div>
        </li>
      ))}
    </ul>
  );
}
