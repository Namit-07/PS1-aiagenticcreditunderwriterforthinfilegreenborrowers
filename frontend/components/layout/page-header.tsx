import type { ReactNode } from "react";
import Link from "next/link";
import { ChevronRight } from "lucide-react";

import { cn } from "@/lib/utils";

export interface Crumb {
  label: ReactNode;
  href?: string;
}

export interface PageHeaderProps {
  title: ReactNode;
  /** Small uppercase label above the title. */
  eyebrow?: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  crumbs?: Crumb[];
  /** Rendered to the right of the title (badges etc). */
  meta?: ReactNode;
  className?: string;
}

export function PageHeader({ title, eyebrow, description, actions, crumbs, meta, className }: PageHeaderProps) {
  return (
    <div className={cn("flex flex-col gap-2", className)}>
      {crumbs && crumbs.length > 0 ? (
        <nav className="flex flex-wrap items-center gap-1 text-xs text-muted-foreground" aria-label="Breadcrumb">
          {crumbs.map((c, i) => (
            <span key={i} className="flex items-center gap-1">
              {i > 0 ? <ChevronRight className="h-3 w-3 opacity-60" /> : null}
              {c.href ? (
                <Link href={c.href} className="rounded px-1 py-0.5 transition-colors hover:bg-accent hover:text-foreground">
                  {c.label}
                </Link>
              ) : (
                <span className="px-1 text-foreground">{c.label}</span>
              )}
            </span>
          ))}
        </nav>
      ) : null}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          {eyebrow ? <div className="eyebrow mb-1.5">{eyebrow}</div> : null}
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-[26px] font-bold leading-tight tracking-tight sm:text-3xl">{title}</h1>
            {meta}
          </div>
          {description ? <p className="mt-1.5 max-w-3xl text-sm text-muted-foreground">{description}</p> : null}
        </div>
        {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
      </div>
    </div>
  );
}
