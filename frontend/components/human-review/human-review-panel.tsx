"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, Check, CircleHelp, FileSearch, Pencil, Send, ShieldAlert, UserCheck, X } from "lucide-react";

import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { api, errorMessage } from "@/lib/api";
import { getUser } from "@/lib/session";
import type { FieldReviewInput, LowConfidenceField, ResumePayload, RunState } from "@/lib/types";
import { cn, confidenceTone, displayValue, formatPercent, humanize } from "@/lib/utils";

type FieldAction = "accept" | "correct" | "reject";

interface FieldDraft {
  action: FieldAction | "";
  corrected: string;
  note: string;
}

const ACTIONS: { value: FieldAction; label: string; icon: React.ReactNode; tone: string }[] = [
  {
    value: "accept",
    label: "Accept",
    icon: <Check className="h-3.5 w-3.5" />,
    tone: "peer-checked:bg-success-soft peer-checked:text-success peer-checked:ring-success/40",
  },
  {
    value: "correct",
    label: "Correct",
    icon: <Pencil className="h-3.5 w-3.5" />,
    tone: "peer-checked:bg-info-soft peer-checked:text-info peer-checked:ring-info/40",
  },
  {
    value: "reject",
    label: "Reject",
    icon: <X className="h-3.5 w-3.5" />,
    tone: "peer-checked:bg-danger-soft peer-checked:text-danger peer-checked:ring-danger/40",
  },
];

/** Interprets a corrected value: numbers become numbers, everything else stays a string. */
function parseCorrected(raw: string): unknown {
  const trimmed = raw.trim();
  if (trimmed === "") return trimmed;
  if (/^-?\d+(\.\d+)?$/.test(trimmed)) return Number(trimmed);
  if (trimmed === "true") return true;
  if (trimmed === "false") return false;
  return trimmed;
}

export interface HumanReviewPanelProps {
  state: RunState;
  onResumed: (next: RunState) => void;
}

