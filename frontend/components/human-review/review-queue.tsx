import Link from "next/link";
import { ArrowRight, UserCheck } from "lucide-react";

import { RunStatusBadge } from "@/components/applications/status-badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { RunSummary } from "@/lib/types";
import { formatDateTime, shortId } from "@/lib/utils";

export function ReviewQueue({ runs }: { runs: RunSummary[] }) {
  if (runs.length === 0) {
    return (
      <EmptyState
        icon={<UserCheck />}
        title="Queue is empty"
        description="No underwriting runs are waiting for a human reviewer right now."
      />
    );
  }
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-12">#</TableHead>
          <TableHead>Run</TableHead>
          <TableHead>Application</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Waiting since</TableHead>
          <TableHead className="text-right">Action</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {runs.map((r, i) => (
          <TableRow key={r.run_id} className="group">
            <TableCell className="text-xs text-muted-foreground tnum">{i + 1}</TableCell>
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
            <TableCell className="whitespace-nowrap text-xs text-muted-foreground tnum">{formatDateTime(r.created_at)}</TableCell>
            <TableCell className="text-right">
              <Button asChild variant="brand" size="sm">
                <Link href={`/applications/${r.application_id}/underwriting?run=${encodeURIComponent(r.run_id)}`}>
                  Review <ArrowRight className="transition-transform group-hover:translate-x-0.5" />
                </Link>
              </Button>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
