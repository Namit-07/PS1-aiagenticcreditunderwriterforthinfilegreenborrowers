"use client";

import { use } from "react";
import { AlertTriangle, FileSearch, GitCompareArrows, ScanSearch } from "lucide-react";

import { ApplicationPageFrame } from "@/components/applications/application-page-frame";
import { EvidenceViewer } from "@/components/evidence/evidence-viewer";
import { ReconciliationList } from "@/components/reconciliation/reconciliation-list";
import { RunLoader } from "@/components/underwriting/run-loader";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { RingMeter } from "@/components/ui/ring-meter";
import { SectionHeading } from "@/components/ui/section-heading";
import { cn, confidenceTone, formatPercent } from "@/lib/utils";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function EvidencePage({ params }: PageProps) {
  const { id } = use(params);

  return (
    <ApplicationPageFrame
      applicationId={id}
      title="Evidence viewer"
      description="Every extracted fact with its confidence and the citation it came from. Click a row for the full snippet."
    >
      <RunLoader applicationId={id}>
        {({ state }) => {
          const overall = state.confidence_summary?.overall ?? null;
          const facts = state.evidence.length;
          const low = state.low_confidence.length;
          const sources = new Set(state.evidence.map((e) => e.source_document ?? "Unattributed")).size;
          return (
            <div className="flex flex-col gap-6">
              <Card className="animate-in-up">
                <CardContent className="flex flex-col gap-5 p-5 md:flex-row md:items-center md:gap-8">
                  <div className="flex items-center gap-4">
                    <RingMeter
                      value={overall ?? 0}
                      tone={overall === null ? "neutral" : confidenceTone(overall)}
                      size={104}
                      stroke={9}
                      label={formatPercent(overall, 0)}
                      sublabel="overall"
                    />
                    <div>
                      <div className="eyebrow">Overall confidence</div>
                      <div className="mt-1 text-sm text-muted-foreground">
                        Weighted across every extracted field. Fields below the policy threshold are routed to human review.
                      </div>
                    </div>
                  </div>

                  <div className="hidden h-16 w-px bg-border md:block" aria-hidden="true" />

                  <dl className="grid flex-1 grid-cols-2 gap-2 sm:grid-cols-3">
                    <div className="flex flex-col gap-1 rounded-md bg-muted/50 px-3 py-2.5">
                      <dt className="eyebrow flex items-center gap-1.5">
                        <ScanSearch className="h-3.5 w-3.5" /> Facts
                      </dt>
                      <dd className="text-2xl font-bold leading-none tracking-tight tnum">{facts}</dd>
                      <dd className="text-[11px] text-muted-foreground tnum">
                        from {sources} document{sources === 1 ? "" : "s"}
                      </dd>
                    </div>
                    <div
                      className={cn(
                        "flex flex-col gap-1 rounded-md px-3 py-2.5",
                        low > 0 ? "bg-danger-soft" : "bg-success-soft"
                      )}
                    >
                      <dt className={cn("eyebrow flex items-center gap-1.5", low > 0 ? "text-danger" : "text-success")}>
                        <AlertTriangle className="h-3.5 w-3.5" /> Below threshold
                      </dt>
                      <dd className={cn("text-2xl font-bold leading-none tracking-tight tnum", low > 0 ? "text-danger" : "text-success")}>
                        {low}
                      </dd>
                      <dd className="text-[11px] text-muted-foreground">{low > 0 ? "need human review" : "all fields clear"}</dd>
                    </div>
                    <div className="col-span-2 flex flex-col justify-center gap-1.5 rounded-md bg-muted/50 px-3 py-2.5 sm:col-span-1">
                      <dt className="eyebrow">Legend</dt>
                      <dd className="flex flex-col gap-1 text-[11px] text-muted-foreground">
                        <span className="flex items-center gap-1.5">
                          <i className="inline-block h-1.5 w-4 rounded-full bg-success" /> ≥ 85%
                        </span>
                        <span className="flex items-center gap-1.5">
                          <i className="inline-block h-1.5 w-4 rounded-full bg-warning" /> ≥ 60%
                        </span>
                        <span className="flex items-center gap-1.5">
                          <i className="inline-block h-1.5 w-4 rounded-full bg-danger" /> &lt; 60%
                        </span>
                      </dd>
                    </div>
                  </dl>
                </CardContent>
              </Card>

              <div className="animate-in-up delay-1 flex flex-col gap-4">
                <SectionHeading
                  icon={<FileSearch />}
                  title="Extracted facts by document"
                  description="Grouped by source. Select any row to open the full citation."
                />
                <EvidenceViewer evidence={state.evidence} />
              </div>

              <Card className="animate-in-up delay-2">
                <CardHeader>
                  <SectionHeading
                    icon={<GitCompareArrows />}
                    title="Reconciliation"
                    description="Mismatches detected between documents and their impact on the decision."
                  />
                </CardHeader>
                <CardContent>
                  <ReconciliationList reconciliation={state.reconciliation} />
                </CardContent>
              </Card>
            </div>
          );
        }}
      </RunLoader>
    </ApplicationPageFrame>
  );
}
