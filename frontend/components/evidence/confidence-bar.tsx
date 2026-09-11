import { Progress } from "@/components/ui/progress";
import { cn, confidenceTone, formatPercent } from "@/lib/utils";

const TEXT_TONE: Record<ReturnType<typeof confidenceTone>, string> = {
  good: "text-success",
  warn: "text-warning",
  bad: "text-danger",
};

export function ConfidenceBar({ value, className }: { value: number; className?: string }) {
  const tone = confidenceTone(value);
  return (
    <div className={cn("flex items-center gap-2", className)}>
      <Progress value={value} tone={tone} className="h-1.5 w-20" label={`Confidence ${formatPercent(value)}`} />
      <span className={cn("w-10 text-right text-xs font-semibold tnum", TEXT_TONE[tone])}>{formatPercent(value, 0)}</span>
    </div>
  );
}
