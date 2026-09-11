"use client";

import { use } from "react";
import { Fingerprint, History, RefreshCw, Repeat } from "lucide-react";

import { ApplicationPageFrame } from "@/components/applications/application-page-frame";
import { RunStatusBadge } from "@/components/applications/status-badge";
import { ReplayPanel } from "@/components/audit/replay-panel";
import { TraceTimeline } from "@/components/audit/trace-timeline";
import { NodeStepper } from "@/components/underwriting/node-stepper";
import { RunLoader } from "@/components/underwriting/run-loader";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { SectionHeading } from "@/components/ui/section-heading";
import { SkeletonBlock } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useAsync } from "@/hooks/use-async";
import { api } from "@/lib/api";
import type { RunState } from "@/lib/types";
import { shortId } from "@/lib/utils";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function AuditPage({ params }: PageProps) {
  const { id } = use(params);
  return (
    <ApplicationPageFrame applicationId={id} title="Audit" description="Full agent trace and deterministic replay for the run.">
      <RunLoader applicationId={id}>{({ runId, state }) => <AuditTabs runId={runId} state={state} />}</RunLoader>
    </ApplicationPageFrame>
  );
}

function AuditTabs({ runId, state }: { runId: string; state: RunState }) {
  const trace = useAsync(() => api.getTrace(runId), [runId]);

  return (
    <div className="flex flex-col gap-5">
      <div className="animate-in-up flex flex-wrap items-center gap-3 rounded-lg border bg-card px-4 py-3 shadow-card">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-primary-soft text-primary">
          <Fingerprint className="h-4 w-4" />
        </span>
        <div className="min-w-0 flex-1">
          <div className="eyebrow">Run under audit</div>
          <div className="truncate font-mono text-sm" title={runId}>
            {shortId(runId, 24)}
          </div>
        </div>
        <RunStatusBadge status={state.status} />
      </div>

      <Tabs defaultValue="trace" className="animate-in-up delay-1">
        <TabsList>
          <TabsTrigger value="trace">
            <History /> Trace
          </TabsTrigger>
          <TabsTrigger value="replay">
            <Repeat /> Replay
          </TabsTrigger>
        </TabsList>
        <TabsContent value="trace">
          <Card>
            <CardHeader>
              <SectionHeading
                icon={<History />}
                title="Trace timeline"
                description={
                  trace.data ? (
                    <>
                      <span className="tnum">{trace.data.steps.length}</span> steps · status{" "}
                      <span className="font-mono">{trace.data.status}</span>
                    </>
                  ) : (
                    "Ordered events emitted by each agent."
                  )
                }
                actions={
                  <Button variant="outline" size="sm" onClick={trace.reload} disabled={trace.loading}>
                    <RefreshCw className={trace.loading ? "animate-spin" : undefined} /> Refresh
                  </Button>
                }
              />
            </CardHeader>
            <CardContent className="flex flex-col gap-6">
              {trace.error ? (
                <Alert variant="destructive" title="Could not load trace">
                  {trace.error}
                </Alert>
              ) : null}
              {trace.loading && !trace.data ? (
                <SkeletonBlock lines={6} />
              ) : trace.data ? (
                <>
                  <NodeStepper nodes={trace.data.nodes} runStatus={state.status} />
                  <TraceTimeline steps={trace.data.steps} />
                </>
              ) : null}
            </CardContent>
          </Card>
        </TabsContent>
        <TabsContent value="replay">
          <Card>
            <CardHeader>
              <SectionHeading
                icon={<Repeat />}
                title="Deterministic replay"
                description="Same inputs, same policy version, same outputs — or a diff that shows where they drift."
              />
            </CardHeader>
            <CardContent>
              <ReplayPanel runId={runId} />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
