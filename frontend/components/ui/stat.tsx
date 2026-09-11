import * as React from "react";

import { cn } from "@/lib/utils";

export interface StatProps {
  label: React.ReactNode;
  value: React.ReactNode;
  hint?: React.ReactNode;
  className?: string;
}

/** Compact label/value pair used in summary grids. */
function Stat({ label, value, hint, className }: StatProps) {
  return (
    <div className={cn("flex flex-col gap-0.5 rounded-md bg-muted/50 px-3 py-2.5", className)}>
      <dt className="eyebrow">{label}</dt>
      <dd className="text-[15px] font-semibold tnum leading-snug">{value}</dd>
      {hint ? <dd className="text-xs text-muted-foreground">{hint}</dd> : null}
    </div>
  );
}

function StatGrid({ children, className }: { children: React.ReactNode; className?: string }) {
  return <dl className={cn("grid grid-cols-2 gap-2 sm:grid-cols-3", className)}>{children}</dl>;
}

export { Stat, StatGrid };
