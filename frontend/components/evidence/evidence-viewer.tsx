"use client";

import { useMemo, useState } from "react";
import { ChevronRight, FileSearch, FileText, Quote } from "lucide-react";

import { ReviewStatusBadge } from "@/components/applications/status-badge";
import { ConfidenceBar } from "@/components/evidence/confidence-bar";
import { Badge } from "@/components/ui/badge";
import { Dialog } from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { RingMeter } from "@/components/ui/ring-meter";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { EvidenceItem } from "@/lib/types";
import { cn, confidenceTone, displayValue, formatPercent, humanize } from "@/lib/utils";

const UNKNOWN = "Unattributed";
const STAGGER = ["", "delay-1", "delay-2", "delay-3", "delay-4"];

const TEXT_TONE = { good: "text-success", warn: "text-warning", bad: "text-danger" } as const;

export function EvidenceViewer({ evidence }: { evidence: EvidenceItem[] }) {
  const [selected, setSelected] = useState<EvidenceItem | null>(null);

  const groups = useMemo(() => {
    const map = new Map<string, EvidenceItem[]>();
    for (const item of evidence) {
      const key = item.source_document ?? UNKNOWN;
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(item);
    }
    return Array.from(map.entries());
  }, [evidence]);

  if (evidence.length === 0) {
    return (
      <EmptyState
        icon={<FileSearch />}
        title="No evidence extracted"
        description="The extraction node has not produced any cited facts for this run."
      />
    );
  }

  return (
    <div className="flex flex-col gap-5">
      {groups.map(([doc, items], gi) => {
        const avg = items.reduce((acc, it) => acc + (Number.isFinite(it.confidence) ? it.confidence : 0), 0) / items.length;
        const lowCount = items.filter((it) => confidenceTone(it.confidence) === "bad").length;
        return (
          <section
            key={doc}
            className={cn("animate-in-up overflow-hidden rounded-lg border bg-card shadow-card", STAGGER[gi] ?? "")}
          >
            <header className="flex flex-wrap items-center gap-3 border-b bg-muted/40 px-4 py-3">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-primary-soft text-primary">
                <FileText className="h-4 w-4" />
              </span>
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-semibold" title={doc}>
                  {doc}
                </div>
                <div className="text-xs text-muted-foreground">
                  <span className="tnum">{items.length}</span> field{items.length === 1 ? "" : "s"} extracted
                  {lowCount ? (
                    <>
                      {" · "}
                      <span className="text-danger tnum">{lowCount} low confidence</span>
                    </>
                  ) : null}
                </div>
              </div>
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <span className="hidden sm:inline">avg confidence</span>
                <span className={cn("font-semibold tnum", TEXT_TONE[confidenceTone(avg)])}>{formatPercent(avg, 0)}</span>
              </div>
            </header>
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead>Field</TableHead>
                  <TableHead>Value</TableHead>
                  <TableHead>Confidence</TableHead>
                  <TableHead className="text-center">Page</TableHead>
                  <TableHead>Review</TableHead>
                  <TableHead>Citation</TableHead>
                  <TableHead className="w-8" aria-label="Open" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((item, i) => (
                  <TableRow
                    key={`${item.field}-${i}`}
                    className="group cursor-pointer"
                    onClick={() => setSelected(item)}
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") setSelected(item);
                    }}
                  >
                    <TableCell>
                      <div className="font-medium">{humanize(item.field)}</div>
                      <div className="font-mono text-[11px] text-muted-foreground">
                        {item.field}
                        {item.kind ? <span className="opacity-70"> · {item.kind}</span> : null}
                      </div>
                    </TableCell>
                    <TableCell className="font-medium tnum">{displayValue(item.value)}</TableCell>
                    <TableCell>
                      <ConfidenceBar value={item.confidence} />
                    </TableCell>
                    <TableCell className="text-center text-muted-foreground tnum">{item.page ?? "—"}</TableCell>
                    <TableCell>
                      <ReviewStatusBadge status={item.review_status} />
                    </TableCell>
                    <TableCell className="max-w-[260px]">
                      {item.evidence ? (
                        <span className="line-clamp-1 text-xs italic text-muted-foreground">&ldquo;{item.evidence}&rdquo;</span>
                      ) : (
                        <span className="text-xs text-muted-foreground">—</span>
                      )}
                    </TableCell>
                    <TableCell className="pl-0 pr-3 text-muted-foreground/50 transition-colors group-hover:text-primary">
                      <ChevronRight className="h-4 w-4" aria-hidden="true" />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </section>
        );
      })}

      <Dialog
        open={selected !== null}
        onClose={() => setSelected(null)}
        side="right"
        title={selected ? humanize(selected.field) : ""}
        description={selected ? <span className="font-mono text-xs">{selected.field}</span> : null}
      >
        {selected ? <EvidenceDetail item={selected} /> : null}
      </Dialog>
    </div>
  );
}

function DetailStat({ label, children, className }: { label: string; children: React.ReactNode; className?: string }) {
  return (
    <div className={cn("flex flex-col gap-1 rounded-md bg-muted/50 px-3 py-2.5", className)}>
      <div className="eyebrow">{label}</div>
      <div className="text-sm">{children}</div>
    </div>
  );
}

function EvidenceDetail({ item }: { item: EvidenceItem }) {
  const tone = confidenceTone(item.confidence);
  return (
    <div className="flex flex-col gap-5 text-sm">
      <div className="flex items-center gap-4 rounded-lg border bg-muted/30 p-4">
        <RingMeter value={item.confidence} tone={tone} size={84} stroke={7} label={formatPercent(item.confidence, 0)} sublabel="conf." />
        <div className="min-w-0 flex-1">
          <div className="eyebrow">Extracted value</div>
          <div className="mt-1 break-words text-2xl font-bold leading-tight tracking-tight tnum">{displayValue(item.value)}</div>
          <div className="mt-2 flex flex-wrap items-center gap-1.5">
            <ReviewStatusBadge status={item.review_status} />
            {item.kind ? <Badge variant="secondary">{item.kind}</Badge> : null}
            <Badge variant={tone === "good" ? "success" : tone === "warn" ? "warning" : "danger"} dot>
              {tone === "good" ? "High confidence" : tone === "warn" ? "Needs attention" : "Below threshold"}
            </Badge>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <DetailStat label="Source document" className="col-span-2">
          <span className="inline-flex items-center gap-1.5 break-all">
            <FileText className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
            {item.source_document ?? "—"}
          </span>
        </DetailStat>
        <DetailStat label="Page">
          <span className="tnum">{item.page ?? "—"}</span>
        </DetailStat>
        <DetailStat label="Field key">
          <span className="break-all font-mono text-xs">{item.field}</span>
        </DetailStat>
      </div>

      <div>
        <div className="mb-2 flex items-center gap-1.5">
          <Quote className="h-3.5 w-3.5 text-primary" />
          <span className="eyebrow">Citation</span>
        </div>
        {item.evidence ? (
          <blockquote className="relative whitespace-pre-wrap rounded-md border border-l-4 border-l-primary bg-primary-soft/40 px-4 py-3 text-[15px] italic leading-relaxed text-foreground/90">
            &ldquo;{item.evidence}&rdquo;
          </blockquote>
        ) : (
          <p className="rounded-md border border-dashed px-4 py-3 text-muted-foreground">No text snippet was captured for this fact.</p>
        )}
      </div>
    </div>
  );
}