export function HumanReviewPanel({ state, onResumed }: HumanReviewPanelProps) {
  const fields = state.low_confidence;
  // The flagged item is the weakest one for a field, so cite that item — not the last one seen.
  const evidenceByField = useMemo(() => {
    const m = new Map<string, RunState["evidence"][number]>();
    for (const e of state.evidence) {
      const cur = m.get(e.field);
      if (!cur || e.confidence < cur.confidence) m.set(e.field, e);
    }
    return m;
  }, [state.evidence]);

  const [drafts, setDrafts] = useState<Record<string, FieldDraft>>({});
  const [reviewer, setReviewer] = useState("");
  const [override, setOverride] = useState<"" | "approved" | "declined" | "referred">("");
  const [overrideNote, setOverrideNote] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const u = getUser();
    if (u && !reviewer) setReviewer(u.name || u.email);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const draft = (field: string): FieldDraft => drafts[field] ?? { action: "", corrected: "", note: "" };
  const setDraft = (field: string, patch: Partial<FieldDraft>) =>
    setDrafts((d) => ({ ...d, [field]: { ...draft(field), ...patch } }));

  const submit = async () => {
    const nextErrors: Record<string, string> = {};
    if (!reviewer.trim()) nextErrors._reviewer = "Reviewer name is required";
    const reviews: FieldReviewInput[] = [];
    for (const f of fields) {
      const d = draft(f.field);
      if (!d.action) {
        nextErrors[f.field] = "Choose Accept, Correct or Reject";
        continue;
      }
      if (d.action === "correct" && d.corrected.trim() === "") {
        nextErrors[f.field] = "Enter the corrected value";
        continue;
      }
      const review: FieldReviewInput = { field: f.field, action: d.action };
      if (d.action === "correct") review.corrected_value = parseCorrected(d.corrected);
      if (d.note.trim()) review.note = d.note.trim();
      reviews.push(review);
    }
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;

    const payload: ResumePayload = { reviewer: reviewer.trim(), reviews };
    if (override) payload.decision_override = { decision: override, note: overrideNote.trim() || undefined };

    setSubmitting(true);
    setSubmitError(null);
    try {
      const next = await api.resumeRun(state.run_id, payload);
      onResumed(next);
    } catch (err) {
      setSubmitError(errorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  const reviewed = fields.filter((f) => draft(f.field).action !== "").length;

  return (
    <Card className="overflow-hidden border-warning/50 shadow-pop">
      {/* Warning header band */}
      <div className="border-b border-warning/30 bg-warning-soft px-5 py-4 sm:px-6">
        <div className="flex flex-wrap items-start gap-4">
          <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-warning text-white shadow-sm" aria-hidden="true">
            <AlertTriangle className="h-5 w-5" />
          </span>
          <div className="min-w-0 flex-1">
            <div className="eyebrow text-warning">Action required</div>
            <h2 className="text-lg font-bold uppercase tracking-[0.08em] sm:text-xl">Human review required</h2>
            <p className="mt-1 text-[13px] text-foreground/80">
              The workflow paused because {fields.length} extracted field{fields.length === 1 ? "" : "s"} did not meet the confidence
              threshold. Every field must be reviewed before the run continues.
            </p>
          </div>
          <div className="flex items-center gap-2 rounded-full border border-warning/40 bg-card px-3 py-1 text-xs font-medium">
            <span className="tnum">
              {reviewed}/{fields.length}
            </span>
            <span className="text-muted-foreground">reviewed</span>
          </div>
        </div>
      </div>

      <CardContent className="flex flex-col gap-6 p-5 sm:p-6">
        {state.pending_fields && state.pending_fields.length > 0 ? (
          <Alert variant="warning" title="Still awaiting review">
            Pending fields:{" "}
            {state.pending_fields.map((p) => (
              <code key={p} className="mr-1 rounded bg-card px-1.5 py-0.5 font-mono text-xs">
                {p}
              </code>
            ))}
          </Alert>
        ) : null}

        {state.review_questions.length > 0 ? (
          <section className="rounded-lg border bg-muted/40 p-4">
            <div className="mb-2.5 flex items-center gap-2">
              <CircleHelp className="h-4 w-4 text-primary" />
              <h3 className="text-sm font-semibold">Questions for the reviewer</h3>
            </div>
            <ul className="flex flex-col gap-2 text-sm">
              {state.review_questions.map((q, i) => (
                <li key={i} className="flex items-start gap-2.5">
                  <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded border border-primary/40 bg-card text-[10px] font-semibold text-primary tnum">
                    {i + 1}
                  </span>
                  <span className="text-foreground/90">{q}</span>
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        <section className="flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <div className="eyebrow">Low-confidence fields</div>
            <span className="text-xs text-muted-foreground">Accept, correct or reject each one</span>
          </div>
          {fields.map((f, i) => (
            <FieldReviewCard
              key={f.field}
              index={i}
              field={f}
              currentValue={f.value !== undefined ? f.value : evidenceByField.get(f.field)?.value}
              page={f.page ?? evidenceByField.get(f.field)?.page ?? null}
              draft={draft(f.field)}
              error={errors[f.field]}
              onChange={(patch) => setDraft(f.field, patch)}
            />
          ))}
        </section>

        <section className="rounded-lg border bg-card p-4 sm:p-5">
          <div className="mb-4 flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-md bg-primary-soft text-primary">
              <UserCheck className="h-4 w-4" />
            </span>
            <div>
              <h3 className="text-sm font-semibold">Reviewer &amp; override</h3>
              <p className="text-xs text-muted-foreground">Your name is logged against every action in the audit trail.</p>
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Reviewer name" htmlFor="reviewer" error={errors._reviewer}>
              <Input id="reviewer" value={reviewer} onChange={(e) => setReviewer(e.target.value)} placeholder="Jane Analyst" />
            </Field>
            <Field label="Decision override (optional)" htmlFor="override" hint="Leave empty to let the policy decide.">
              <Select id="override" value={override} onChange={(e) => setOverride(e.target.value as typeof override)}>
                <option value="">No override</option>
                <option value="approved">Approve</option>
                <option value="declined">Decline</option>
                <option value="referred">Refer</option>
              </Select>
            </Field>
            {override ? (
              <Field label="Override note" htmlFor="override_note" className="sm:col-span-2">
                <Textarea
                  id="override_note"
                  value={overrideNote}
                  onChange={(e) => setOverrideNote(e.target.value)}
                  placeholder="Why is the policy outcome being overridden?"
                />
              </Field>
            ) : null}
          </div>
          {override ? (
            <div className="mt-3 flex items-start gap-2 rounded-md border border-warning/40 bg-warning-soft px-3 py-2 text-xs text-foreground/85">
              <ShieldAlert className="mt-0.5 h-3.5 w-3.5 shrink-0 text-warning" />
              An override replaces the policy outcome and is recorded as a human override on the decision.
            </div>
          ) : null}
        </section>

        {submitError ? (
          <Alert variant="destructive" title="Could not submit review">
            {submitError}
          </Alert>
        ) : null}

        <div className="flex flex-col-reverse items-stretch gap-3 border-t pt-5 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-xs text-muted-foreground">
            Submitting resumes the run from the paused node with your reviews applied.
          </p>
          <Button variant="brand" size="lg" onClick={submit} disabled={submitting || fields.length === 0} className="sm:min-w-[260px]">
            <Send /> {submitting ? "Submitting…" : "Submit review and resume"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function FieldReviewCard({
  index,
  field,
  currentValue,
  page,
  draft,
  error,
  onChange,
}: {
  index: number;
  field: LowConfidenceField;
  currentValue: unknown;
  page: number | null;
  draft: FieldDraft;
  error?: string;
  onChange: (patch: Partial<FieldDraft>) => void;
}) {
  const tone = confidenceTone(field.confidence);
  const name = `review-${field.field}`;
  const decided = draft.action !== "";
  const thresholdPct = Math.max(0, Math.min(1, field.threshold)) * 100;
  return (
    <div
      className={cn(
        "surface p-4 transition-colors sm:p-5",
        error ? "border-danger/60 ring-1 ring-danger/30" : decided ? "border-success/40" : "border-warning/40"
      )}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-3">
          <span
            className={cn(
              "flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-xs font-semibold tnum",
              decided ? "bg-success-soft text-success" : "bg-warning-soft text-warning"
            )}
          >
            {decided ? <Check className="h-4 w-4" /> : index + 1}
          </span>
          <div className="min-w-0">
            <div className="text-sm font-semibold">{humanize(field.field)}</div>
            <div className="font-mono text-xs text-muted-foreground">{field.field}</div>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          {field.requires_human_review ? <Badge variant="warning" dot>requires review</Badge> : null}
          <Badge variant="outline">threshold {formatPercent(field.threshold, 0)}</Badge>
        </div>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <div className="rounded-md bg-muted/50 px-3 py-2.5">
          <div className="eyebrow">Current value</div>
          <div className="mt-1 break-words text-base font-semibold tnum">{displayValue(currentValue)}</div>
        </div>
        <div className="rounded-md bg-muted/50 px-3 py-2.5">
          <div className="flex items-center justify-between">
            <div className="eyebrow">Confidence</div>
            <span
              className={cn(
                "text-base font-semibold tnum",
                tone === "good" ? "text-success" : tone === "warn" ? "text-warning" : "text-danger"
              )}
            >
              {formatPercent(field.confidence, 0)}
            </span>
          </div>
          <div className="relative mt-2">
            <Progress value={field.confidence} tone={tone} label={`Confidence ${formatPercent(field.confidence)}`} />
            <span
              aria-hidden="true"
              className="absolute -top-1 h-4 w-0.5 rounded-full bg-foreground/70"
              style={{ left: `calc(${thresholdPct}% - 1px)` }}
              title={`Threshold ${formatPercent(field.threshold, 0)}`}
            />
          </div>
          <div className="mt-1.5 text-[11px] text-muted-foreground">
            {field.threshold > field.confidence ? (
              <>
                <span className="tnum">{formatPercent(field.threshold - field.confidence, 0)}</span> below the{" "}
                <span className="tnum">{formatPercent(field.threshold, 0)}</span> threshold
              </>
            ) : (
              <>
                Meets the <span className="tnum">{formatPercent(field.threshold, 0)}</span> threshold
              </>
            )}
          </div>
        </div>
      </div>

      {field.source_document || field.evidence ? (
        <figure className="mt-3 rounded-md border-l-[3px] border-primary bg-primary-soft/50 px-4 py-3">
          <figcaption className="flex items-center gap-1.5 text-[11px] font-medium text-muted-foreground">
            <FileSearch className="h-3.5 w-3.5 text-primary" />
            Source: <span className="font-mono text-foreground/80">{field.source_document ?? "unknown"}</span>
            {page !== null ? <span className="tnum">· page {page}</span> : null}
          </figcaption>
          {field.evidence ? <blockquote className="mt-1.5 text-sm italic leading-relaxed text-foreground/90">&ldquo;{field.evidence}&rdquo;</blockquote> : null}
        </figure>
      ) : null}

      <fieldset className="mt-4">
        <legend className="eyebrow mb-2">Reviewer action</legend>
        <div className="inline-flex w-full max-w-md rounded-md border bg-muted/60 p-1" role="radiogroup">
          {ACTIONS.map((a) => (
            <div key={a.value} className="flex-1">
              <input
                type="radio"
                id={`${name}-${a.value}`}
                name={name}
                value={a.value}
                className="peer sr-only"
                checked={draft.action === a.value}
                onChange={() => onChange({ action: a.value })}
              />
              <label
                htmlFor={`${name}-${a.value}`}
                className={cn(
                  "flex cursor-pointer select-none items-center justify-center gap-1.5 rounded-[7px] px-3 py-1.5 text-sm font-medium text-muted-foreground ring-1 ring-transparent transition-all hover:text-foreground peer-checked:shadow-sm peer-focus-visible:ring-2 peer-focus-visible:ring-ring",
                  a.tone
                )}
              >
                {a.icon} {a.label}
              </label>
            </div>
          ))}
        </div>
      </fieldset>

      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        {draft.action === "correct" ? (
          <Field label="Corrected value" htmlFor={`${name}-corrected`}>
            <Input
              id={`${name}-corrected`}
              value={draft.corrected}
              onChange={(e) => onChange({ corrected: e.target.value })}
              placeholder={displayValue(currentValue)}
              className="font-mono"
            />
          </Field>
        ) : null}
        <Field label="Note (optional)" htmlFor={`${name}-note`} className={draft.action === "correct" ? undefined : "sm:col-span-2"}>
          <Input id={`${name}-note`} value={draft.note} onChange={(e) => onChange({ note: e.target.value })} placeholder="Reasoning for the reviewer log" />
        </Field>
      </div>
      {error ? (
        <p className="mt-2 flex items-center gap-1.5 text-xs font-medium text-danger" role="alert">
          <AlertTriangle className="h-3.5 w-3.5" /> {error}
        </p>
      ) : null}
    </div>
  );
}
