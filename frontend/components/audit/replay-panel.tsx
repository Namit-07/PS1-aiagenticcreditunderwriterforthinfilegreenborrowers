"use client";

import { useState } from "react";
import { ArrowRight, Check, Repeat, RotateCw, ShieldCheck, ShieldX, X } from "lucide-react";

import { DecisionBadge } from "@/components/applications/status-badge";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api, errorMessage } from "@/lib/api";
import type { ReplayResponse, ReplaySnapshot } from "@/lib/types";
import { cn, displayValue, formatDateTime } from "@/lib/utils";

function decisionOf(s: ReplaySnapshot): string | null {
  if (!s.decision) return null;
  return typeof s.decision === "string" ? s.decision : s.decision.decision ?? null;
}

export function ReplayPanel({ runId }: { runId: string }) {
  const [result, setResult] = useState<ReplayResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const replay = async () => {
    setBusy(true);
    setError(null);
    try {
      setResult(await api.getReplay(runId));
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const mismatches = result ? result.diffs.filter((d) => !d.equal).length : 0;

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex min-w-0 items-start gap-3">
          <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-primary-soft text-primary">
            <Repeat className="h-4 w-4" />
          </span>
          <p className="max-w-xl text-sm leading-relaxed text-muted-foreground">
            Re-executes the deterministic compute, risk and policy nodes on the stored inputs and compares the output to the
            original run. A deterministic run reproduces the same decision from the same evidence and policy version.
          </p>
        </div>
        <Button variant="brand" onClick={replay} disabled={busy}>
          <RotateCw className={busy ? "animate-spin" : undefined} /> {busy ? "Replaying…" : result ? "Replay again" : "Run replay"}
        </Button>
      </div>

      {error ? (
        <Alert variant="destructive" title="Replay failed">
          {error}
        </Alert>
      ) : null}

      {!result && !error ? (
        <EmptyState
          icon={<Repeat />}
          title="No replay yet"
          description="Run a replay to verify that the recorded decision can be reproduced from its stored inputs."
        />
      ) : null}

      {result ? (
        <div className="animate-in-up flex flex-col gap-5">
          <div
            className={cn(
              "flex flex-col gap-4 rounded-lg border p-4 sm:flex-row sm:items-center sm:gap-6",
              result.deterministic ? "border-success/30 bg-success-soft/60" : "border-danger/30 bg-danger-soft/60"
            )}
          >
            <div className="flex items-center gap-3">
              <span
                className={cn(
                  "flex h-12 w-12 shrink-0 items-center justify-center rounded-xl text-white shadow-sm",
                  result.deterministic ? "bg-success" : "bg-danger"
                )}
              >
                {result.deterministic ? <ShieldCheck className="h-6 w-6" /> : <ShieldX className="h-6 w-6" />}
              </span>
              <div>
                <div className={cn("text-lg font-bold leading-tight tracking-tight", result.deterministic ? "text-success" : "text-danger")}>
                  {result.deterministic ? "Deterministic" : "Non-deterministic"}
                </div>
                <div className="text-xs text-muted-foreground">
                  {result.deterministic
                    ? "Every compared field reproduced exactly."
                    : `${mismatches} field${mismatches === 1 ? "" : "s"} drifted from the original run.`}
                </div>
              </div>
            </div>

            <div className="hidden h-10 w-px bg-border sm:block" aria-hidden="true" />

            <div className="flex flex-1 flex-wrap items-center gap-x-6 gap-y-2 text-xs text-muted-foreground">
              <span className="flex flex-col gap-0.5">
                <span className="eyebrow">Policy</span>
                <span className="font-mono text-foreground">
                  {result.policy.profile} · v{result.policy.version}
                </span>
              </span>
              <span className="flex flex-col gap-0.5">
                <span className="eyebrow">Replayed at</span>
                <span className="text-foreground tnum">{formatDateTime(result.replayed_at)}</span>
              </span>
            </div>

            <div className="flex items-center gap-2 rounded-md border bg-card px-3 py-2">
              <span className="flex flex-col items-start gap-0.5">
                <span className="eyebrow">Original</span>
                <DecisionBadge decision={decisionOf(result.original)} />
              </span>
              <ArrowRight className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
              <span className="flex flex-col items-start gap-0.5">
                <span className="eyebrow">Replayed</span>
                <DecisionBadge decision={decisionOf(result.replayed)} />
              </span>
            </div>
          </div>

          {result.diffs.length === 0 ? (
            <p className="text-sm text-muted-foreground">No diff entries returned.</p>
          ) : (
            <div className="overflow-hidden rounded-lg border">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b bg-muted/40 px-4 py-2.5">
                <span className="eyebrow">Field comparison</span>
                <span className="text-xs text-muted-foreground tnum">
                  {result.diffs.length - mismatches}/{result.diffs.length} equal
                </span>
              </div>
              <Table>
                <TableHeader>
                  <TableRow className="hover:bg-transparent">
                    <TableHead>Field</TableHead>
                    <TableHead>Original</TableHead>
                    <TableHead>Replayed</TableHead>
                    <TableHead className="text-center">Equal</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {result.diffs.map((d) => (
                    <TableRow key={d.field} className={cn(!d.equal && "bg-danger-soft/70 hover:bg-danger-soft")}>
                      <TableCell className="font-mono text-xs">{d.field}</TableCell>
                      <TableCell className="tnum">{displayValue(d.original)}</TableCell>
                      <TableCell className={cn("tnum", !d.equal && "font-semibold text-danger")}>{displayValue(d.replayed)}</TableCell>
                      <TableCell className="text-center">
                        {d.equal ? (
                          <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-success-soft text-success">
                            <Check className="h-3.5 w-3.5" aria-label="equal" strokeWidth={3} />
                          </span>
                        ) : (
                          <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-danger text-white">
                            <X className="h-3.5 w-3.5" aria-label="different" strokeWidth={3} />
                          </span>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}
