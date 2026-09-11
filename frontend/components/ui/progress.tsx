import { cn } from "@/lib/utils";

export interface ProgressProps extends React.HTMLAttributes<HTMLDivElement> {
  /** 0..1 */
  value: number;
  tone?: "good" | "warn" | "bad" | "neutral";
  label?: string;
}

const toneClass: Record<NonNullable<ProgressProps["tone"]>, string> = {
  good: "bg-success",
  warn: "bg-warning",
  bad: "bg-danger",
  neutral: "bg-primary",
};

/** Thin horizontal meter for 0..1 values (confidence, risk score). */
function Progress({ value, tone = "neutral", label, className, ...props }: ProgressProps) {
  const pct = Math.max(0, Math.min(1, Number.isFinite(value) ? value : 0)) * 100;
  return (
    <div
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(pct)}
      aria-label={label}
      className={cn("h-2 w-full overflow-hidden rounded-full bg-muted", className)}
      {...props}
    >
      <div
        className={cn("h-full rounded-full transition-[width] duration-500 ease-out", toneClass[tone])}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

export { Progress };
