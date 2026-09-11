import { Calendar, FileText, Hash, User } from "lucide-react";

import { DecisionBadge, ReviewStatusBadge } from "@/components/applications/status-badge";
import { FinancialsTable } from "@/components/decision/financials-table";
import { HumanOverrides } from "@/components/decision/human-overrides";
import { ReasonsList } from "@/components/decision/reasons-list";
import { RiskCard } from "@/components/decision/risk-card";
import { RiskReasoningView } from "@/components/decision/risk-reasoning";
import { ShapExplanationView } from "@/components/decision/shap-explanation";
import { ConfidenceBar } from "@/components/evidence/confidence-bar";
import { ApprovalPathCard } from "@/components/what-if/approval-path-card";
import { Badge } from "@/components/ui/badge";
import { JsonView } from "@/components/ui/json-view";
import { RingMeter } from "@/components/ui/ring-meter";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { CreditMemo } from "@/lib/types";
import { cn, confidenceTone, displayValue, formatDateTime, formatPercent, humanize } from "@/lib/utils";

const SECTION_EYEBROW: Record<number, string> = {
  0: "Summary",
  1: "Facts",
  2: "Facts",
  3: "Calculations",
  4: "Model signal",
  5: "Policy",
  6: "AI reasoning",
  7: "Human judgement",
  8: "Outcome",
};

function Section({ n, title, subtitle, children, className }: { n: number; title: string; subtitle: string; children: React.ReactNode; className?: string }) {
  return (
    <section
      className={cn(
        "relative break-inside-avoid overflow-hidden rounded-lg border bg-card shadow-card print:border-0 print:p-0 print:shadow-none",
        className
      )}
    >
      <span className="absolute inset-y-0 left-0 w-1 bg-primary print:hidden" aria-hidden="true" />
      <header className="flex items-start gap-4 border-b px-5 py-4 pl-6 print:px-0 print:pl-0">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-primary-soft font-mono text-sm font-bold text-primary tnum print:border print:bg-transparent">
          {String(n).padStart(2, "0")}
        </span>
        <div className="min-w-0">
          <div className="eyebrow">{SECTION_EYEBROW[n] ?? "Section"}</div>
          <h2 className="mt-0.5 text-base font-semibold leading-tight tracking-tight">{title}</h2>
          <p className="mt-0.5 text-xs text-muted-foreground">{subtitle}</p>
        </div>
      </header>
      <div className="px-5 py-4 pl-6 print:px-0 print:pl-0">{children}</div>
    </section>
  );
}

function isPrimitive(v: unknown) {
  return v === null || ["string", "number", "boolean"].includes(typeof v);
}

function KeyValueGrid({ data }: { data: Record<string, unknown> }) {
  const entries = Object.entries(data ?? {});
  if (entries.length === 0) return <p className="text-sm text-muted-foreground">Nothing recorded.</p>;
  const simple = entries.filter(([, v]) => isPrimitive(v));
  const complex = entries.filter(([, v]) => !isPrimitive(v));
  return (
    <div className="flex flex-col gap-3">
      {simple.length ? (
        <dl className="grid grid-cols-1 gap-x-6 gap-y-0 text-sm sm:grid-cols-2 md:grid-cols-3">
          {simple.map(([k, v]) => (
            <div key={k} className="flex items-baseline justify-between gap-3 border-b border-dashed py-1.5">
              <dt className="truncate text-muted-foreground" title={k}>
                {humanize(k)}
              </dt>
              <dd className="shrink-0 font-medium tnum">{displayValue(v)}</dd>
            </div>
          ))}
        </dl>
      ) : null}
      {complex.length ? <JsonView value={Object.fromEntries(complex)} collapsible="Show details" /> : null}
    </div>
  );
}

function MetaItem({ icon, label, children, mono }: { icon: React.ReactNode; label: string; children: React.ReactNode; mono?: boolean }) {
  return (
    <div className="flex items-start gap-2.5">
      <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground [&_svg]:h-3.5 [&_svg]:w-3.5 print:hidden">
        {icon}
      </span>
      <div className="min-w-0">
        <div className="eyebrow">{label}</div>
        <div className={cn("mt-0.5 break-all text-[13px]", mono ? "font-mono text-xs" : "font-medium")}>{children}</div>
      </div>
    </div>
  );
}

