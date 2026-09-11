import * as React from "react";

import { cn } from "@/lib/utils";

export interface SectionHeadingProps {
  title: React.ReactNode;
  description?: React.ReactNode;
  icon?: React.ReactNode;
  actions?: React.ReactNode;
  className?: string;
}

/** Small in-page section header: icon tile + title + optional description/actions. */
function SectionHeading({ title, description, icon, actions, className }: SectionHeadingProps) {
  return (
    <div className={cn("flex flex-wrap items-start justify-between gap-3", className)}>
      <div className="flex min-w-0 items-start gap-3">
        {icon ? (
          <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary-soft text-primary [&_svg]:h-4 [&_svg]:w-4">
            {icon}
          </span>
        ) : null}
        <div className="min-w-0">
          <h3 className="text-[15px] font-semibold leading-tight tracking-tight">{title}</h3>
          {description ? <p className="mt-0.5 text-[13px] text-muted-foreground">{description}</p> : null}
        </div>
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
    </div>
  );
}

export { SectionHeading };
