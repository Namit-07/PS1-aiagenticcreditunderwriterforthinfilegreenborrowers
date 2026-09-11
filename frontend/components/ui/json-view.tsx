"use client";

import * as React from "react";
import { ChevronDown, ChevronRight } from "lucide-react";

import { cn } from "@/lib/utils";

export interface JsonViewProps {
  value: unknown;
  className?: string;
  /** Render inside a collapsible toggle with this label. */
  collapsible?: string;
  defaultOpen?: boolean;
}

/** Pretty-printed JSON block, optionally collapsible. */
function JsonView({ value, className, collapsible, defaultOpen = false }: JsonViewProps) {
  const [open, setOpen] = React.useState(defaultOpen);
  const text = React.useMemo(() => {
    try {
      return JSON.stringify(value, null, 2);
    } catch {
      return String(value);
    }
  }, [value]);

  const pre = (
    <pre
      className={cn(
        "max-h-96 overflow-auto rounded-md border bg-[hsl(var(--sidebar))] p-3.5 font-mono text-[12px] leading-relaxed text-[hsl(var(--sidebar-foreground))]",
        className
      )}
    >
      {text}
    </pre>
  );

  if (!collapsible) return pre;
  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="inline-flex items-center gap-1 rounded-md px-1.5 py-1 text-xs font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
        aria-expanded={open}
      >
        {open ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
        {collapsible}
      </button>
      {open ? <div className="mt-2">{pre}</div> : null}
    </div>
  );
}

export { JsonView };
