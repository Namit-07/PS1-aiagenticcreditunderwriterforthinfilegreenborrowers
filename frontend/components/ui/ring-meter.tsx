import * as React from "react";

import { cn } from "@/lib/utils";

export interface RingMeterProps {
  /** 0..1 */
  value: number;
  tone?: "good" | "warn" | "bad" | "neutral" | "info";
  size?: number;
  stroke?: number;
  label?: React.ReactNode;
  sublabel?: React.ReactNode;
  className?: string;
}

const STROKE: Record<NonNullable<RingMeterProps["tone"]>, string> = {
  good: "stroke-success",
  warn: "stroke-warning",
  bad: "stroke-danger",
  neutral: "stroke-primary",
  info: "stroke-info",
};

/** Radial gauge for 0..1 values (confidence, risk score). */
function RingMeter({ value, tone = "neutral", size = 96, stroke = 8, label, sublabel, className }: RingMeterProps) {
  const v = Math.max(0, Math.min(1, Number.isFinite(value) ? value : 0));
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  return (
    <div className={cn("relative inline-flex shrink-0 items-center justify-center", className)} style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="-rotate-90" aria-hidden="true">
        <circle cx={size / 2} cy={size / 2} r={r} className="stroke-muted" strokeWidth={stroke} fill="none" />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          className={cn("transition-[stroke-dashoffset] duration-700 ease-out", STROKE[tone])}
          strokeWidth={stroke}
          strokeLinecap="round"
          fill="none"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - v)}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
        {label !== undefined ? <span className="text-lg font-semibold leading-none tnum">{label}</span> : null}
        {sublabel ? <span className="mt-1 text-[10px] uppercase tracking-wide text-muted-foreground">{sublabel}</span> : null}
      </div>
    </div>
  );
}

export { RingMeter };
