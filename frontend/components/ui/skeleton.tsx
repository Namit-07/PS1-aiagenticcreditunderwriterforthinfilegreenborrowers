import { cn } from "@/lib/utils";

function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "rounded-md bg-[linear-gradient(90deg,hsl(var(--muted))_0%,hsl(var(--secondary))_50%,hsl(var(--muted))_100%)] bg-[length:200%_100%] animate-shimmer",
        className
      )}
      {...props}
    />
  );
}

/** A few stacked skeleton lines, handy as a page-level loading state. */
function SkeletonBlock({ lines = 3, className }: { lines?: number; className?: string }) {
  return (
    <div className={cn("space-y-2.5", className)} aria-busy="true" aria-live="polite">
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton key={i} className={cn("h-4", i === lines - 1 ? "w-2/3" : "w-full")} />
      ))}
    </div>
  );
}

export { Skeleton, SkeletonBlock };
