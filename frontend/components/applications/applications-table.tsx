"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { ChevronRight, Plus } from "lucide-react";

import { ApplicationStatusBadge, DecisionBadge } from "@/components/applications/status-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { Application } from "@/lib/types";
import { formatCurrency, formatDateTime, humanize, shortId } from "@/lib/utils";

function initialsOf(name: string): string {
  const parts = name.trim().split(/[\s._-]+/).filter(Boolean);
  if (parts.length === 0) return "?";
  return parts
    .slice(0, 2)
    .map((p) => p[0]!.toUpperCase())
    .join("");
}

export function ApplicationsTable({ applications }: { applications: Application[] }) {
  const router = useRouter();
  if (applications.length === 0) {
    return (
      <EmptyState
        title="No applications yet"
        description="Create an application to start underwriting."
        action={
          <Button asChild size="sm">
            <Link href="/applications/new">
              <Plus /> New application
            </Link>
          </Button>
        }
      />
    );
  }
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Borrower</TableHead>
          <TableHead>Product</TableHead>
          <TableHead className="text-right">Amount</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Latest decision</TableHead>
          <TableHead>Created</TableHead>
          <TableHead className="w-10 text-right">
            <span className="sr-only">Open</span>
          </TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {applications.map((a) => {
          const display = a.borrower.full_name || a.borrower.ref_id;
          return (
            <TableRow
              key={a.id}
              className="group cursor-pointer"
              onClick={() => router.push(`/applications/${a.id}`)}
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter") router.push(`/applications/${a.id}`);
              }}
            >
              <TableCell>
                <div className="flex items-center gap-3">
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary-soft text-xs font-semibold text-primary">
                    {initialsOf(display)}
                  </span>
                  <div className="min-w-0 leading-tight">
                    <div className="truncate font-medium">{display}</div>
                    <div className="mt-0.5 flex flex-wrap items-center gap-x-2 font-mono text-[11px] text-muted-foreground">
                      {a.borrower.full_name ? <span>{a.borrower.ref_id}</span> : null}
                      <span title={a.id}>#{shortId(a.id, 8)}</span>
                    </div>
                  </div>
                </div>
              </TableCell>
              <TableCell>
                <Badge variant="outline" className="font-normal">
                  {humanize(a.product.type)}
                </Badge>
              </TableCell>
              <TableCell className="whitespace-nowrap text-right font-semibold tnum">
                {formatCurrency(a.loan_request?.amount ?? a.product.amount)}
              </TableCell>
              <TableCell>
                <ApplicationStatusBadge status={a.status} />
              </TableCell>
              <TableCell>
                <DecisionBadge decision={a.latest_decision} />
              </TableCell>
              <TableCell className="whitespace-nowrap text-xs text-muted-foreground tnum">{formatDateTime(a.created_at)}</TableCell>
              <TableCell className="text-right">
                <ChevronRight className="ml-auto h-4 w-4 text-muted-foreground/60 transition-all group-hover:translate-x-0.5 group-hover:text-primary" />
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}
