"use client";

import { useEffect, useState, type FormEvent } from "react";
import { FlaskConical, RotateCcw, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import type { Financials, WhatIfOverrides, WhatIfRequest } from "@/lib/types";
import { cn, humanize } from "@/lib/utils";
import { POLICY_PROFILES, whatIfSchema, zodErrors } from "@/lib/validations";

export type WhatIfFormValues = Record<keyof WhatIfOverrides, string>;

const FIELDS: { key: keyof WhatIfOverrides; label: string; step?: string; aliases: string[] }[] = [
  { key: "loan_amount", label: "Loan amount (INR)", step: "1000", aliases: ["loan_amount", "amount", "principal"] },
  { key: "tenure_months", label: "Tenure (months)", step: "1", aliases: ["tenure_months", "tenure"] },
  { key: "annual_rate", label: "Annual rate", step: "0.1", aliases: ["annual_rate", "rate_annual", "rate"] },
  { key: "vehicle_price", label: "Vehicle / asset price (INR)", step: "1000", aliases: ["vehicle_price", "asset_price"] },
  { key: "existing_monthly_obligations", label: "Existing monthly obligations (INR)", step: "500", aliases: ["existing_monthly_obligations", "existing_obligations", "total_monthly_obligations"] },
  { key: "monthly_income", label: "Monthly income (INR)", step: "500", aliases: ["monthly_income", "verified_income", "income"] },
  { key: "down_payment", label: "Down payment (INR)", step: "1000", aliases: ["down_payment"] },
];

function pick(inputs: Record<string, unknown>, aliases: string[]): string {
  for (const a of aliases) {
    const v = inputs[a];
    if (typeof v === "number" && Number.isFinite(v)) return String(v);
    if (typeof v === "string" && v !== "" && !Number.isNaN(Number(v))) return v;
  }
  return "";
}

/** Prefill values from a base run's financials (calculation_inputs first, then top-level aliases). */
export function baseValues(financials: Financials | null | undefined): WhatIfFormValues {
  const inputs: Record<string, unknown> = { ...(financials?.calculation_inputs ?? {}) };
  if (financials) {
    inputs.existing_obligations ??= financials.existing_obligations ?? financials.total_monthly_obligations;
    inputs.verified_income ??= financials.verified_income ?? financials.monthly_income;
    inputs.down_payment ??= financials.down_payment;
  }
  const out = {} as WhatIfFormValues;
  for (const f of FIELDS) out[f.key] = pick(inputs, f.aliases);
  return out;
}

export interface WhatIfFormProps {
  initial: WhatIfFormValues;
  basePolicy: string;
  /** Externally applied values (e.g. "Apply suggestion"). */
  applied?: Partial<WhatIfFormValues> | null;
  submitting: boolean;
  onSubmit: (payload: WhatIfRequest) => void;
}

export function WhatIfForm({ initial, basePolicy, applied, submitting, onSubmit }: WhatIfFormProps) {
  const [values, setValues] = useState<WhatIfFormValues>(initial);
  const [policy, setPolicy] = useState<string>(basePolicy);
  const [findMin, setFindMin] = useState(true);
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (applied) setValues((v) => ({ ...v, ...applied }));
  }, [applied]);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const parsed = whatIfSchema.safeParse(values);
    if (!parsed.success) {
      setErrors(zodErrors(parsed.error));
      return;
    }
    setErrors({});
    const overrides: WhatIfOverrides = {};
    for (const f of FIELDS) {
      const v = parsed.data[f.key];
      // Only send values that differ from the base run so the scenario is a true diff.
      if (v !== undefined && String(v) !== (initial[f.key] || "")) overrides[f.key] = v;
    }
    onSubmit({ overrides, policy_profile: policy || undefined, find_min_change: findMin });
  };

  const changedCount = FIELDS.filter((f) => (values[f.key] || "") !== (initial[f.key] || "")).length;
  const policyChanged = policy !== basePolicy;

  return (
    <form onSubmit={submit} className="flex flex-col gap-5" noValidate>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
        {FIELDS.map((f) => {
          const changed = (values[f.key] || "") !== (initial[f.key] || "");
          const error = errors[f.key];
          return (
            <div key={f.key} className="flex flex-col gap-1.5">
              <div className="flex items-baseline justify-between gap-2">
                <Label htmlFor={`wi-${f.key}`}>{f.label}</Label>
                {changed ? (
                  <span className="rounded-full bg-primary-soft px-1.5 py-px text-[10px] font-semibold uppercase tracking-wide text-primary">
                    changed
                  </span>
                ) : null}
              </div>
              <Input
                id={`wi-${f.key}`}
                type="number"
                step={f.step}
                min={0}
                value={values[f.key]}
                onChange={(e) => setValues((v) => ({ ...v, [f.key]: e.target.value }))}
                placeholder="unchanged"
                aria-invalid={error ? true : undefined}
                className={cn("tnum", changed && "border-primary/60 bg-primary-soft/30", error && "border-danger focus-visible:ring-danger/25")}
              />
              {error ? (
                <p className="text-xs text-danger" role="alert">
                  {error}
                </p>
              ) : (
                <p className="flex items-center gap-1 text-[11px] text-muted-foreground">
                  <span className="uppercase tracking-wide">base</span>
                  {initial[f.key] ? (
                    <button
                      type="button"
                      className="rounded px-1 font-mono text-[11px] text-foreground/80 tnum transition-colors hover:bg-accent hover:text-foreground"
                      onClick={() => setValues((v) => ({ ...v, [f.key]: initial[f.key] }))}
                      title="Reset this field to its base value"
                    >
                      {initial[f.key]}
                    </button>
                  ) : (
                    <span className="italic">unknown</span>
                  )}
                </p>
              )}
            </div>
          );
        })}

        <div className="flex flex-col gap-1.5">
          <div className="flex items-baseline justify-between gap-2">
            <Label htmlFor="wi-policy">Policy profile</Label>
            {policyChanged ? (
              <span className="rounded-full bg-primary-soft px-1.5 py-px text-[10px] font-semibold uppercase tracking-wide text-primary">
                changed
              </span>
            ) : null}
          </div>
          <Select
            id="wi-policy"
            value={policy}
            onChange={(e) => setPolicy(e.target.value)}
            className={cn(policyChanged && "border-primary/60 bg-primary-soft/30")}
          >
            {POLICY_PROFILES.map((p) => (
              <option key={p} value={p}>
                {humanize(p)}
              </option>
            ))}
            {!POLICY_PROFILES.includes(basePolicy as (typeof POLICY_PROFILES)[number]) && basePolicy ? (
              <option value={basePolicy}>{humanize(basePolicy)}</option>
            ) : null}
          </Select>
          <p className="flex items-center gap-1 text-[11px] text-muted-foreground">
            <span className="uppercase tracking-wide">base</span>
            <span className="font-mono text-[11px] text-foreground/80">{humanize(basePolicy)}</span>
          </p>
        </div>
      </div>

      <label
        htmlFor="wi-find-min"
        className={cn(
          "flex cursor-pointer items-center gap-3 rounded-lg border p-3.5 transition-colors",
          findMin ? "border-primary/40 bg-primary-soft/40" : "bg-muted/30 hover:bg-muted/50"
        )}
      >
        <span className={cn("flex h-9 w-9 shrink-0 items-center justify-center rounded-md", findMin ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground")}>
          <Sparkles className="h-4 w-4" />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block text-sm font-medium">Find minimum change for approval</span>
          <span className="block text-xs text-muted-foreground">Search for the smallest input change that flips the decision to approved.</span>
        </span>
        <input
          id="wi-find-min"
          type="checkbox"
          role="switch"
          aria-checked={findMin}
          className="peer sr-only"
          checked={findMin}
          onChange={(e) => setFindMin(e.target.checked)}
        />
        <span
          aria-hidden="true"
          className={cn(
            "relative h-6 w-11 shrink-0 rounded-full transition-colors peer-focus-visible:ring-2 peer-focus-visible:ring-primary/40 peer-focus-visible:ring-offset-2",
            findMin ? "bg-primary" : "bg-muted-foreground/30"
          )}
        >
          <span
            className={cn(
              "absolute top-0.5 h-5 w-5 rounded-full bg-white shadow-sm transition-transform",
              findMin ? "translate-x-[22px]" : "translate-x-0.5"
            )}
          />
        </span>
      </label>

      <div className="flex flex-wrap items-center justify-between gap-3 border-t pt-4">
        <span className="text-xs text-muted-foreground tnum">
          {changedCount + (policyChanged ? 1 : 0) === 0
            ? "No overrides yet — scenario equals base."
            : `${changedCount + (policyChanged ? 1 : 0)} override${changedCount + (policyChanged ? 1 : 0) === 1 ? "" : "s"} will be sent.`}
        </span>
        <div className="flex flex-wrap items-center gap-2">
          <Button type="button" variant="outline" onClick={() => setValues(initial)}>
            <RotateCcw /> Reset
          </Button>
          <Button type="submit" variant="brand" disabled={submitting}>
            <FlaskConical className={submitting ? "animate-pulse" : undefined} /> {submitting ? "Simulating…" : "Run scenario"}
          </Button>
        </div>
      </div>
    </form>
  );
}
