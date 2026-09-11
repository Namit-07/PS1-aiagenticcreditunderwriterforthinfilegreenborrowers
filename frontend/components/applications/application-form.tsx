"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Calculator, Leaf, Save, UserRound } from "lucide-react";

import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { SectionHeading } from "@/components/ui/section-heading";
import { Select } from "@/components/ui/select";
import { api, errorMessage } from "@/lib/api";
import type { CreateApplicationPayload } from "@/lib/types";
import { formatCurrency, humanize } from "@/lib/utils";
import {
  applicationSchema,
  EMPLOYMENT_TYPES,
  LOCATION_TIERS,
  PRODUCT_TYPES,
  zodErrors,
} from "@/lib/validations";

type FormValues = {
  product_type: string;
  amount: string;
  tenure_months: string;
  rate_annual: string;
  ref_id: string;
  full_name: string;
  age: string;
  location_tier: string;
  declared_monthly_income: string;
  employment_type: string;
  vehicle_price: string;
  down_payment: string;
};

const INITIAL: FormValues = {
  product_type: "ev_two_wheeler",
  amount: "",
  tenure_months: "36",
  rate_annual: "12",
  ref_id: "",
  full_name: "",
  age: "",
  location_tier: "tier_2",
  declared_monthly_income: "",
  employment_type: "gig_platform",
  vehicle_price: "",
  down_payment: "",
};

