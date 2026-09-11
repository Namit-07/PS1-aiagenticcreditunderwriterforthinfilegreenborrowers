import Link from "next/link";
import { ArrowUpRight } from "lucide-react";

import { DecisionBadge, RunStatusBadge } from "@/components/applications/status-badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { RunSummary } from "@/lib/types";
import { formatDateTime, shortId } from "@/lib/utils";

export function RecentRunsTable({ runs, emptyTitle = "No runs yet" }: { runs: RunSummary[]; emptyTitle?: string }) {
  if (runs.length === 0) {
    return <EmptyState title={emptyTitle} description="Start underwriting on an application to see runs here." />;
  }
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Run</TableHead>
          <TableHead>Application</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Decision</TableHead>
          <TableHead>Created</TableHead>
          <TableHead className="text-right">Open</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {runs.map((r) => (
          <TableRow key={r.run_id} className="group">
            <TableCell>
              <code
                className="rounded-md border bg-muted/60 px-1.5 py-0.5 font-mono text-[11px] text-foreground/80"
                title={r.run_id}
              >
                {shortId(r.run_id, 12)}
              </code>
            </TableCell>
            <TableCell>
              <Link
                href={`/applications/${r.application_id}`}
                className="font-mono text-xs text-foreground/80 underline-offset-4 hover:text-primary hover:underline"
                title={r.application_id}
              >
                {shortId(r.application_id, 12)}
              </Link>
            </TableCell>
            <TableCell>
              <RunStatusBadge status={r.status} />
            </TableCell>
            <TableCell>
              <DecisionBadge decision={r.decision} />
            </TableCell>
            <TableCell className="whitespace-nowrap text-xs text-muted-foreground tnum">{formatDateTime(r.created_at)}</TableCell>
            <TableCell className="text-right">
              <Button asChild variant="ghost" size="sm" className="text-primary">
                <Link href={`/applications/${r.application_id}/underwriting?run=${r.run_id}`}>
                  Workflow <ArrowUpRight className="transition-transform group-hover:-translate-y-px group-hover:translate-x-px" />
                </Link>
              </Button>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
