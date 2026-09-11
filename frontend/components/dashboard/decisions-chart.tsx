"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { EmptyState } from "@/components/ui/empty-state";
import type { DashboardStats } from "@/lib/types";
import { cn } from "@/lib/utils";

// Decision outcome is a state, so each series uses its reserved status hue (the same
// token the decision badges use). Colours resolve from CSS variables so dark mode is free.
const SERIES = [
  { key: "approved", label: "Approved", color: "hsl(var(--success))", dot: "bg-success" },
  { key: "declined", label: "Declined", color: "hsl(var(--danger))", dot: "bg-danger" },
  { key: "referred", label: "Referred", color: "hsl(var(--warning))", dot: "bg-warning" },
] as const;

function formatDay(day: string): string {
  const d = new Date(day);
  if (Number.isNaN(d.getTime())) return day;
  return d.toLocaleDateString(undefined, { day: "2-digit", month: "short" });
}

export function DecisionsChart({ data }: { data: DashboardStats["decisions_by_day"] }) {
  if (!data || data.length === 0) {
    return <EmptyState title="No decisions yet" description="Decisions by day will appear once runs complete." />;
  }

  const totals = SERIES.map((s) => ({
    ...s,
    total: data.reduce((acc, row) => acc + (Number(row[s.key]) || 0), 0),
  }));

  return (
    <div className="flex flex-col gap-4">
      {/* Legend with period totals — doubles as the series key. */}
      <div className="flex flex-wrap gap-2">
        {totals.map((s) => (
          <span
            key={s.key}
            className="inline-flex items-center gap-2 rounded-full border bg-card px-2.5 py-1 text-xs"
          >
            <span className={cn("h-2 w-2 rounded-full", s.dot)} aria-hidden="true" />
            <span className="text-muted-foreground">{s.label}</span>
            <span className="font-semibold tnum">{s.total}</span>
          </span>
        ))}
      </div>

      <div className="h-64 w-full sm:h-72">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 4, left: -20, bottom: 0 }} barGap={3} barCategoryGap="26%">
            <CartesianGrid vertical={false} stroke="hsl(var(--border))" strokeDasharray="3 3" />
            <XAxis
              dataKey="day"
              tickLine={false}
              axisLine={false}
              tickMargin={8}
              tickFormatter={formatDay}
              tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
            />
            <YAxis
              allowDecimals={false}
              tickLine={false}
              axisLine={false}
              width={40}
              tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
            />
            <Tooltip
              cursor={{ fill: "hsl(var(--muted) / 0.7)", radius: 6 }}
              labelFormatter={(label) => formatDay(String(label))}
              contentStyle={{
                background: "hsl(var(--popover))",
                border: "1px solid hsl(var(--border))",
                borderRadius: 10,
                boxShadow: "0 8px 30px -12px hsl(var(--shadow-color) / 0.25)",
                color: "hsl(var(--popover-foreground))",
                fontSize: 12,
                padding: "8px 12px",
              }}
              labelStyle={{ fontWeight: 600, marginBottom: 4, color: "hsl(var(--popover-foreground))" }}
              itemStyle={{ padding: 0, fontVariantNumeric: "tabular-nums" }}
            />
            {SERIES.map((s) => (
              <Bar key={s.key} dataKey={s.key} name={s.label} fill={s.color} radius={[4, 4, 0, 0]} maxBarSize={26} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
