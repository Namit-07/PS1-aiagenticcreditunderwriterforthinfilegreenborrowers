import { FileText, GitCompareArrows, Hash, Scale } from "lucide-react";

import { ReconSeverityBadge } from "@/components/applications/status-badge";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import type { Reconciliation } from "@/lib/types";
import { cn, formatNumber, humanize } from "@/lib/utils";

const SEVERITY_RAIL: Record<string, string> = {
  LOW: "before:bg-info",
  MEDIUM: "before:bg-warning",
  HIGH: "before:bg-danger",
};

function mismatchTone(pct: number): { text: string; bg: string; label: string } {
  if (pct >= 20) return { text: "text-danger", bg: "bg-danger-soft", label: "High mismatch" };
  if (pct >= 10) return { text: "text-warning", bg: "bg-warning-soft", label: "Moderate mismatch" };
  return { text: "text-success", bg: "bg-success-soft", label: "Within tolerance" };
}

function Column({ icon, label, children }: { icon: React.ReactNode; label: string; children: React.ReactNode }) {
  return (
    <div className="min-w-0 rounded-md bg-muted/40 p-3">
      <div className="mb-1.5 flex items-center gap-1.5 [&_svg]:h-3.5 [&_svg]:w-3.5 [&_svg]:text-muted-foreground">
        {icon}
        <span className="eyebrow">{label}</span>
      </div>
      {children}
    </div>
  );
}

export function ReconciliationList({ reconciliation }: { reconciliation: Reconciliation | null | undefined }) {
  const items = reconciliation?.items ?? [];
  const mismatch = reconciliation?.income_mismatch_percentage ?? null;
  const tone = mismatch !== null ? mismatchTone(mismatch) : null;

  return (
    <div className="flex flex-col gap-4">
      {mismatch !== null && tone ? (
        <div className="flex flex-wrap items-center gap-4 rounded-lg border bg-muted/30 p-4">
          <div className={cn("flex h-11 w-11 shrink-0 items-center justify-center rounded-md", tone.bg, tone.text)}>
            <Scale className="h-5 w-5" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="text-sm font-semibold">Income mismatch across documents</div>
            <div className="text-xs text-muted-foreground">Difference between declared / platform / bank-derived income.</div>
          </div>
          <div className="flex flex-col items-end">
            <div className={cn("text-3xl font-bold leading-none tracking-tight tnum", tone.text)}>
              {formatNumber(mismatch, 1)}
              <span className="text-lg font-semibold">%</span>
            </div>
            <div className="mt-1 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">{tone.label}</div>
          </div>
        </div>
      ) : null}

      {items.length === 0 ? (
        <EmptyState
          icon={<GitCompareArrows />}
          title="No reconciliation issues"
          description="Values across the uploaded documents agree within tolerance."
        />
      ) : (
        <ul className="flex flex-col gap-3">
          {items.map((it, i) => (
            <li
              key={`${it.type}-${i}`}
              className={cn(
                "relative overflow-hidden rounded-lg border bg-card p-4 pl-5 shadow-card before:absolute before:inset-y-0 before:left-0 before:w-1 before:content-['']",
                SEVERITY_RAIL[it.severity] ?? "before:bg-muted-foreground/40"
              )}
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex flex-wrap items-center gap-2">
                  <ReconSeverityBadge severity={it.severity} />
                  <span className="text-sm font-semibold">{humanize(it.type)}</span>
                </div>
                {it.mismatch_percentage !== undefined ? (
                  <Badge variant="outline" className="tnum">
                    mismatch {formatNumber(it.mismatch_percentage, 1)}%
                  </Badge>
                ) : null}
              </div>
              <p className="mt-2 text-sm leading-relaxed text-foreground/90">{it.description}</p>
              <div className="mt-3 grid gap-2 text-xs sm:grid-cols-3">
                <Column icon={<FileText />} label="Documents">
                  <ul className="space-y-1">
                    {it.documents.length ? (
                      it.documents.map((d) => (
                        <li key={d} className="truncate" title={d}>
                          {d}
                        </li>
                      ))
                    ) : (
                      <li className="text-muted-foreground">—</li>
                    )}
                  </ul>
                </Column>
                <Column icon={<Hash />} label="Evidence values">
                  <ul className="space-y-1">
                    {it.evidence.length ? (
                      it.evidence.map((e, j) => (
                        <li key={j} className="break-all font-mono text-[11px] tnum">
                          {e}
                        </li>
                      ))
                    ) : (
                      <li className="text-muted-foreground">—</li>
                    )}
                  </ul>
                </Column>
                <Column icon={<GitCompareArrows />} label="Impact">
                  <p className="leading-relaxed">{it.impact || "—"}</p>
                </Column>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
