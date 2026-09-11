import { z } from "zod";

import { cn } from "@/lib/utils";
export { cn };

function toNumberOrUndefined(v: unknown): unknown {
  if (v === "" || v === undefined || v === null) return undefined;
  const n = typeof v === "number" ? v : Number(v);
  return Number.isNaN(n) ? v : n;
}

/** Accepts "" / undefined as "not provided", otherwise coerces to a number. */
const optionalNumber = (schema: z.ZodNumber = z.number().nonnegative()) =>
  z.preprocess(toNumberOrUndefined, schema.optional());

const requiredNumber = (schema: z.ZodNumber) => z.preprocess(toNumberOrUndefined, schema);

export const loginSchema = z.object({
  email: z.string().min(1, "Email is required").email("Enter a valid email"),
  password: z.string().min(1, "Password is required"),
});
export type LoginInput = z.infer<typeof loginSchema>;

export const PRODUCT_TYPES = [
  "ev_two_wheeler",
  "ev_three_wheeler",
  "solar_rooftop",
  "ev_four_wheeler",
] as const;
export const EMPLOYMENT_TYPES = ["gig_platform", "salaried", "self_employed"] as const;
export const LOCATION_TIERS = ["tier_1", "tier_2", "tier_3"] as const;
export const POLICY_PROFILES = ["default", "conservative", "aggressive"] as const;
export const DOCUMENT_CATEGORIES = [
  "kyc",
  "bank_statement",
  "dealer_invoice",
  "platform_earnings",
  "other",
] as const;

/** Zod schema for creating a new application (raw form values are strings). */
export const applicationSchema = z.object({
  product_type: z.enum(PRODUCT_TYPES, { errorMap: () => ({ message: "Select a product" }) }),
  amount: requiredNumber(
    z.number({ invalid_type_error: "Enter an amount" }).positive("Amount must be > 0")
  ),
  tenure_months: requiredNumber(
    z.number({ invalid_type_error: "Enter tenure" }).int("Whole months").positive().max(360)
  ),
  rate_annual: requiredNumber(z.number({ invalid_type_error: "Enter a rate" }).min(0).max(100)),
  ref_id: z.string().min(2, "Borrower reference is required"),
  full_name: z.string().optional(),
  age: requiredNumber(z.number({ invalid_type_error: "Enter age" }).int().min(16).max(100)),
  location_tier: z.enum(LOCATION_TIERS, { errorMap: () => ({ message: "Select a tier" }) }),
  declared_monthly_income: optionalNumber(),
  employment_type: z.enum(EMPLOYMENT_TYPES).or(z.literal("")).optional(),
  vehicle_price: optionalNumber(),
  down_payment: optionalNumber(),
});
export type ApplicationInput = z.infer<typeof applicationSchema>;

export const whatIfSchema = z.object({
  loan_amount: optionalNumber(z.number().positive()),
  tenure_months: optionalNumber(z.number().int().positive()),
  annual_rate: optionalNumber(z.number().min(0)),
  vehicle_price: optionalNumber(z.number().nonnegative()),
  existing_monthly_obligations: optionalNumber(z.number().nonnegative()),
  monthly_income: optionalNumber(z.number().nonnegative()),
  down_payment: optionalNumber(z.number().nonnegative()),
});
export type WhatIfInput = z.infer<typeof whatIfSchema>;

/** Flattens zod issues to a { field: message } map. */
export function zodErrors(error: z.ZodError): Record<string, string> {
  const out: Record<string, string> = {};
  for (const issue of error.issues) {
    const key = issue.path.join(".") || "_";
    if (!out[key]) out[key] = issue.message;
  }
  return out;
}
