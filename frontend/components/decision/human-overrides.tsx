import { ArrowRight, UserCheck } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { HumanReview } from "@/lib/types";
import { displayValue, formatDateTime, humanize } from "@/lib/utils";

const ACTION_VARIANT = (action: HumanReview["action"]) =>
  action === "reject" ? "danger" : action === "override" ? "warning" : action === "correct" ? "info" : "success";

export function HumanOverrides({ reviews }: { reviews: HumanReview[] }) {
  if (!reviews || reviews.length === 0) {
    return (
      <div className="flex items-center gap-3 rounded-md border border-dashed px-4 py-4 text-sm text-muted-foreground">
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
          <UserCheck className="h-4 w-4" />
        </span>
        No human reviews or overrides on this run — the outcome is fully automated.
      </div>
    );
  }
  return (
    <div className="overflow-hidden rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Field</TableHead>
            <TableHead>Action</TableHead>
            <TableHead>Value</TableHead>
            <TableHead>Reviewer</TableHead>
            <TableHead>Note</TableHead>
            <TableHead className="text-right">When</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {reviews.map((r) => {
            const changed = r.corrected_value !== null && r.corrected_value !== undefined && r.corrected_value !== r.original_value;
            return (
              <TableRow key={r.id}>
                <TableCell className="font-mono text-xs font-medium">{r.field}</TableCell>
                <TableCell>
                  <Badge variant={ACTION_VARIANT(r.action)} dot>
                    {humanize(r.action)}
                  </Badge>
                </TableCell>
                <TableCell className="tnum">
                  <span className="inline-flex flex-wrap items-center gap-1.5">
                    <span className={changed ? "text-muted-foreground line-through decoration-danger/60" : undefined}>
                      {displayValue(r.original_value)}
                    </span>
                    {changed ? (
                      <>
                        <ArrowRight className="h-3 w-3 text-muted-foreground" />
                        <span className="font-semibold">{displayValue(r.corrected_value)}</span>
                      </>
                    ) : null}
                  </span>
                </TableCell>
                <TableCell className="whitespace-nowrap">{r.reviewer ?? "—"}</TableCell>
                <TableCell className="max-w-[240px] truncate text-muted-foreground" title={r.note ?? undefined}>
                  {r.note ?? "—"}
                </TableCell>
                <TableCell className="whitespace-nowrap text-right text-xs text-muted-foreground tnum">{formatDateTime(r.timestamp)}</TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
