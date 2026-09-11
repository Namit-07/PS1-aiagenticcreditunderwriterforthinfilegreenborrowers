import * as React from "react";
import { Inbox } from "lucide-react";

import { cn } from "@/lib/utils";

export interface EmptyStateProps {
  title: React.ReactNode;
  description?: React.ReactNode;
  action?: React.ReactNode;
  icon?: React.ReactNode;
  className?: string;
}

function EmptyState({ title, description, action, icon, className }: EmptyStateProps) {
  return (
    <div
      className={cn(
        "bg-grid flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed px-6 py-10 text-center",
        className
      )}
    >
      <div className="mb-1 flex h-12 w-12 items-center justify-center rounded-xl border bg-card text-muted-foreground shadow-sm [&_svg]:h-5 [&_svg]:w-5">
        {icon ?? <Inbox />}
      </div>
      <div className="text-sm font-semibold">{title}</div>
      {description ? <p className="max-w-md text-[13px] text-muted-foreground">{description}</p> : null}
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  );
}

export { EmptyState };
