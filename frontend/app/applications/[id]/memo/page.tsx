"use client";

import { use } from "react";
import Link from "next/link";
import { FileDown, FileText, Printer, RefreshCw } from "lucide-react";

import { ApplicationPageFrame } from "@/components/applications/application-page-frame";
import { CreditMemoView } from "@/components/credit-memo/credit-memo-view";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton, SkeletonBlock } from "@/components/ui/skeleton";
import { useAsync } from "@/hooks/use-async";
import { api } from "@/lib/api";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function MemoPage({ params }: PageProps) {
  const { id } = use(params);
  const memo = useAsync(() => api.getCreditMemo(id), [id]);

  // The backend renders the PDF automatically when the run completes; prefer that cached file.
  const exportPdf = () => {
    const url = memo.data?.run_id ? api.runMemoPdfUrl(memo.data.run_id) : api.creditMemoPdfUrl(id);
    window.open(url, "_blank", "noopener");
  };

  return (
    <ApplicationPageFrame
      applicationId={id}
      title="Credit memo"
      description="Facts, calculations, AI reasoning, policy and human decisions — kept in separate sections."
      actions={
        <>
          <Button variant="outline" size="sm" onClick={memo.reload} disabled={memo.loading} className="print:hidden">
            <RefreshCw className={memo.loading ? "animate-spin" : undefined} /> Refresh
          </Button>
          <Button variant="outline" size="sm" onClick={() => window.print()} className="print:hidden" disabled={!memo.data}>
            <Printer /> Print
          </Button>
          <Button variant="brand" size="sm" onClick={exportPdf} className="print:hidden" title={memo.data?.pdf_ready ? "PDF was generated automatically when the run completed" : undefined}>
            <FileDown /> {memo.data?.pdf_ready ? "Download PDF" : "Export PDF"}
          </Button>
        </>
      }
    >
      {memo.error ? (
        memo.error.toLowerCase().includes("not found") || memo.error.includes("404") ? (
          <EmptyState
            icon={<FileText />}
            title="No credit memo yet"
            description="A memo is generated when an underwriting run completes."
            action={
              <Button asChild variant="outline">
                <Link href={`/applications/${id}`}>Go to application</Link>
              </Button>
            }
          />
        ) : (
          <Alert variant="destructive" title="Could not load credit memo">
            {memo.error}
          </Alert>
        )
      ) : null}
      {memo.loading && !memo.data ? (
        <div className="mx-auto flex w-full max-w-5xl flex-col gap-5">
          <div className="rounded-lg border bg-card p-6 shadow-card">
            <Skeleton className="h-3 w-32" />
            <Skeleton className="mt-3 h-7 w-2/3" />
            <SkeletonBlock lines={2} className="mt-4" />
          </div>
          <div className="rounded-lg border bg-card p-6 shadow-card">
            <SkeletonBlock lines={5} />
          </div>
        </div>
      ) : null}
      {memo.data ? <CreditMemoView memo={memo.data} /> : null}
    </ApplicationPageFrame>
  );
}