export function CreditMemoView({ memo }: { memo: CreditMemo }) {
  const s = memo.sections;
  const confidence = s.decision?.confidence ?? null;
  return (
    <article className="mx-auto flex w-full max-w-5xl flex-col gap-5 print:max-w-none">
      <header className="animate-in-up overflow-hidden rounded-lg border bg-card shadow-card print:border-0 print:p-0 print:shadow-none">
        <div className="bg-brand-gradient h-2 w-full print:hidden" aria-hidden="true" />
        <div className="flex flex-col gap-5 p-5 sm:p-6 print:p-0">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="min-w-0">
              <div className="eyebrow flex items-center gap-1.5">
                <FileText className="h-3.5 w-3.5" /> Credit memorandum
              </div>
              <h1 className="mt-1.5 text-2xl font-bold leading-tight tracking-tight sm:text-[28px]">{memo.title}</h1>
              <p className="mt-1.5 max-w-2xl text-sm text-muted-foreground">
                Facts, calculations, model signal, AI reasoning, policy and human decisions — recorded in separate sections so
                each can be audited on its own.
              </p>
            </div>
            <div className="flex items-center gap-4 rounded-lg border bg-muted/40 px-4 py-3">
              <RingMeter
                value={confidence ?? 0}
                tone={confidence === null ? "neutral" : confidenceTone(confidence)}
                size={64}
                stroke={6}
                label={<span className="text-sm">{formatPercent(confidence, 0)}</span>}
              />
              <div className="flex flex-col items-start gap-1">
                <span className="eyebrow">Decision</span>
                <DecisionBadge decision={s.decision?.decision} className="px-3 py-1 text-sm" />
                <span className="text-[11px] text-muted-foreground">confidence {formatPercent(confidence)}</span>
              </div>
            </div>
          </div>

          <div className="grid gap-4 border-t pt-4 sm:grid-cols-2 lg:grid-cols-4">
            <MetaItem icon={<Hash />} label="Application" mono>
              {memo.application_id}
            </MetaItem>
            <MetaItem icon={<Hash />} label="Run" mono>
              {memo.run_id}
            </MetaItem>
            <MetaItem icon={<Calendar />} label="Generated at">
              <span className="tnum">{formatDateTime(memo.generated_at)}</span>
            </MetaItem>
            <MetaItem icon={<User />} label="Generated by">
              {memo.generated_by}
            </MetaItem>
          </div>
        </div>
      </header>

      {s.narrative ? (
        <Section
          n={0}
          title="Executive summary"
          subtitle={
            s.narrative.generated_by === "template"
              ? "Template narrative built from the verified numbers (no language model key configured)."
              : `Narrative written by ${s.narrative.generated_by}; every figure comes from the deterministic engine.`
          }
          className="animate-in-up delay-1"
        >
          <div className="flex flex-col gap-4">
            <p className="text-[15px] leading-relaxed">{s.narrative.executive_summary}</p>
            <div className="rounded-md border border-primary/25 bg-primary-soft/40 p-4">
              <div className="eyebrow mb-1.5">Plain-language explanation for the borrower</div>
              <p className="text-sm leading-relaxed">{s.narrative.borrower_explanation}</p>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <div className="eyebrow mb-1.5">Key drivers</div>
                <ul className="list-disc space-y-1 pl-5 text-sm">
                  {s.narrative.key_drivers.map((d, i) => (
                    <li key={i}>{d}</li>
                  ))}
                </ul>
              </div>
              <div>
                <div className="eyebrow mb-1.5">Next steps</div>
                <ol className="list-decimal space-y-1 pl-5 text-sm">
                  {s.narrative.next_steps.map((d, i) => (
                    <li key={i}>{d}</li>
                  ))}
                </ol>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
              <Badge variant={s.narrative.generated_by === "template" ? "muted" : "brand"} className="font-mono text-[10px]">
                {s.narrative.generated_by}
              </Badge>
              {s.narrative.llm_error ? <span>model unavailable, template used ({s.narrative.llm_error})</span> : null}
            </div>
          </div>
        </Section>
      ) : null}

      {s.decision_explanation || s.risk_signal?.shap ? (
        <Section
          n={0}
          title="Why this decision"
          subtitle="Policy margins (the cause) and SHAP contributions to the risk score (the context), in numbers and in words."
          className="animate-in-up delay-1"
        >
          <ShapExplanationView bare explanation={s.decision_explanation} shap={s.risk_signal?.shap} />
        </Section>
      ) : null}

      {s.decision?.decision === "declined" ? (
        <ApprovalPathCard path={s.approval_path ?? null} className="animate-in-up delay-1 print:border print:shadow-none" compact />
      ) : null}

      <Section n={1} title="Borrower summary" subtitle="Declared profile and requested facility." className="animate-in-up delay-1">
        <KeyValueGrid data={s.borrower_summary} />
      </Section>

      <Section
        n={2}
        title="Extracted facts"
        subtitle="Evidence from documents, with confidence and citation. Facts, not judgements."
        className="animate-in-up delay-2"
      >
        {s.extracted_facts?.length ? (
          <div className="overflow-hidden rounded-md border">
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead>Field</TableHead>
                  <TableHead>Value</TableHead>
                  <TableHead>Confidence</TableHead>
                  <TableHead>Source</TableHead>
                  <TableHead>Review</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {s.extracted_facts.map((f, i) => (
                  <TableRow key={`${f.field}-${i}`}>
                    <TableCell>
                      <div className="text-sm font-medium">{humanize(f.field)}</div>
                      <div className="font-mono text-[11px] text-muted-foreground">{f.field}</div>
                    </TableCell>
                    <TableCell className="font-medium tnum">{displayValue(f.value)}</TableCell>
                    <TableCell>
                      <ConfidenceBar value={f.confidence} />
                    </TableCell>
                    <TableCell className="max-w-[220px] text-xs text-muted-foreground">
                      <span className="line-clamp-1" title={f.source_document ?? undefined}>
                        {f.source_document ?? "—"}
                      </span>
                      {f.page !== null ? <span className="tnum">p.{f.page}</span> : null}
                    </TableCell>
                    <TableCell>
                      <ReviewStatusBadge status={f.review_status} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No extracted facts.</p>
        )}
      </Section>

      <Section n={3} title="Calculated values" subtitle="Deterministic formulas applied to the verified facts." className="animate-in-up delay-3">
        {s.calculated_values ? <FinancialsTable financials={s.calculated_values} /> : <p className="text-sm text-muted-foreground">Not computed.</p>}
      </Section>

      <div className="grid gap-5 lg:grid-cols-2">
        <Section n={4} title="Risk signal" subtitle="Model output; a signal, not the decision." className="animate-in-up delay-4">
          <RiskCard risk={s.risk_signal} />
        </Section>
        <Section n={5} title="Policy rules" subtitle="Thresholds and rules that governed the decision." className="animate-in-up delay-4">
          <KeyValueGrid data={s.policy_rules} />
        </Section>
      </div>

      <Section n={6} title="AI reasoning" subtitle="Narrative assessment, kept separate from facts and calculations.">
        <RiskReasoningView reasoning={s.ai_reasoning} />
      </Section>

      <Section n={7} title="Human overrides" subtitle="Reviewer actions recorded on this run.">
        <HumanOverrides reviews={s.human_overrides ?? []} />
      </Section>

      <Section n={8} title="Decision" subtitle="Final outcome with reason codes.">
        <div className="flex flex-col gap-4">
          <div className="flex flex-wrap items-center gap-3 rounded-md bg-muted/40 px-4 py-3">
            <DecisionBadge decision={s.decision?.decision} className="px-3 py-1 text-sm" />
            <span className="text-sm text-muted-foreground">
              confidence <span className="font-semibold text-foreground tnum">{formatPercent(confidence)}</span>
            </span>
          </div>
          <ReasonsList reasons={s.decision?.reasons ?? []} />
          {s.reason_codes?.length ? (
            <div className="flex flex-col gap-1.5">
              <span className="eyebrow">Reason codes</span>
              <div className="flex flex-wrap gap-1.5">
                {s.reason_codes.map((c) => (
                  <Badge key={c} variant="outline" className="font-mono">
                    {c}
                  </Badge>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      </Section>

      <footer className="hidden border-t pt-3 text-[11px] text-muted-foreground print:block">
        {memo.title} · application {memo.application_id} · run {memo.run_id} · generated {formatDateTime(memo.generated_at)} by{" "}
        {memo.generated_by}
      </footer>
    </article>
  );
}