function num(v: string): number | null {
  if (v.trim() === "") return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

/**
 * Display-only EMI estimate: P*r*(1+r)^n / ((1+r)^n - 1), r = annual rate / 1200.
 * The underwriting run computes the verified EMI; this is just a live preview.
 */
function estimateEmi(principal: number | null, tenureMonths: number | null, rateAnnual: number | null): number | null {
  if (principal === null || tenureMonths === null || rateAnnual === null) return null;
  if (principal <= 0 || tenureMonths <= 0 || rateAnnual < 0) return null;
  const n = Math.round(tenureMonths);
  const r = rateAnnual / 1200;
  if (r === 0) return principal / n;
  const f = Math.pow(1 + r, n);
  const emi = (principal * r * f) / (f - 1);
  return Number.isFinite(emi) ? emi : null;
}

export function ApplicationForm() {
  const router = useRouter();
  const [values, setValues] = useState<FormValues>(INITIAL);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [apiError, setApiError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const set = (key: keyof FormValues) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setValues((v) => ({ ...v, [key]: e.target.value }));

  const amount = num(values.amount);
  const tenure = num(values.tenure_months);
  const rate = num(values.rate_annual);
  const emi = estimateEmi(amount, tenure, rate);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setApiError(null);
    const parsed = applicationSchema.safeParse(values);
    if (!parsed.success) {
      setErrors(zodErrors(parsed.error));
      return;
    }
    setErrors({});
    const d = parsed.data;
    const payload: CreateApplicationPayload = {
      product: {
        type: d.product_type,
        amount: d.amount,
        tenure_months: d.tenure_months,
        rate_annual: d.rate_annual,
      },
      borrower: {
        ref_id: d.ref_id,
        age: d.age,
        location_tier: d.location_tier,
        full_name: d.full_name?.trim() ? d.full_name.trim() : null,
        declared_monthly_income: d.declared_monthly_income ?? null,
        employment_type: d.employment_type ? d.employment_type : null,
      },
      loan_request: {
        amount: d.amount,
        tenure_months: d.tenure_months,
        vehicle_price: d.vehicle_price ?? null,
        down_payment: d.down_payment ?? null,
      },
    };
    setSubmitting(true);
    try {
      const created = await api.createApplication(payload);
      router.push(`/applications/${created.id}/documents`);
    } catch (err) {
      setApiError(errorMessage(err));
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={onSubmit} className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_320px]" noValidate>
      {/* Left: form sections */}
      <div className="flex min-w-0 flex-col gap-6">
        <Card className="animate-in-up">
          <CardHeader className="border-b">
            <SectionHeading
              icon={<Leaf />}
              title="Product"
              description="Green asset being financed and the requested terms."
            />
          </CardHeader>
          <CardContent className="grid gap-4 pt-5 sm:grid-cols-2 xl:grid-cols-3">
            <Field label="Product type" htmlFor="product_type" error={errors.product_type}>
              <Select id="product_type" value={values.product_type} onChange={set("product_type")}>
                {PRODUCT_TYPES.map((p) => (
                  <option key={p} value={p}>
                    {humanize(p)}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Loan amount (INR)" htmlFor="amount" error={errors.amount}>
              <Input id="amount" type="number" min={0} step="1000" inputMode="numeric" value={values.amount} onChange={set("amount")} placeholder="120000" className="tnum" />
            </Field>
            <Field label="Tenure (months)" htmlFor="tenure_months" error={errors.tenure_months}>
              <Input id="tenure_months" type="number" min={1} step="1" value={values.tenure_months} onChange={set("tenure_months")} className="tnum" />
            </Field>
            <Field label="Annual rate (%)" htmlFor="rate_annual" error={errors.rate_annual} hint="e.g. 12 for 12% p.a.">
              <Input id="rate_annual" type="number" min={0} step="0.1" value={values.rate_annual} onChange={set("rate_annual")} className="tnum" />
            </Field>
            <Field label="Vehicle / asset price (INR)" htmlFor="vehicle_price" error={errors.vehicle_price} hint="Optional; used for LTV.">
              <Input id="vehicle_price" type="number" min={0} step="1000" value={values.vehicle_price} onChange={set("vehicle_price")} placeholder="150000" className="tnum" />
            </Field>
            <Field label="Down payment (INR)" htmlFor="down_payment" error={errors.down_payment} hint="Optional.">
              <Input id="down_payment" type="number" min={0} step="1000" value={values.down_payment} onChange={set("down_payment")} placeholder="30000" className="tnum" />
            </Field>
          </CardContent>
        </Card>

        <Card className="animate-in-up delay-1">
          <CardHeader className="border-b">
            <SectionHeading
              icon={<UserRound />}
              title="Borrower"
              description="Applicant details as declared. Documents will be used to verify them."
            />
          </CardHeader>
          <CardContent className="grid gap-4 pt-5 sm:grid-cols-2 xl:grid-cols-3">
            <Field label="Borrower reference ID" htmlFor="ref_id" error={errors.ref_id}>
              <Input id="ref_id" value={values.ref_id} onChange={set("ref_id")} placeholder="BRW-0001" className="font-mono" />
            </Field>
            <Field label="Full name" htmlFor="full_name" error={errors.full_name} hint="Optional.">
              <Input id="full_name" value={values.full_name} onChange={set("full_name")} placeholder="Asha Kumar" />
            </Field>
            <Field label="Age" htmlFor="age" error={errors.age}>
              <Input id="age" type="number" min={16} max={100} value={values.age} onChange={set("age")} placeholder="27" className="tnum" />
            </Field>
            <Field label="Location tier" htmlFor="location_tier" error={errors.location_tier}>
              <Select id="location_tier" value={values.location_tier} onChange={set("location_tier")}>
                {LOCATION_TIERS.map((t) => (
                  <option key={t} value={t}>
                    {humanize(t)}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Declared monthly income (INR)" htmlFor="declared_monthly_income" error={errors.declared_monthly_income} hint="Optional.">
              <Input id="declared_monthly_income" type="number" min={0} step="500" value={values.declared_monthly_income} onChange={set("declared_monthly_income")} placeholder="25000" className="tnum" />
            </Field>
            <Field label="Employment type" htmlFor="employment_type" error={errors.employment_type}>
              <Select id="employment_type" value={values.employment_type} onChange={set("employment_type")}>
                <option value="">Not specified</option>
                {EMPLOYMENT_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {humanize(t)}
                  </option>
                ))}
              </Select>
            </Field>
          </CardContent>
        </Card>
      </div>

      {/* Right: sticky live summary */}
      <aside className="lg:sticky lg:top-20">
        <Card className="overflow-hidden animate-in-up delay-2">
          <span className="block h-[3px] bg-brand-gradient" aria-hidden="true" />
          <CardHeader className="pb-3">
            <SectionHeading
              icon={<Calculator />}
              title="Request summary"
              description="Live preview of the terms you are capturing."
            />
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <div className="rounded-md border bg-muted/50 p-4">
              <div className="flex items-center justify-between gap-2">
                <span className="eyebrow">Estimated EMI</span>
                <Badge variant="muted" className="text-[10px] uppercase tracking-wide">
                  Estimate
                </Badge>
              </div>
              <div className="mt-1.5 text-[28px] font-bold leading-none tracking-tight tnum">
                {emi !== null ? formatCurrency(emi) : "—"}
              </div>
              <p className="mt-2 text-[11px] leading-snug text-muted-foreground">
                {emi !== null ? "Per month, indicative only." : "Enter amount, tenure and rate to preview."} The
                underwriting run computes the verified EMI.
              </p>
            </div>

            <dl className="divide-y rounded-md border">
              <div className="flex items-center justify-between gap-3 px-3 py-2.5">
                <dt className="text-xs text-muted-foreground">Product</dt>
                <dd className="truncate text-sm font-medium">{humanize(values.product_type)}</dd>
              </div>
              <div className="flex items-center justify-between gap-3 px-3 py-2.5">
                <dt className="text-xs text-muted-foreground">Loan amount</dt>
                <dd className="text-sm font-semibold tnum">{amount !== null ? formatCurrency(amount) : "—"}</dd>
              </div>
              <div className="flex items-center justify-between gap-3 px-3 py-2.5">
                <dt className="text-xs text-muted-foreground">Tenure</dt>
                <dd className="text-sm font-semibold tnum">{tenure !== null ? `${tenure} mo` : "—"}</dd>
              </div>
              <div className="flex items-center justify-between gap-3 px-3 py-2.5">
                <dt className="text-xs text-muted-foreground">Annual rate</dt>
                <dd className="text-sm font-semibold tnum">{rate !== null ? `${rate}% p.a.` : "—"}</dd>
              </div>
            </dl>

            {apiError ? (
              <Alert variant="destructive" title="Could not create application">
                {apiError}
              </Alert>
            ) : null}
          </CardContent>
          <CardFooter className="flex-col items-stretch gap-2">
            <Button type="submit" disabled={submitting} className="w-full">
              <Save /> {submitting ? "Creating…" : "Create and upload documents"}
            </Button>
            <Button type="button" variant="ghost" className="w-full" onClick={() => router.push("/applications")}>
              Cancel
            </Button>
          </CardFooter>
        </Card>
      </aside>
    </form>
  );
}
