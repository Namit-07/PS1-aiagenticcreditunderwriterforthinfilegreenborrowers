"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { ArrowLeft, Play } from "lucide-react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton, SkeletonBlock } from "@/components/ui/skeleton";
import { useRunId, useRunState } from "@/hooks/use-run";
import type { Application, RunState } from "@/lib/types";

export interface RunContext {
  runId: string;
  state: RunState;
  setState: (state: RunState) => void;
  reload: () => void;
  application: Application | null;
}

export interface RunLoaderProps {
  applicationId: string;
  /** Poll GET /underwriting/{run_id} every 1.5 s while the run is running. */
  poll?: boolean;
  children: (ctx: RunContext) => ReactNode;
}

function RunSkeleton() {
  return (
    <div className="flex flex-col gap-6" aria-busy="true" aria-live="polite">
      <Skeleton className="h-20 rounded-lg" />
      <div className="rounded-lg border bg-card p-5 shadow-card">
        <SkeletonBlock lines={2} className="max-w-sm" />
        <div className="mt-6 hidden grid-cols-10 gap-2 lg:grid">
          {Array.from({ length: 10 }).map((_, i) => (
            <div key={i} className="flex flex-col items-center gap-2">
              <Skeleton className="h-9 w-9 rounded-full" />
              <Skeleton className="h-3 w-full" />
            </div>
          ))}
        </div>
        <div className="mt-6 lg:hidden">
          <SkeletonBlock lines={5} />
        </div>
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <Skeleton className="h-48 rounded-lg" />
        <Skeleton className="h-48 rounded-lg" />
      </div>
    </div>
  );
}

/**
 * Resolves the run id (?run= or application.latest_run_id), loads the run state and
 * renders loading / error / empty states; the render-prop receives the live state.
 */
export function RunLoader({ applicationId, poll = false, children }: RunLoaderProps) {
  const resolved = useRunId(applicationId);
  const run = useRunState(resolved.runId, poll);

  if (resolved.loading && !resolved.runId) return <RunSkeleton />;

  if (!resolved.runId) {
    return (
      <div className="flex flex-col gap-4">
        {resolved.error ? (
          <Alert variant="destructive" title="Could not load application">
            {resolved.error}
          </Alert>
        ) : null}
        <EmptyState
          className="py-14"
          icon={<Play className="h-5 w-5 text-primary" />}
          title="No underwriting run yet"
          description="Start underwriting from the application overview to generate a run, then come back here to follow the pipeline live."
          action={
            <Button asChild variant="brand">
              <Link href={`/applications/${applicationId}`}>
                <ArrowLeft /> Go to application
              </Link>
            </Button>
          }
        />
      </div>
    );
  }

  if (run.error && !run.state) {
    return (
      <Alert variant="destructive" title="Could not load run">
        {run.error}
      </Alert>
    );
  }

  if (!run.state) return <RunSkeleton />;

  // A `?run=` copied from another application must not render (or sync) under this one.
  if (run.state.application_id && run.state.application_id !== applicationId) {
    return (
      <EmptyState
        icon={<ArrowLeft />}
        title="This run belongs to a different application"
        description="The run id in the URL was created for another application, so it is not shown here."
        action={
          <Button asChild variant="outline">
            <Link href={`/applications/${run.state.application_id}/underwriting?run=${encodeURIComponent(resolved.runId)}`}>
              Open it under its own application
            </Link>
          </Button>
        }
      />
    );
  }

  return (
    <>
      {run.error ? (
        <Alert variant="warning" title="Polling error">
          {run.error}
        </Alert>
      ) : null}
      {children({
        runId: resolved.runId,
        state: run.state,
        setState: run.setState,
        reload: run.reload,
        application: resolved.application,
      })}
    </>
  );
}
