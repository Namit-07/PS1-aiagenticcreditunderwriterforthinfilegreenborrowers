"use client";

import { Activity, CheckCircle2, ListChecks, RefreshCw, UserCheck } from "lucide-react";

import { ReviewQueue } from "@/components/human-review/review-queue";
import { AppShell } from "@/components/layout/app-shell";
import { PageHeader } from "@/components/layout/page-header";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { SectionHeading } from "@/components/ui/section-heading";
import { Skeleton, SkeletonBlock } from "@/components/ui/skeleton";
import { useAsync } from "@/hooks/use-async";
import { api } from "@/lib/api";
import { cn, formatPercent } from "@/lib/utils";

export default function ReviewPage() {
  const runs = useAsync(() => api.auditRuns(), []);
  const all = runs.data ?? [];
  const waiting = all.filter((r) => r.status === "awaiting_human");
  const completed = all.filter((r) => r.status === "completed");
  const waitingShare = all.length > 0 ? waiting.length / all.length : 0;
  const initialLoading = runs.loading && !runs.data;

  return (
    <AppShell>
      <PageHeader
        eyebrow="Human in the loop"
        title="Human review queue"
        description={`Runs paused for a reviewer${runs.data ? ` · ${waiting.length} waiting` : ""}.`}
        meta={
          runs.data ? (
            <Badge variant={waiting.length > 0 ? "warning" : "success"} dot>
              {waiting.length > 0 ? `${waiting.length} waiting` : "All clear"}
            </Badge>
          ) : null
        }
        actions={
          <Button variant="outline" size="sm" onClick={runs.reload} disabled={runs.loading}>
            <RefreshCw className={runs.loading ? "animate-spin" : undefined} /> Refresh
          </Button>
        }
      />
      {runs.error ? (
        <Alert variant="destructive" title="Could not load runs">
          {runs.error}
        </Alert>
      ) : null}

      {/* Queue stats */}
      {initialLoading ? (
        <div className="grid gap-3 md:grid-cols-3">
          <Skeleton className="h-[132px] rounded-lg md:col-span-2" />
          <Skeleton className="h-[132px] rounded-lg" />
        </div>
      ) : (
        <div className="grid gap-3 md:grid-cols-3">
          <Card className="relative overflow-hidden p-5 md:col-span-2">
            <span
              className={cn("absolute inset-x-0 top-0 h-[3px]", waiting.length > 0 ? "bg-warning" : "bg-success")}
              aria-hidden="true"
            />
            <div className="flex flex-wrap items-start gap-4 sm:gap-6">
              <span
                className={cn(
                  "flex h-14 w-14 shrink-0 items-center justify-center rounded-xl [&_svg]:h-6 [&_svg]:w-6",
                  waiting.length > 0 ? "bg-warning-soft text-warning" : "bg-success-soft text-success"
                )}
              >
                <UserCheck />
              </span>
              <div className="min-w-0 flex-1">
                <div className="eyebrow">Waiting for a reviewer</div>
                <div className="mt-1 flex flex-wrap items-baseline gap-x-2">
                  <span className="text-[40px] font-bold leading-none tracking-tight tnum">{waiting.length}</span>
                  <span className="text-sm text-muted-foreground">
                    {waiting.length === 1 ? "run" : "runs"} paused for a human decision
                  </span>
                </div>
                <div className="mt-4">
                  <div className="mb-1.5 flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">Share of all runs</span>
                    <span className="font-medium tnum">{formatPercent(waitingShare, 0)}</span>
                  </div>
                  <Progress value={waitingShare} tone={waiting.length > 0 ? "warn" : "good"} label="Share of runs waiting" />
                </div>
              </div>
            </div>
          </Card>
          <Card className="flex flex-col divide-y p-0">
            <div className="flex items-center gap-3 px-5 py-4">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-primary-soft text-primary [&_svg]:h-4 [&_svg]:w-4">
                <Activity />
              </span>
              <div className="min-w-0 flex-1">
                <div className="eyebrow">Runs total</div>
                <div className="text-xs text-muted-foreground">Across all applications</div>
              </div>
              <div className="text-xl font-semibold tracking-tight tnum">{all.length}</div>
            </div>
            <div className="flex items-center gap-3 px-5 py-4">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-success-soft text-success [&_svg]:h-4 [&_svg]:w-4">
                <CheckCircle2 />
              </span>
              <div className="min-w-0 flex-1">
                <div className="eyebrow">Completed</div>
                <div className="text-xs text-muted-foreground">Finished end-to-end</div>
              </div>
              <div className="text-xl font-semibold tracking-tight tnum">{completed.length}</div>
            </div>
          </Card>
        </div>
      )}

      <Card>
        <CardHeader className="border-b">
          <SectionHeading
            icon={<ListChecks />}
            title="Queue"
            description="Oldest first. Open a run to accept, correct or reject extracted fields and resume the workflow."
          />
        </CardHeader>
        <CardContent className="p-0">
          {initialLoading ? (
            <div className="p-5">
              <SkeletonBlock lines={4} />
            </div>
          ) : (
            <ReviewQueue runs={waiting} />
          )}
        </CardContent>
      </Card>
    </AppShell>
  );
}
