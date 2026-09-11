"use client";

import * as React from "react";
import { X } from "lucide-react";

import { cn } from "@/lib/utils";

export interface DialogProps {
  open: boolean;
  onClose: () => void;
  title?: React.ReactNode;
  description?: React.ReactNode;
  children?: React.ReactNode;
  className?: string;
  /** Slide in from the right as a drawer instead of a centered modal. */
  side?: "center" | "right";
}

/** Minimal accessible modal / drawer (no portal dependency). */
function Dialog({ open, onClose, title, description, children, className, side = "center" }: DialogProps) {
  React.useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex" role="presentation">
      <div
        className="absolute inset-0 bg-[hsl(var(--sidebar))]/60 backdrop-blur-[2px] animate-in fade-in duration-150"
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        role="dialog"
        aria-modal="true"
        className={cn(
          "relative z-10 flex max-h-full w-full flex-col overflow-hidden border bg-card shadow-pop",
          side === "right"
            ? "ml-auto h-full max-w-lg border-l animate-in slide-in-from-right duration-200"
            : "m-auto max-w-lg rounded-xl animate-in zoom-in-95 fade-in duration-150",
          className
        )}
      >
        <div className="flex items-start justify-between gap-4 border-b bg-muted/40 px-5 py-4">
          <div className="min-w-0">
            {title ? <h2 className="text-base font-semibold leading-tight">{title}</h2> : null}
            {description ? <p className="mt-1 text-[13px] text-muted-foreground">{description}</p> : null}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="overflow-y-auto p-5">{children}</div>
      </div>
    </div>
  );
}

export { Dialog };
