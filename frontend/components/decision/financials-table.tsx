import { Table, TableBody, TableCell, TableRow } from "@/components/ui/table";
import type { Financials } from "@/lib/types";
import { formatCurrency, formatNumber, formatPercent } from "@/lib/utils";

interface Row {
  label: string;
  value: string;
  hint?: string;
}

export function financialRows(f: Financials, compact = false): Row[] {
  const rows: Row[] = [
    { label: "EMI", value: formatCurrency(f.emi ?? f.monthly_emi), hint: "per month" },
    { label: "FOIR", value: formatPercent(f.foir), hint: "fixed obligations / income" },
    { label: "LTV", value: formatPercent(f.ltv), hint: "loan / asset value" },
    { label: "Verified income", value: formatCurrency(f.verified_income ?? f.monthly_income), hint: "per month" },
    { label: "Existing obligations", value: formatCurrency(f.existing_obligations ?? f.total_monthly_obligations), hint: "per month" },
  ];
  if (compact) return rows;
  rows.push(
    { label: "EMI to income", value: formatPercent(f.emi_to_income) },
    { label: "Loan to income", value: formatNumber(f.loan_to_income, 2), hint: "x annual income" },
    { label: "Income stability", value: formatPercent(f.income_stability) },
    { label: "Income volatility", value: formatPercent(f.income_volatility) },
    { label: "Down payment", value: formatCurrency(f.down_payment) },
    { label: "Formula version", value: f.formula_version ?? "—" }
  );
  return rows;
}

/** The three headline ratios are shown as boxed metrics; everything else in a compact table. */
const HEADLINE = 3;

export function FinancialsTable({ financials, compact = false }: { financials: Financials; compact?: boolean }) {
  const rows = financialRows(financials, compact);
  const headline = rows.slice(0, HEADLINE);
  const rest = rows.slice(HEADLINE);
  return (
    <div className="flex flex-col gap-4">
      <dl className="grid grid-cols-1 gap-2 sm:grid-cols-3">
        {headline.map((r) => (
          <div key={r.label} className="rounded-md border bg-muted/40 px-3.5 py-3">
            <dt className="eyebrow">{r.label}</dt>
            <dd className="mt-1 text-xl font-semibold leading-none tracking-tight tnum">{r.value}</dd>
            {r.hint ? <dd className="mt-1.5 text-[11px] text-muted-foreground">{r.hint}</dd> : null}
          </div>
        ))}
      </dl>
      {rest.length > 0 ? (
        <div className="overflow-hidden rounded-md border">
          <Table>
            <TableBody>
              {rest.map((r) => (
                <TableRow key={r.label}>
                  <TableCell className="py-2 text-[13px] text-muted-foreground">
                    {r.label}
                    {r.hint ? <span className="ml-1.5 text-[11px] opacity-70">({r.hint})</span> : null}
                  </TableCell>
                  <TableCell className="py-2 text-right text-[13px] font-medium tnum">{r.value}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      ) : null}
    </div>
  );
}
