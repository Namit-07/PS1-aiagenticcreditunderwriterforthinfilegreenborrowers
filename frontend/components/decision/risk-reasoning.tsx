import { Brain, CircleHelp, ShieldAlert, ThumbsUp, type LucideIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import type { RiskReasoning } from "@/lib/types";
import { cn } from "@/lib/utils";

type Tone = "success" | "danger" | "warning";

const COLUMN: Record<Tone, { wrap: string; head: string; bullet: string }> = {
  success: { wrap: "border-success/30 bg-success-soft", head: "text-success", bullet: "bg-success" },
  danger: { wrap: "border-danger/30 bg-danger-soft", head: "text-danger", bullet: "bg-danger" },
  warning: { wrap: "border-warning/40 bg-warning-soft", head: "text-warning", bullet: "bg-warning" },
};

function Column({ tone, icon: Icon, title, items, empty }: { tone: Tone; icon: LucideIcon; title: string; items: string[]; empty: string }) {
  const c = COLUMN[tone];
  return (
    <section className={cn("rounded-lg border p-4", c.wrap)}>
      <h4 className={cn("mb-3 flex items-center justify-between gap-2 text-sm font-semibold", c.head)}>
        <span className="inline-flex items-center gap-1.5">
          <Icon className="h-4 w-4" /> {title}
        </span>
        <span className="rounded-full bg-card px-2 py-px text-[11px] font-semibold tnum">{items?.length ?? 0}</span>
      </h4>
      {!items || items.length === 0 ? (
        <p className="text-sm text-muted-foreground">{empty}</p>
      ) : (
        <ul className="flex flex-col gap-2 text-sm">
          {items.map((s, i) => (
            <li key={i} className="flex items-start gap-2.5 leading-relaxed text-foreground/90">
              <span aria-hidden="true" className={cn("mt-2 h-1.5 w-1.5 shrink-0 rounded-full", c.bullet)} />
              <span>{s}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

const LEVEL_TONE: Record<string, "success" | "warning" | "danger" | "outline"> = {
  LOW: "success",
  MEDIUM: "warning",
  HIGH: "danger",
  low: "success",
  medium: "warning",
  high: "danger",
};

export function RiskReasoningView({ reasoning }: { reasoning: RiskReasoning | null }) {
  if (!reasoning) {
    return (
      <p className="rounded-md border border-dashed px-3 py-6 text-center text-sm text-muted-foreground">
        No AI reasoning recorded for this run.
      </p>
    );
  }
  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <span className="eyebrow">Assessed risk level</span>
        <Badge variant={LEVEL_TONE[reasoning.risk_level] ?? "outline"} dot>
          {reasoning.risk_level}
        </Badge>
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        <Column tone="success" icon={ThumbsUp} title="Strengths" items={reasoning.strengths} empty="None noted." />
        <Column tone="danger" icon={ShieldAlert} title="Risks" items={reasoning.risks} empty="None noted." />
        <Column tone="warning" icon={CircleHelp} title="Uncertainties" items={reasoning.uncertainties} empty="None noted." />
      </div>
      <section>
        <h4 className="mb-3 flex items-center gap-2 text-sm font-semibold">
          <span className="flex h-7 w-7 items-center justify-center rounded-md bg-primary-soft text-primary">
            <Brain className="h-4 w-4" />
          </span>
          Reasoning steps
        </h4>
        {reasoning.reasoning.length ? (
          <ol className="flex flex-col gap-2">
            {reasoning.reasoning.map((s, i) => (
              <li key={i} className="flex items-start gap-3 rounded-md border bg-card px-3.5 py-2.5 text-sm leading-relaxed">
                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary text-[11px] font-semibold text-primary-foreground tnum">
                  {i + 1}
                </span>
                <span className="text-foreground/90">{s}</span>
              </li>
            ))}
          </ol>
        ) : (
          <p className="text-sm text-muted-foreground">No reasoning steps.</p>
        )}
      </section>
      {reasoning.evidence_refs.length ? (
        <section>
          <h4 className="eyebrow mb-2">Evidence references</h4>
          <div className="flex flex-wrap gap-1.5">
            {reasoning.evidence_refs.map((r, i) => (
              <Badge key={i} variant="secondary" className="font-mono text-[11px]">
                {r}
              </Badge>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
