"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import {
  BookOpenText,
  FileText,
  FlaskConical,
  Gavel,
  History,
  LayoutList,
  Search,
  Workflow,
  type LucideIcon,
} from "lucide-react";

import { cn } from "@/lib/utils";

interface SubNav {
  segment: string;
  label: string;
  icon: LucideIcon;
  runAware?: boolean;
}

const SUBNAV: SubNav[] = [
  { segment: "", label: "Overview", icon: LayoutList },
  { segment: "documents", label: "Documents", icon: FileText },
  { segment: "underwriting", label: "Underwriting", icon: Workflow, runAware: true },
  { segment: "evidence", label: "Evidence", icon: Search, runAware: true },
  { segment: "decision", label: "Decision", icon: Gavel, runAware: true },
  { segment: "what-if", label: "What-if", icon: FlaskConical, runAware: true },
  { segment: "audit", label: "Audit", icon: History, runAware: true },
  { segment: "memo", label: "Credit memo", icon: BookOpenText },
];

/** Segmented sub-navigation shown on every application page. Preserves ?run=. */
export function ApplicationNav({ applicationId }: { applicationId: string }) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const run = searchParams.get("run");
  const base = `/applications/${applicationId}`;

  return (
    <nav
      className="-mx-1 overflow-x-auto px-1 pb-1 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
      aria-label="Application sections"
    >
      <div className="inline-flex min-w-full items-center gap-0.5 rounded-lg border bg-muted/60 p-1 sm:min-w-0">
        {SUBNAV.map((item) => {
          const href = item.segment ? `${base}/${item.segment}` : base;
          const active = pathname === href;
          const target = item.runAware && run ? `${href}?run=${encodeURIComponent(run)}` : href;
          return (
            <Link
              key={item.segment}
              href={target}
              className={cn(
                "flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-md px-3 py-1.5 text-[13px] font-medium transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                active
                  ? "bg-card text-foreground shadow-sm ring-1 ring-border"
                  : "text-muted-foreground hover:bg-card/60 hover:text-foreground"
              )}
              aria-current={active ? "page" : undefined}
            >
              <item.icon className={cn("h-4 w-4", active ? "text-primary" : "opacity-70")} />
              {item.label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
